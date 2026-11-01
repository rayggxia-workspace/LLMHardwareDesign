# -*- coding: utf-8 -*-
"""Local ModelSim runner. Writes only --output; reads declared task sources.

No SSH/network/install/PATH changes, no license/config/credential inspection.
Use an independent output directory for every evidence run.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
NATIVE = ["project/rtl/block_v2/block_v2_m.sv",
          "project/rtl/block_feed_v1/block_feed_loader.sv",
          "project/rtl/block_feed_v1/block_feed_s16k.sv",
          "project/rtl/block_feed_v1/block_feed_s_macro.sv",
          "project/rtl/block_v1/transaction6k.sv"]
SOURCE_REF = "707878621b2add4ed218b8c43df2e95c9a56e2ba"


def file_info(path):
    raw = path.read_bytes()
    return {"name": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()}


def utf8_log(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("mbcs", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tool-dir","--tool-root",dest="tool_root",type=Path,default=Path("D:/EDA/modeltech64_2020.4/win64"))
    ap.add_argument("--root","--source-root",dest="source_root",type=Path,default=Path("."))
    ap.add_argument("--core-root",type=Path)
    ap.add_argument("--s-ctrl-root",type=Path)
    ap.add_argument("--tb-root",type=Path)
    ap.add_argument("--suite",choices=("smoke","native-compile","helper","mst","all"),default="all")
    ap.add_argument("--output-dir","--output",dest="output",type=Path,required=True)
    args = ap.parse_args()
    if args.core_root is None:
        args.core_root=args.source_root/"project/rtl/block_connection_p2"
    if args.s_ctrl_root is None:
        args.s_ctrl_root=args.core_root
    if args.tb_root is None:
        args.tb_root=args.source_root/"project/tb/block_connection_p2"
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be new/empty; previous logs are never overwritten")
    out.mkdir(parents=True,exist_ok=True)
    snapshot = out/"source"; snapshot.mkdir()
    receipt = {"schema_version":1,"started_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "suite":args.suite,"source_ref":SOURCE_REF,"tool":{},"runs":[],"inputs":[],"case_ids":[],
               "host":{"python":platform.python_version(),"platform":platform.platform()},
               "scope":{"RTL_simulation_attempted":True,"physical_validation":False,
                        "whole_model_validation":False,"SSH_or_server_used":False}}
    receipt_path = out/"run-receipt.json"

    def save():
        receipt_path.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode("utf-8"))

    def run(label,command,required=True):
        entry = {"label":label,"argv":[str(x) for x in command],"working_directory":str(out),
                 "started_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            result = subprocess.run(entry["argv"],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            raw, code = result.stdout,result.returncode
        except (OSError,subprocess.TimeoutExpired) as error:
            raw,code = str(error).encode("utf-8"),-1
        text = utf8_log(raw)
        log = out/(label+".log"); log.write_bytes(text.encode("utf-8"))
        entry.update({"exit_code":code,"stdout_raw_sha256":hashlib.sha256(raw).hexdigest(),
                      "log":log.name,"log_sha256":hashlib.sha256(log.read_bytes()).hexdigest(),
                      "finished_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()})
        receipt["runs"].append(entry);save()
        print("{}: exit={} log={}".format(label,code,log),flush=True)
        if required and code != 0:
            raise RuntimeError(label+" failed; see recorded log")
        return text

    def copy_source(path,tag):
        data = path.read_bytes()
        target = snapshot/path.name
        if target.exists():
            raise RuntimeError("duplicate source basename: "+path.name)
        target.write_bytes(data)
        record = dict(file_info(target),origin=str(path.resolve()),scope=tag)
        if tag == "frozen_native_RTL":
            record["source_ref"] = SOURCE_REF
        receipt["inputs"].append(record)
        return target

    try:
        # Local minimal mapping. No reading/copying the installation modelsim.ini.
        (out/"modelsim.ini").write_bytes(b"[Library]\nwork = work\n\n[vsim]\nTranscriptFile = transcript\n")
        for tool in ("vlib","vlog","vsim"):
            path=args.tool_root/(tool+".exe")
            receipt["tool"][tool]=dict(file_info(path),path=str(path.resolve()))
        receipt["tool"]["vlog"]["version"]=run("vlog-version",[args.tool_root/"vlog.exe","-version"]).strip()
        receipt["tool"]["vsim"]["version"]=run("vsim-version",[args.tool_root/"vsim.exe","-version"]).strip()
        files=[]
        tops=[]
        if args.suite == "smoke":
            top="phase2_environment_smoke_tb"
            files.append(copy_source(args.tb_root/(top+".sv"),"testbench"))
            tops=[("smoke",top)]
        else:
            lock_path=args.source_root/"work/Melodydt/151/phase2-source-lock.json"
            lock=json.loads(lock_path.read_text(encoding="utf-8"))
            if lock["selected_PR144_ref"] != SOURCE_REF or len(lock["core_files"]) != 14:
                raise RuntimeError("unexpected core source-lock ref or file count")
            receipt["inputs"].append(dict(file_info(lock_path),scope="source_lock",origin=str(lock_path.resolve())))
            for item in lock["core_files"]:
                source=copy_source(args.source_root/item["path"],"frozen_native_RTL")
                if file_info(source)["sha256"] != item["sha256"] or file_info(source)["git_blob_sha1"] != item["sha"]:
                    raise RuntimeError("source lock mismatch: "+item["path"])
                if source.suffix==".sv":
                    files.append(source)
            receipt["core_compile_scope"]="14 locked source/include files; syntax compile only for N/E/G/R/legacy files"
            if args.suite != "native-compile":
                files.append(copy_source(args.s_ctrl_root/"block_p2_s_ctrl.sv","new_helper_RTL"))
            if args.suite in ("mst","all"):
                files.extend(copy_source(args.core_root/name,"new_MST_RTL") for name in ("block_p2_mother_rom.sv","block_p2_mst_top.sv"))
            for suite,top in (("helper","phase2_s_ctrl_tb"),("mst","phase2_mst_tb")):
                if args.suite in (suite,"all"):
                    files.append(copy_source(args.tb_root/(top+".sv"),"testbench"))
                    tops.append((suite,top))
        fixture=args.source_root/"work/Melodydt/151/phase1-mst-vectors.json"
        if fixture.exists():
            record=dict(file_info(fixture),origin=str(fixture.resolve()),scope="frozen_P1_literal_fixture")
            receipt["inputs"].append(record)
        receipt["inputs"].append(dict(file_info(Path(__file__).resolve()),scope="run_script"))
        save()
        run("vlib",[args.tool_root/"vlib.exe","work"])
        run("compile",[args.tool_root/"vlog.exe","-modelsimini","modelsim.ini","-sv","-work","work","+incdir+"+str(snapshot)]+files)
        receipt["native_compile_passed"]=args.suite!="smoke"
        receipt["pass_markers"]=[]
        for suite,top in tops:
            text=run("simulation-"+suite,[args.tool_root/"vsim.exe","-modelsimini","modelsim.ini","-c","-voptargs=+acc","-onfinish","stop","work."+top,
                                   "-do","onbreak {quit -code 2}; onerror {quit -code 3}; run -all; quit -code 0"])
            marker={"smoke":"PASS_P2_ENVIRONMENT_SMOKE","helper":"PASS_P2_S_CTRL","mst":"PASS_P2_MST"}[suite]
            if marker not in text or "FAIL_P2" in text or "Fatal:" in text:
                raise RuntimeError("simulation missing required PASS marker or contains FAIL/Fatal")
            receipt["pass_markers"].append(marker)
            receipt["case_ids"].extend(re.findall(r"CASE_PASS ([A-Z][A-Z0-9_]+)",text))
        receipt["status"]="PASS_REAL_RTL_SIMULATION" if tops else "PASS_NATIVE_SYNTAX_COMPILE_ONLY"
        receipt["scope"]["RTL_simulation_attempted"]=bool(tops)
    except Exception as error:
        receipt["status"]="FAILED_OR_BLOCKED"
        receipt["failure"]=str(error)
        save()
        raise
    finally:
        receipt["finished_at_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print("PASS actual RTL simulation: "+str(receipt_path),flush=True)


if __name__ == "__main__":
    main()
