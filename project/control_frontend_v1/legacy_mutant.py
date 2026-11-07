"""Materialize pinned legacy behavior with test-only interface compatibility."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=("old_u_e", "old_cf"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    expected = json.loads((HERE / "mutants.json").read_text())["entries"][a.kind]
    data = a.source.read_bytes()
    digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if digest != expected["git_blob"]:
        raise ValueError("legacy source pin mismatch")
    if a.kind == "old_u_e":
        text = data.decode("utf-8")
        anchor = "    input wire [3:0] cmd_op,"
        if text.count(anchor)!=1:
            raise ValueError("legacy E input declaration changed")
        data = text.replace(anchor, "    input wire [1:0] cmd_sources,\n"+anchor).encode("utf-8")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(data)
    print(json.dumps({"kind":a.kind,"source_blob":digest,
                      "output_sha256":hashlib.sha256(data).hexdigest(),
                      "compatibility":expected.get("compatibility","none")}))


if __name__ == "__main__":
    main()
