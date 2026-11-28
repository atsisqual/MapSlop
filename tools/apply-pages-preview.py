#!/usr/bin/env python3
"""Materialize the minimal Xclipse fallback for Pages branch preview."""
from pathlib import Path
import subprocess,sys
subprocess.run([sys.executable,str(Path(__file__).with_name("apply-xclipse-fallback.py")),sys.argv[1]],check=True)
