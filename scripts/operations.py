#!/usr/bin/env python3
"""Repository convenience entry point; the installed skill has its own self-contained CLI."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "skills/koro-operations/scripts/operations.py"), run_name="__main__")
