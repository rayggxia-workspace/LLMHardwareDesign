"""Record management/protocol checks, never an inference acceptance certificate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from analyze import HERE,ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,cmd in (("management",[sys.executable,"-B","scripts/check_project.py"]),
                     ("protocol",[sys.executable,"-B",str(HERE/"test_catalog.py")]),
                     ("whitespace",["git","diff","--check"])):
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,errors="replace",timeout=30)
        data=(r.stdout+r.stderr).encode("utf-8");log=a.output/(name+".log");log.write_bytes(data)
        rows.append({"name":name,"argv":cmd,"returncode":r.returncode,"file":log.name,"sha256":hashlib.sha256(data).hexdigest()})
    report={"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "kind":"metadata/protocol only, no neural inference", "checks":rows,"passed":all(x["returncode"]==0 for x in rows)}
    (a.output/"checks.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
    print({x["name"]:x["returncode"] for x in rows})
    if not report["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
