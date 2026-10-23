"""Independent source-byte, payload, resource-bound and physical-traffic audit."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from capture import validate,replay_linear
from record import HERE,ROOT,provenance,digest,save


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    checks=Counter();report_paths=[HERE/"inputs/capture-record.json",HERE/"results/numerical.json",HERE/"results/placement.json",HERE/"results-v2/numerical.json",HERE/"results-v2/refinement.json",HERE/"results-v2/refinement-v3.json",HERE/"results-v2/placement-v4.json",ROOT/"work/Liangruizhi/33/checks/checks.json",ROOT/"work/Liangruizhi/33/checks-v2/checks.json",ROOT/"work/Liangruizhi/33/checks-v3/checks.json",ROOT/"work/Liangruizhi/33/checks-v4/checks.json",ROOT/"work/Liangruizhi/33/rtl/rtl.json"]
    source_cache={}
    for path in report_paths:
        doc=json.loads(path.read_text(encoding="utf-8"));prod=doc["producer"]
        assert prod["source_dirty"] is False,(path,"dirty source")
        for source,wanted in prod["source_sha256"].items():
            key=(prod["code_commit"],source)
            if key not in source_cache:
                blob=subprocess.check_output(["git","show",key[0]+":"+key[1]],cwd=ROOT)
                source_cache[key]=hashlib.sha256(blob).hexdigest()
            assert source_cache[key]==wanted,(path,source,"source bytes differ")
            checks["source_version_bindings"]+=1
        for cmd in doc.get("checks",doc.get("commands",[])):
            assert digest(path.parent/cmd["log"])==cmd["sha256"]
            assert cmd["returncode"]==0
            checks["raw_log_bindings"]+=1
    receipt=json.loads(report_paths[0].read_text(encoding="utf-8"));raw=HERE/"inputs"/receipt["file"]["path"]
    assert digest(raw)==receipt["file"]["sha256"] and raw.stat().st_size==receipt["file"]["bytes"]
    for directory,commit in (("results","db74f40e3c91783e0a64b17cf95df000e06223d0"),("results-v2","60cc1b7f74d01c5bb05e21e23ad93b5c6077d6e5")):
        package=HERE/directory/"capture-example"
        doc,arrays=validate(package,commit,"c1899de289a04d12100db370d81485cdf75e47ca")
        checks["captured_payloads"]+=len(arrays)
        checks["exact_integer_outputs"]+=replay_linear(package)["integer_outputs_replayed"]
    graph=json.loads((HERE/"results-v2/placement-v4.json").read_text(encoding="utf-8"))
    assert graph["inventory"]["state_working_bytes"]==32768
    reasons=Counter()
    for c in graph["candidates"]:
        for reason in c["rejected"]:reasons[reason]+=1
        nr=c["tile_rows"];tiles=32//nr;elem=nr*16;window=c["window"]
        params=16*5*(32 if c["scale_mode"]=="dynamic_row" else 1)
        banks=[16384+window*nr*1024,0]
        banks[c["state_bank"]]+=c["state_cells"]*(c["state_bits"]//8)
        banks[0 if c["rq"]=="near" else 1]+=params
        banks=[x+window*elem*4 for x in banks]
        assert banks==c["bank_resident_bytes"] and params==c["rq_parameter_bytes"]
        assert c["boundary_bytes"]==window*elem*5
        assert c["state_working_bytes"]==c["state_cells"]*(c["state_bits"]//8)
        if c["feasible"]:assert c["state_working_bytes"]<=32768
        checks["capacity_metadata_cases"]+=1
        if not c["feasible"]:continue
        assert c["cycles"]>=max(c["resource_busy"].values())
        assert c["resource_busy"]["matrix"]==2048
        assert c["resource_busy"]["rq"]==32*16*28
        expected_v=32*(c["state_cells"]+1)+(32*16*3+tiles if c["partial"]=="cross" else 0)
        assert c["resource_busy"]["vector"]==expected_v
        packet=lambda n:(n+63)//64
        if c["partial"]=="internal":
            link=tiles*packet(elem if c["rq"]=="near" else elem*4)
        else:
            link=tiles*4*packet(elem*4)
            if c["rq"]=="near":link+=tiles*(packet(elem*4)+packet(elem))
        if c["state_bank"]==0:link+=2*32*packet(c["state_cells"]*(c["state_bits"]//8))
        assert c["link_beats"]==link and c["traffic_bytes"]["link_physical"]==link*64
        checks["independent_traffic_and_compute_cases"]+=1
    checks["input_capture_sha"]+=1
    save(a.output,{"producer":provenance("audit_results.py"),"passed":True,"checks":dict(checks),"rejections":dict(reasons),
                   "limits":"Audits v4 graph with explicit 32KiB private state scratch. Initial placement.json omitted that hardware budget and is retained as superseded, not a complete finite-buffer result. Not physical or full-model accuracy audit"})
    print(dict(checks));print(dict(reasons))


if __name__=="__main__":main()
