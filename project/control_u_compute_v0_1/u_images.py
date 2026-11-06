"""Assemble and admit the bounded U RMS+ADD experiment ABI."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT / "control_p_compute_v0_1"))
from run_a2 import assemble, CAPACITY
from image import codec

BINDINGS = json.loads((PROJECT / "control_f_compute_v0_1/trial_bindings.json").read_bytes())
U = BINDINGS["profiles"]["U"]
ABI, TOPOLOGY = U["abi"], U["topology"]
RESOURCE, MASK = U["service_resource"], U["resource_mask"]
OP = int(U["operation"], 16)
MOTHER_ID, LOCAL_ID = 17930, 17931


def images(a=4, b=9, dst=20, n0=8, n1=5, epsilon=1024, bias=256):
    words = (a, b, dst, dst+1)
    if len(set(words))!=4 or any(not 0<=word<1024 for word in words):
        raise ValueError("U address overlap or two-word range")
    if not (1<=n0<=8 and 1<=n1<=8 and 1<=epsilon<=0xffffffff and -32768<=bias<=32767):
        raise ValueError("U segment count, epsilon or bias")
    mother = assemble("mother", [dict(op="G_CALL", a=0, b=2, c=0),
                                 dict(op="G_WAIT", x=4), dict(op="G_END")], {},
                      MOTHER_ID, 0, ABI, TOPOLOGY)
    task = dict(block_type=U["block_type"], entry_pc=0, max_steps=3, required_resources=MASK,
                program_image_id=LOCAL_ID, topology_id=TOPOLOGY, native_abi_id=ABI)
    execution = dict(resource=RESOURCE, service=0, native_op=OP, native_abi_id=ABI,
                     native0=a | b<<10 | dst<<20, native1=n0 | n1<<4 | (bias & 65535)<<16,
                     native2=epsilon)
    local = assemble("local", [dict(op="L_EXEC", a=RESOURCE, b=3, c=0),
                               dict(op="L_WAIT", x=8), dict(op="L_END")],
                     dict(task=[task], execution=[execution]), LOCAL_ID, MASK, ABI, TOPOLOGY)
    return mother, local


def validate_pair(mother, local):
    if len(local)!=368:
        raise ValueError("U image size")
    desc = codec.unpack_record("execution", local[-128:])
    a, b, dst = ((desc["native0"] >> shift)&1023 for shift in (0,10,20))
    n0, n1 = (desc["native1"]&15), (desc["native1"]>>4)&15
    bias = int.from_bytes((desc["native1"]>>16).to_bytes(2,"little"), "little", signed=True)
    if (mother, local)!=images(a,b,dst,n0,n1,desc["native2"],bias):
        raise ValueError("U image, topology or descriptor is not canonical")
    return dict(image_sha256=[hashlib.sha256(v).hexdigest() for v in (mother,local)])


def validate_sources():
    for name in ("N", "NT", "NG", "E", "S", "SA", "SB"):
        entry = BINDINGS["sources"][name]
        data = (PROJECT.parent / entry["path"]).read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        if blob!=entry["blob"]:
            raise ValueError(f"wrong source bytes: {name}")
