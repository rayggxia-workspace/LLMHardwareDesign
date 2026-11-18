"""Bind every captured Qwen3 write to its descriptor and choose deterministic cases."""
from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
from struct import pack_into, unpack_from
import sys


stage, window, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
positions = {"prefill": (0, 1), "first_token": (512,), "decode": (513,)}[window]
capture = stage/"ddr-write-payload.tsv"
receipt = json.loads((stage/"real-activity.json").read_bytes())
if sha256(capture.read_bytes()).hexdigest() != receipt["payload_sha256"]:
    raise ValueError("payload manifest differs")
by_address = {}
with capture.open() as stream:
    for row in csv.DictReader(stream, delimiter="\t"):
        if row["window"] != window:
            continue
        address, tag = int(row["address"]), int(row["tag"])
        data = bytes.fromhex(row["payload_le"])
        if address in by_address or len(data)!=64 or tag!=address//64:
            raise ValueError("malformed or duplicate captured beat")
        by_address[address] = data

samples = defaultdict(list)
for pos in positions:
    for layer in range(28):
        file = stage/"assets"/f"pos{pos}-l{layer}-descriptors.bin"
        data = file.read_bytes()
        kv = 0
        for offset in range(0,len(data),128):
            if unpack_from("<IHHI",data,offset) != (9,128,1,8):
                continue
            address, word, words = unpack_from("<QHH",data,offset+16)
            if words!=32 or address%64:
                raise ValueError(f"unexpected span extent at {file}:{offset}")
            if 1<<33 <= address < 15<<30:
                role = "k" if kv%2 == 0 else "v"
                kv += 1
            elif 15<<30 <= address < (15<<30)+56*3072*4:
                role = "ffn"
            else:
                raise ValueError(f"unclassified write: {address:#x}")
            beats = [by_address.pop(address+i) for i in range(0,512,64)]
            words512 = [int.from_bytes(beat,"little") for beat in beats]
            flips = sum(bin(a^b).count("1") for a,b in zip(words512,words512[1:]))
            samples[role].append((flips,address,pos,layer,offset,word,b"".join(beats)))
        if kv != 16:
            raise ValueError(f"unexpected K/V pairs: {file}")
if by_address or sum(map(len,samples.values()))*8 != receipt["writes_by_window"][window]:
    raise ValueError("descriptor extents did not consume the complete captured window")

result = {"window":window,"distribution":{},"cases":{}}
for role, rows in samples.items():
    ordered = sorted(rows)
    pick = {"anchor":rows[0],"median":ordered[len(rows)//2],"p90":ordered[9*len(rows)//10]}
    if len(rows) < 100:
        raise ValueError(f"incomplete span coverage: {role}")
    result["distribution"][role] = {
        "row_count":len(rows),"min":ordered[0][0],"median":pick["median"][0],
        "p90":pick["p90"][0],"max":ordered[-1][0],
    }
    used = set()
    for label,(flips,address,pos,layer,offset,word,payload) in pick.items():
        if address in used:
            continue
        used.add(address)
        destination = f"{role}-{label}"
        descriptor = bytearray(128)
        schema = 0x31535744 if role=="ffn" else 0x3152564B
        pack_into("<IHHII",descriptor,0,schema,128,2 if role=="v" else 1,0x02500002,25001)
        pack_into("<H6xQQ",descriptor,16,word,address,address//64)
        (out/f"{destination}.desc.hex").write_text(descriptor[::-1].hex()+"\n")
        (out/f"{destination}.data.hex").write_text("".join(payload[i:i+16][::-1].hex()+"\n"
                                                          for i in range(0,512,16)))
        result["cases"][destination] = dict(address=address,position=pos,layer=layer,offset=offset,
                                             inter_beat_bit_flips=flips,payload_sha256=sha256(payload).hexdigest())
(out/"cases.json").write_text(json.dumps(result,indent=2)+"\n")
