/* RTX Model Forge CLI Interface
   Talks to the Node.js API proxy which forwards to the Python CLI.
   Every operation is an HTTP request. */

import type {
  CommandResult,
  OperationId,
  SystemState,
} from "../types";

/* Public API */

export async function fetchSystemState(): Promise<SystemState> {
  try {
    const res = await fetch("/api/state");
    if (!res.ok) {
      return {
        gpu: { name: "", vramTotal: 0, vramUsed: 0, temperature: 0, utilization: 0, clockCore: 0, clockMem: 0, detected: false },
        engines: [],
        cliAvailable: false,
        cliError: `HTTP ${res.status}`,
        cliVersion: null,
      };
    }
    return (await res.json()) as SystemState;
  } catch (err) {
    return {
      gpu: { name: "", vramTotal: 0, vramUsed: 0, temperature: 0, utilization: 0, clockCore: 0, clockMem: 0, detected: false },
      engines: [],
      cliAvailable: false,
      cliError: err instanceof Error ? err.message : "CLI unreachable",
      cliVersion: null,
    };
  }
}

export async function executeCommand(
  command: OperationId,
  args: string[] = [],
): Promise<CommandResult> {
  try {
    const res = await fetch(`/api/operation/${command}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
    });
    return (await res.json()) as CommandResult;
  } catch (err) {
    return {
      ok: false,
      output: "",
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

export async function checkCliHealth(): Promise<boolean> {
  try {
    const state = await fetchSystemState();
    return state.cliAvailable;
  } catch {
    return false;
  }
}

export function streamChat(
  prompt: string,
  onToken: (token: string) => void,
  onComplete: () => void,
  onError: (err: Error) => void,
): () => void {
  const controller = new AbortController();

  fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.body) {
        onError(new Error("No response body"));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop()!;

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              onComplete();
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.token) onToken(parsed.token);
            } catch (_) {
              /* skip unparseable lines */
            }
          }
        }
      }
      onComplete();
    })
    .catch((err) => {
      if (!controller.signal.aborted) onError(err);
    });

  return () => {
    controller.abort();
  };
}
