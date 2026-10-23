"""Record actual meaningful checks and their exact source provenance."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from record import HERE,ROOT,provenance,digest,save


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    records=[]
    for name,cmd in (("management",[sys.executable,"-B","scripts/check_project.py"]),
                     ("integer",[sys.executable,"-B",str(HERE/"test_integer.py")]),
                     ("placement",[sys.executable,"-B",str(HERE/"test_placement.py")]),
                     ("whitespace",["git","diff","--check"])):
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,errors="replace",timeout=60)
        log=a.output/(name+".log");log.write_text(r.stdout+r.stderr,encoding="utf-8")
        records.append({"name":name,"argv":cmd,"returncode":r.returncode,"log":log.name,"sha256":digest(log)})
    save(a.output/"checks.json",{"producer":provenance("run_checks.py"),"checks":records,"passed":all(r["returncode"]==0 for r in records)})
    print({r["name"]:r["returncode"] for r in records})
    if any(r["returncode"] for r in records):raise SystemExit(1)


if __name__=="__main__":main()
