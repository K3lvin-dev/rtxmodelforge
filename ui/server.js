/* RTX Model Forge — Static file server + API proxy */
import http from "node:http";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "dist");
const PROJ_ROOT = path.resolve(__dirname, "..");

/* Python CLI invocation.
   On Windows the CLI lives in WSL, so we exec via wsl.exe.
   On Linux/macOS we use the venv Python directly. */
const IS_WINDOWS = process.platform === "win32";
const PYTHON = process.env.RTXFORGE_PYTHON ||
  (IS_WINDOWS ? "wsl.exe" : path.join(PROJ_ROOT, ".venv", "bin", "python"));

/* Porta: --port N, env PORT, ou 8081 */
const portArg = process.argv.indexOf("--port");
const PORT = portArg !== -1 ? Number(process.argv[portArg + 1]) : Number(process.env.PORT) || 8081;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

/* Command map: frontend OperationId -> CLI subcommand */
const OP_MAP = {
  prepare: "build",
  serve: "serve",
  chat: "chat",
  run: "run",
  login: "login",
  doctor: "doctor",
  list: "list",
  delete: "delete",
};

/* ── Helpers ── */

function sendJSON(res, data, status = 200) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function sendError(res, msg, status = 500) {
  sendJSON(res, { ok: false, error: msg }, status);
}

/** Run python -m rtxmodelforge.main <args> --json and return parsed result.
    Handles mixed output (diagnostic messages + JSON) by extracting the JSON line. */
