# Archived-stage diagnostic only. Stage boundaries/order originate in the archive.
# This program does not implement whole-graph mapping or generate fresh machine code.
"""Replan every stage of a sealed full-model native graph with Algo1."""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import tarfile

from run import compile_event_ir


def comparable_program(program):
    result = deepcopy(program)
    result.pop("source", None)
    for commands in result["locals"].values():
        for command in commands:
            if command.get("service") in ("rms", "add", "bias"):
                command["read"] = sorted(command["read"], key=lambda operand: (
                    operand["site"], operand["address"], operand["value"]))
    return result


def compile_all(archive, output):
    output.mkdir()
    receipts = []
    with tarfile.open(archive) as package:
        names = set(package.getnames())
        def read(name):
            return package.extractfile("./" + name).read()
        stages = json.loads(read("stages.json"))
        for stage in stages["stages"]:
            root = stage["root"]
            proof = read(root + "/proof.sha256")
            if sha256(proof).hexdigest() != stage["proof_sha256"]:
                raise ValueError(f"invalid proof for {root}")
            prefix = root if stage["bundle"] == "." else root + "/" + stage["bundle"]
            candidates = [prefix + "/" + filename for filename in ("compile.json", "algo1-result.json")]
            source = next(name for name in candidates if "./" + name in names)
            raw = read(source)
            seals = dict(line.split("  ", 1)[::-1] for line in proof.decode().splitlines())
            if sha256(raw).hexdigest() != seals[source.removeprefix(root + "/")]:
                raise ValueError(f"invalid compiler input seal for {root}")
            prior = json.loads(raw)
            result = compile_event_ir(prior["event_ir"], prior["resolved_hardware"], emit_outputs=True)
            if result["status"] != "planned" or not result["verification"]["passed"]:
                raise ValueError(f"Algo1 failed stage {root}: {result['status']}")
            # Machine-code cache reuse is permitted only for identical symbolic commands,
            # addresses and dependencies. A changed schedule requires fresh native lowering.
            old = prior["outputs"]["program"]
            new = result["outputs"]["program"]
            equal = comparable_program(old) == comparable_program(new)
            if not equal:
                (output / "changed-program.json").write_text(json.dumps(
                    {"stage":root,"old":old,"new":new},indent=2)+"\n")
                raise ValueError(f"native lowering required for changed commands at {root}")
            dest = output / root
            dest.mkdir(parents=True)
            (dest / "algo1-result.json").write_text(json.dumps(result, indent=2) + "\n")
            receipts.append({"stage": root, "status": result["status"],
                             "instructions_match_sealed_encoding": equal,
                             "input_sha256": sha256(raw).hexdigest(),
                             "tasks": len(prior["event_ir"]["tasks"])})
            print(root, len(receipts), flush=True)
    report = {"status":"all_stages_replanned", "stages":receipts,
              "machine_deployment_ready":False,
              "remaining_gate":"RTL dispatch, phase control and joint deployment binding"}
    (output / "report.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("archive","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    compile_all(args.archive,args.output)
