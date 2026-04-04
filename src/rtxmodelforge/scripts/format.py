from __future__ import annotations

import subprocess
import sys


def run() -> None:
    """Run Ruff and Pyright in sequence."""
    print("--- Formatting and Linting (Ruff) ---")
    try:
        # Formatting
        subprocess.run(["uv", "run", "ruff", "format", "src"], check=True)
        # Linting and Fixes
        subprocess.run(["uv", "run", "ruff", "check", "src", "--fix"], check=True)

        print("\n--- Type Checking (Pyright) ---")
        # Type Checking
        subprocess.run(["uv", "run", "pyright", "src"], check=True)

        print("\nValidation successful.")

    except subprocess.CalledProcessError as e:
        print(f"\nError during validation: {e}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    run()
