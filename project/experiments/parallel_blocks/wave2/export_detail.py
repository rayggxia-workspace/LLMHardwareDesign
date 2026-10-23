"""Export actual detailed obstructions; never remove macro geometry."""
import json
from pathlib import Path
import subprocess

meta = json.loads(Path("experiment.json").read_text())
result = Path.cwd() / "flow/results/nangate45" / ("parallel_" + meta["case"].replace("-", "_")) / "base"
script = "read_db {" + str(result / "6_final.odb") + "}\n"
script += "write_abstract_lef -bloat_factor 0 {" + str(result / (meta["top"] + ".detailed.lef")) + "}\n"
Path("export-detail.tcl").write_text(script)
with Path("export-detail.log").open("w") as log:
    subprocess.run(["openroad", "-exit", "export-detail.tcl"], stdout=log, stderr=subprocess.STDOUT, check=True)
