"""Verify explicit G-only/allocated-CPU specializations of main access gates.

No geometry, rule, source-file or electrical checks are removed. Original
main files stay unchanged. The two local derived modules have an exact,
machine-checked textual diff: use 10/12 allocated CPUs, select G and its
accepted-delivery adapter, and rebuild the explicit edge-staggered pin plan.
The same two advisory I/O slots use a new, narrower issue250-only namespace;
the historical issue143 helper correctly rejects new unrelated directories.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
RECIPES = {
    "g_geometry.py":("project/experiments/block_v2/actual_geometry.py",[
        ("from io_slots import file_sha,slot", "from io_slots import file_sha\n    from g_slots import slot"),
        ("assert cpus==16 and kind in ('m','n','e','g','r','s','t')", "assert cpus in (10,12) and kind=='g'"),
        ("script='set_thread_count 16\\n", "script='set_thread_count '+str(cpus)+'\\n")]),
    "g_escape.py":("project/experiments/block_feed_v1/escape.py",[
        ("from deliver import accepted", "from g_deliver import accepted"),
        ("from pins import generate", "from g_pins import generate"),
        ("assert cpus==16 and kind in 'mvrst'", "assert cpus in (10,12) and kind=='g'"),
        ("script='set_thread_count 16\\n", "script='set_thread_count '+str(cpus)+'\\n")])}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(write=False):
    rows = {}
    for target,(original,replacements) in RECIPES.items():
        raw = (ROOT/original).read_bytes()
        text = raw.decode()
        for before,after in replacements:
            assert text.count(before)==1, (original,before)
            text=text.replace(before,after)
        data=text.encode()
        destination=HERE/target
        if write:
            destination.write_bytes(data)
        assert destination.read_bytes()==data
        rows[target]=dict(original=original,original_sha256=digest(raw),derived_sha256=digest(data),
            replacements=[dict(before=a,after=b) for a,b in replacements])
    result=dict(passed=True,profiles=rows,scope=__doc__)
    path=HERE/"profile-sources.json"
    if write:
        path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    assert json.loads(path.read_text())==result
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    print(json.dumps(verify(args.write)))
