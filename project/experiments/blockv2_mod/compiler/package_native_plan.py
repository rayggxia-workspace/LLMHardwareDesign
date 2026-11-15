import json,sys
from pathlib import Path
from native_machine_package import package
plan=json.loads(Path(sys.argv[1]).read_text())
print(json.dumps(package(plan,Path(sys.argv[2]),plan['search_hardware']['topology_id'],json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv)>3 else None)),flush=True)
