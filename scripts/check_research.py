"""Run the two research suites with the same explicitly selected interpreter."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
for suite in ("frozen_routing", "endpoint_ablation"):
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                    f"project/experiments/{suite}", "-p", "test_*.py", "-v"],
                   cwd=root, check=True)
