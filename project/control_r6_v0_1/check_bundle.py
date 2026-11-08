"""Mutate rehashed, structurally legal bundles to exercise the IR comparison."""
from copy import deepcopy
import json

from task_ir import HERE, IRValidationError, require
from verify_bundle import image, verify


def check():
    ir = (HERE / "examples/split_wait.json").read_bytes()
    original = json.loads((HERE / "generated/split_wait.bundle.json").read_text(encoding="utf-8"))
    verify(ir, original)
    cases = [
        ("different_s_address", "local0", "LC0.object"),
        ("different_ingress_edge", "local0", "LC0.transfer"),
        ("different_local_credit", "local0", "LC0.transfer"),
        ("different_ready_scalar", "local1", "LC1.ready"),
        ("different_mother_register", "mother", "mother.event"),
        ("joined_instead_of_split", "mother", "mother.wait"),
    ]
    rejected = {}
    for name, role, diagnostic in cases:
        mutant = deepcopy(original)
        parsed = image.parse_image(bytes.fromhex(mutant["images_hex"][role]))
        header, program = parsed["header"], parsed["program"]
        records = {k: v for k, v in parsed["records"].items() if k != "instruction"}
        if name == "different_s_address":
            records["object"][0]["base_bytes"] -= 16
        elif name == "different_ingress_edge":
            records["transfer"][0]["edge_id"] += 1
        elif name == "different_local_credit":
            program[1]["b"] = 0
            program[2]["x"] = 1
        elif name == "different_ready_scalar":
            next(i for i in program if i["op"] == "L_MOVI")["x"] ^= 1
        elif name == "different_mother_register":
            next(i for i in program if i["op"] == "G_EVENT")["a"] ^= 1
        elif name == "joined_instead_of_split":
            program[3]["x"] |= program.pop(4)["x"]
        changed = image.assemble_image(parsed["role"], program, records,
                                       header["program_image_id"], header["resource_mask"])
        mutant["images_hex"][role] = changed.hex()
        mutant["manifest"]["images"][role].update(bytes=len(changed), sha256=image.digest(changed))
        mutant["manifest_sha256"] = image.manifest_digest(mutant["manifest"])
        image.validate_bundle(mutant["manifest"], {k: bytes.fromhex(v) for k, v in mutant["images_hex"].items()})
        try:
            verify(ir, mutant)
        except IRValidationError as exc:
            require(str(exc).startswith(diagnostic + ":"), name, f"unexpected diagnostic: {exc}")
            rejected[name] = str(exc)
        else:
            raise RuntimeError(f"independent verifier accepted {name}")
    return rejected


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
