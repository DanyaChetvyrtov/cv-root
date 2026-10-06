#!/usr/bin/env python3
"""Run the full BFF acceptance test from the single project entry point."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    script = Path(__file__).resolve().parents[1] / "keycloak-integration-test" / "scripts" / "smoke_test.py"
    runpy.run_path(str(script), run_name="__main__")
