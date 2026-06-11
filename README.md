<div align="center">

# RTX Model Forge

**Forge blazing-fast LLM engines for your NVIDIA RTX GPU**

Automatically download, quantize, and compile open-source language models into highly optimized TensorRT engines — no ML engineering expertise required.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TensorRT-LLM](https://img.shields.io/badge/TensorRT--LLM-1.3.0-76B900?style=flat-square&logo=nvidia&logoColor=white)](https://github.com/NVIDIA/TensorRT-LLM)
[![CUDA](https://img.shields.io/badge/CUDA-13.0-76B900?style=flat-square&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?style=flat-square&logo=linux&logoColor=black)](https://www.linux.org)
[![Package Manager](https://img.shields.io/badge/Managed%20by-uv-DE5FE9?style=flat-square)](https://github.com/astral-sh/uv)

</div>

---

## What is RTX Model Forge?

RTX Model Forge is a Linux CLI that orchestrates the full TensorRT-LLM compilation pipeline for NVIDIA RTX GPUs (30, 40, and 50 series). It automatically detects your GPU architecture, selects the optimal quantization format, downloads model weights from Hugging Face, and compiles two dedicated TensorRT engines — one for interactive chat and one for multi-client API serving.

The result: **2-4x faster inference than generic tools like Ollama**, with zero manual tuning.

---

## Features

- **Automatic quantization selection** — GPU architecture and VRAM-aware cascade (FP8, INT8, INT4-AWQ, FP4)
- **Dual-engine compilation** — dedicated engines for low-latency chat and high-throughput API serving
- **OpenAI-compatible REST API** — drop-in replacement for OpenAI clients via `rtxforge serve`
- **Hugging Face integration** — downloads model weights with gated model support (Llama, Gemma, etc.)
- **GPU health diagnostics** — validates drivers, CUDA toolkit, and TensorRT-LLM with `rtxforge doctor`
- **Rich terminal UI** — progress indicators, structured tables, and clear error guidance
- **Secure token storage** — HF credentials saved with 600 permissions under `~/.rtxmodelforge/`

---

## GPU Support

| GPU Series | Architecture  | SM Version | Primary Quantization | Fallback        |
|------------|---------------|:----------:|----------------------|-----------------|
| RTX 50xx   | Blackwell     | 100+       | FP8                  | FP4 (NVFP4)     |
| RTX 40xx   | Ada Lovelace  | 89         | FP8                  | INT8 -> INT4 AWQ|
| RTX 30xx   | Ampere        | 80-88      | INT8                  | INT4 AWQ        |

RTX Model Forge explains *why* each quantization format was chosen for your specific GPU and VRAM configuration.

---

## Quick Start

### Prerequisites

- Linux (x86_64)
- Python 3.12+
- NVIDIA driver >= 525
- CUDA Toolkit >= 12.x (`nvcc` available in PATH)
- An NVIDIA RTX 30, 40, or 50 series GPU

### Installation

```sh
pip install rtxmodelforge
```

Or with [uv](https://github.com/astral-sh/uv) (recommended):

```sh
uv tool install rtxmodelforge
```

For development:

```sh
git clone https://github.com/k3lvin-dev/rtxmodelforge
cd rtxmodelforge
pip install -e ".[dev]"
```

### 4-Step Workflow

**1. Authenticate with Hugging Face** (required for gated models like Llama)

```sh
rtxforge login
```

**2. Verify your system is ready**

```sh
rtxforge doctor
```

```
Component          Status    Details
GPU                OK        NVIDIA GeForce RTX 4090 (24 GB VRAM, SM 89)
NVIDIA Driver      OK        550.54.14
CUDA Toolkit       OK        12.4.0
TensorRT-LLM       OK        1.3.0rc10
HuggingFace Token  OK        Authenticated as your-username
```

**3. Build an optimized engine**

```sh
rtxforge build meta-llama/Llama-3.1-8B-Instruct
```

```
Stage 1/5  Downloading model weights ...  done  (4.2 GB)
Stage 2/5  Parsing model configuration ... done  (8.0B params)
Stage 3/5  Calculating build plan ...      done  (FP8, seq=4096, batch=1)
Stage 4/5  Compiling chat engine ...       done  (3m 14s)
Stage 5/5  Compiling serve engine ...      done  (3m 07s)

Engines saved to ~/.rtxmodelforge/engines/meta-llama/Llama-3.1-8B-Instruct/
```

**4. Run inference**

```sh
# Interactive terminal chat
rtxforge chat meta-llama/Llama-3.1-8B-Instruct

# OpenAI-compatible REST server
rtxforge serve meta-llama/Llama-3.1-8B-Instruct
```

---

## Commands Reference

| Command             | Description                                              | Example                                          |
|---------------------|----------------------------------------------------------|--------------------------------------------------|
| `rtxforge login`    | Authenticate with Hugging Face and save token            | `rtxforge login`                                 |
| `rtxforge doctor`   | Run GPU, driver, CUDA, and toolkit health checks         | `rtxforge doctor`                                |
| `rtxforge build`    | Download, quantize, and compile a model into TRT engines | `rtxforge build mistralai/Mistral-7B-v0.1`       |
| `rtxforge chat`     | Launch interactive terminal chat from a compiled engine  | `rtxforge chat mistralai/Mistral-7B-v0.1`        |
| `rtxforge serve`    | Start OpenAI-compatible REST API server                  | `rtxforge serve mistralai/Mistral-7B-v0.1 --port 8000` |
| `rtxforge list`     | List all compiled engines with metadata                  | `rtxforge list`                                  |
| `rtxforge delete`   | Remove a compiled engine from disk                       | `rtxforge delete mistralai/Mistral-7B-v0.1`      |

---

## How It Works

RTX Model Forge runs a 5-stage build pipeline to produce production-ready TensorRT engines:

```
1. Download      Pull model weights and tokenizer from Hugging Face
      |
      v
2. Profile       Parse config.json, estimate parameter count and VRAM footprint
      |
      v
3. Plan          Select quantization format, compute KV cache size,
                 set batch size and max sequence length
      |
      v
4. Chat Engine   Compile a batch=1, max-sequence TRT engine
                 optimized for minimum latency (interactive use)
      |
      v
5. Serve Engine  Compile a dynamic-batch TRT engine
                 optimized for throughput (multi-client API)
```

Engine metadata (GPU model, quantization, VRAM usage, build timestamp) is stored alongside each engine for traceability.

---

## Architecture

| Layer         | Component                                    | Role                                           |
|---------------|----------------------------------------------|------------------------------------------------|
| CLI           | [Typer](https://typer.tiangolo.com) 0.15     | Command definitions and argument parsing       |
| UI            | [Rich](https://rich.readthedocs.io) 13.9     | Tables, progress bars, styled terminal output  |
| GPU Profiling | [pynvml](https://github.com/gpuopenanalytics/pynvml) 12.0 | NVIDIA GPU detection and VRAM query |
| Model Hub     | [huggingface-hub](https://huggingface.co/docs/huggingface_hub) 0.28 | Weight downloads, token auth |
| Compilation   | [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) 1.3 | LLM engine compilation and inference |
| Tokenization  | [transformers](https://huggingface.co/docs/transformers) 4.48 | Tokenizer loading and model config parsing |
| Config        | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 2.10 | Typed configuration management |
| Storage       | TOML (`~/.rtxmodelforge/config.toml`)        | Credentials and engine directory configuration |

---

## Requirements

```
Linux (x86_64)
Python >= 3.12
NVIDIA GPU: RTX 3000, 4000, or 5000 series
NVIDIA Driver >= 525
CUDA Toolkit >= 12.x
libopenmpi-dev (for multi-GPU support)
Hugging Face account (free; required for gated models)
```

Minimum VRAM recommendations by model size:

| Model Size | Minimum VRAM |
|:----------:|:------------:|
| 7B         | 8 GB         |
| 13B        | 16 GB        |
| 34B        | 24 GB        |
| 70B        | 48 GB        |

---

## Development

```sh
# Clone and install with dev dependencies
git clone https://github.com/k3lvin-dev/rtxmodelforge
cd rtxmodelforge
pip install -e ".[dev]"

# Run linting and type checks
format

# Run tests
pytest
```

### Code Quality

| Tool    | Purpose               | Config                         |
|---------|-----------------------|--------------------------------|
| ruff    | Linting (E,F,I,B,C4,ARG) | `pyproject.toml`            |
| pyright | Type checking (basic) | `pyproject.toml`               |
| pytest  | Unit tests            | `pyproject.toml`               |

---

## License

This project is licensed under the MIT License.

---

<div align="center">

Built for NVIDIA RTX users who want maximum performance without the complexity.

</div>