function execCLI(args) {
  const jsonArgs = [...args, "--json"];
  let cmd, cmdArgs;

  if (IS_WINDOWS) {
    /* Build full bash command string with all arguments inline */
    const escaped = jsonArgs.map(a => `'${a.replace(/'/g, `'\\''`)}'`).join(" ");
    cmd = "wsl.exe";
    cmdArgs = [
      "bash", "-c",
      `cd ~/rtxmodelforge && .venv/bin/python -m rtxmodelforge.main ${escaped}`,
    ];
  } else {
    cmd = PYTHON;
    cmdArgs = ["-m", "rtxmodelforge.main", ...jsonArgs];
  }

  return new Promise((resolve, reject) => {
    execFile(
      cmd,
      cmdArgs,
      { timeout: 300000, ...(IS_WINDOWS ? {} : { cwd: PROJ_ROOT }) },
      (err, stdout, stderr) => {
        if (err) {
          const parsed = _findJSON(stdout);
          if (parsed) return resolve(parsed);
          return reject(new Error(stderr.trim() || stdout.trim() || err.message));
        }
        const parsed = _findJSON(stdout);
        if (parsed) return resolve(parsed);
        reject(new Error(`CLI output is not valid JSON: ${stdout.slice(0, 200)}`));
      },
    );
  });
}

/** Find and parse a JSON object from mixed output (last {}-line wins). */
function _findJSON(text) {
  if (!text) return null;
  const lines = text.trim().split(/\r?\n/);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line.startsWith("{")) {
      try { return JSON.parse(line); } catch (_) { /* continue */ }
    }
  }
  try { return JSON.parse(text.trim()); } catch (_) { return null; }
}

/** Read JSON body from incoming POST request. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error("Invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

/** Parse URL pathname and search params. */
function parseURL(req) {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  return url;
}

/* ── Route handlers ── */

async function handleState(req, res) {
  try {
    const [doctorData, listData] = await Promise.all([
      execCLI(["doctor"]),
      execCLI(["list"]),
    ]);

    const gpu = doctorData.gpu || { detected: false };
    /* Convert vram_total_gb to mb for frontend compatibility */
    const gpuInfo = {
      name: gpu.name || "",
      vramTotal: gpu.vram_total_gb ? Math.round(gpu.vram_total_gb * 1024) : 0,
      vramUsed: gpu.vram_free_gb
        ? Math.round((gpu.vram_total_gb - gpu.vram_free_gb) * 1024)
        : 0,
      temperature: gpu.temperature || 0,
      utilization: gpu.utilization || 0,
      clockCore: gpu.clock_core || 0,
      clockMem: gpu.clock_mem || 0,
      detected: gpu.detected || false,
    };

    const engines = (listData.engines || []).map((e) => ({
      name: e.model_id || "",
      status: "stopped",
      model: e.model_id || null,
      port: null,
    }));

    sendJSON(res, {
      gpu: gpuInfo,
      engines,
      cliAvailable: true,
      cliError: null,
      cliVersion: doctorData.version || null,
    });
  } catch (err) {
    sendJSON(res, {
      gpu: {
        name: "",
        vramTotal: 0,
        vramUsed: 0,
        temperature: 0,
        utilization: 0,
        clockCore: 0,
        clockMem: 0,
        detected: false,
      },
      engines: [],
      cliAvailable: false,
      cliError: err.message,
      cliVersion: null,
    });
  }
}

async function handleOperation(req, res, opId) {
  const cliCmd = OP_MAP[opId];
  if (!cliCmd) {
    return sendError(res, `Unknown operation: ${opId}`, 400);
  }

  let body = {};
  try {
    body = await readBody(req);
  } catch (_) {
    /* no body, that's fine */
  }

  const args = [cliCmd];
  /* Pass through arguments from body */
  if (body.args) args.push(...body.args);

  try {
    const result = await execCLI(args);
    if (result && result.ok !== undefined) {
      sendJSON(res, {
        ok: result.ok,
        output: result.output || "",
        error: result.error || null,
      });
    } else {
      sendJSON(res, { ok: true, output: JSON.stringify(result), error: null });
    }
  } catch (err) {
    sendJSON(res, { ok: false, output: "", error: err.message });
  }
}

async function handleChat(req, res) {
  let body;
  try {
    body = await readBody(req);
  } catch (_) {
    return sendError(res, "Invalid JSON body", 400);
  }

  const prompt = body.prompt || body.message || "";
  if (!prompt) return sendError(res, "Prompt is required", 400);

  /* Streaming chat via SSE. Calls 'rtxforge run' in one-shot JSON mode. */
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });

  try {
    const modelArgs = body.model_id ? [body.model_id] : [];
    const result = await execCLI(["run", ...modelArgs, "--json"]);
    if (result && result.ok) {
      const tokens = (result.output || "").split(/(\s+)/);
      for (const token of tokens) {
        res.write(`data: ${JSON.stringify({ token })}\n\n`);
      }
    } else {
      res.write(
        `data: ${JSON.stringify({ error: (result && result.error) || "Generation failed" })}\n\n`,
      );
    }
  } catch (err) {
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
  }
  res.write("data: [DONE]\n\n");
  res.end();
}

/* ── Server ── */

http
  .createServer(async (req, res) => {
    const url = parseURL(req);
    const pathname = url.pathname;

    try {
      /* API routes */
      if (pathname === "/api/state" && req.method === "GET") {
        return await handleState(req, res);
      }

      if (pathname.startsWith("/api/operation/") && req.method === "POST") {
        const opId = pathname.slice("/api/operation/".length);
        return await handleOperation(req, res, opId);
      }

      if (pathname === "/api/chat" && req.method === "POST") {
        return await handleChat(req, res);
      }

      /* Static files */
      let filePath = path.join(ROOT, pathname === "/" ? "index.html" : pathname);
      if (!filePath.startsWith(ROOT)) {
        res.writeHead(403);
        return res.end("Forbidden");
      }

      const ext = path.extname(filePath);
      const mime = MIME[ext] || "application/octet-stream";

      fs.readFile(filePath, (err, data) => {
        if (err) {
          /* SPA fallback: serve index.html for unknown paths */
          fs.readFile(path.join(ROOT, "index.html"), (err2, indexData) => {
            if (err2) {
              res.writeHead(404);
              return res.end("Not found");
            }
            res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
            res.end(indexData);
          });
          return;
        }
        res.writeHead(200, { "Content-Type": mime });
        res.end(data);
      });
    } catch (err) {
      sendError(res, err.message);
    }
  })
  .listen(PORT, "127.0.0.1", () => {
    console.log(`RTXMF UI → http://127.0.0.1:${PORT}`);
  });
