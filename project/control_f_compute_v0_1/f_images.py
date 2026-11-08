"""Build and admit only the first fixed-wiring F control image pair."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT / "control_p_compute_v0_1"))
from run_a2 import assemble, CAPACITY
from image import codec

MANIFEST = json.loads((HERE / "trial_bindings.json").read_bytes())
F = MANIFEST["profiles"]["F"]
ABI, TOPOLOGY, BLOCK_TYPE = F["abi"], F["topology"], F["block_type"]
RESOURCE = F["service_resource"]
BYPASS, ADD = (int(op, 16) for op in F["services"])
MOTHER_ID, LOCAL_ID = 17920, 17921


def word_addresses(a, b, dst, use_add):
    return (a, b, dst) if use_add else (a, dst)


def images(a=5, b=0, dst=19, use_add=False):
    addresses = word_addresses(a, b, dst, use_add)
    if any(not 0 <= v < 1024 for v in addresses) or len(set(addresses)) != len(addresses):
        raise ValueError("F word address out of range or aliased")
    if not use_add and b != 0:
        raise ValueError("F bypass addend must be zero")
    op = ADD if use_add else BYPASS
    mask = F["services"][f"0x{op:04x}"]["resources"]
    mother = assemble("mother", [dict(op="G_CALL", a=0, b=2, c=0),
                                 dict(op="G_WAIT", x=4), dict(op="G_END")], {},
                      MOTHER_ID, 0, ABI, TOPOLOGY)
    task = dict(block_type=BLOCK_TYPE, entry_pc=0, max_steps=3, required_resources=mask,
                program_image_id=LOCAL_ID, topology_id=TOPOLOGY, native_abi_id=ABI)
    execution = dict(resource=RESOURCE, service=0, native_op=op, native_abi_id=ABI,
                     native0=a | (b << 10) | (dst << 20))
    local = assemble("local", [dict(op="L_EXEC", a=RESOURCE, b=3, c=0),
                               dict(op="L_WAIT", x=8), dict(op="L_END")],
                     dict(task=[task], execution=[execution]), LOCAL_ID, mask, ABI, TOPOLOGY)
    return mother, local


def validate_pair(mother, local):
    """Check the exact bounded topology and canonical program/descriptor encoding."""
    if len(local) != 368:
        raise ValueError("F image size")
    desc = codec.unpack_record("execution", local[-128:])
    op = desc["native_op"]
    if op not in (BYPASS, ADD):
        raise ValueError("unregistered F operation")
    native = desc["native0"]
    a, b, dst = ((native >> shift) & 1023 for shift in (0, 10, 20))
    addresses = word_addresses(a, b, dst, op == ADD)
    if native >> 30 or (op == BYPASS and b) or len(set(addresses)) != len(addresses):
        raise ValueError("invalid F word addresses or reserved bits")
    if (mother, local) != images(a, b, dst, op == ADD):
        raise ValueError("F topology, identity, descriptor or instruction is not canonical")
    return dict(addresses=addresses, op=op,
                image_sha256=[hashlib.sha256(v).hexdigest() for v in (mother, local)])


def validate_sources():
    """Verify every F input against its registered Git blob."""
    for name in ("E", "G", "GT", "S", "SA", "SB"):
        ref = MANIFEST["sources"][name]
        data = (PROJECT.parent / ref["path"]).read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        if blob != ref["blob"]:
            raise ValueError(f"wrong source bytes: {name}")
