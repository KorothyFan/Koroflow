#!/usr/bin/env python3
"""Repository entry for the independently installable KoroFlow core."""
from pathlib import Path
import runpy
import sys

scripts = Path(__file__).resolve().parents[1] / "skills/koroflow/scripts"
sys.path.insert(0, str(scripts))
runpy.run_path(str(scripts / "workflow.py"), run_name="__main__")
