from __future__ import annotations

import subprocess
import sys


def run() -> None:
    """Roda Ruff e Pyright em sequência."""
    print("--- 🖌️ Formatação e Lint (Ruff) ---")
    try:
        # Formatação
        subprocess.run(["uv", "run", "ruff", "format", "src"], check=True)
        # Linting e Correção
        subprocess.run(["uv", "run", "ruff", "check", "src", "--fix"], check=True)

        print("\n--- 🧠 Verificação de Tipagem (Pyright) ---")
        # Tipagem
        subprocess.run(["uv", "run", "pyright", "src"], check=True)

        print("\n[bold green]✔ Código está CLEAN, DRY e TIPO-SEGURO![/bold green]")

    except subprocess.CalledProcessError as e:
        print(f"\n[red]✘ Erro durante a validação:[/red] {e}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    run()
