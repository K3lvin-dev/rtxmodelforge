from __future__ import annotations

import subprocess
import sys


def run() -> None:
    """Run Ruff format and check with fixes."""
    print("--- Formatting and Linting (Ruff) ---")
    try:
        # Formatting
        subprocess.run(["ruff", "format", "."], check=True)
        # Linting and Fixes
        subprocess.run(["ruff", "check", ".", "--fix"], check=True)

        print("\nFormatting and fixes successful.")

    except subprocess.CalledProcessError as e:
        print(f"\nError during validation: {e}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    run()
