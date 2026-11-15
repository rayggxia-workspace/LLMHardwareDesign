"""Validate emitted native images and embedded U0 instructions against the profile."""
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
import zlib

import image


def check(root):
    manifest=json.loads((root/"manifest.json").read_text())
    profile=json.loads((root/"rtl-profile.json").read_text())
    signatures={(t["id"],r["schema"],r["abi"],r["opcode"],c)
                for t in profile["targets"] for r in t["routes"] for c in r["completions"]}
    files=0
    calls=0
    for index,stage in enumerate(manifest["stages"]):
        directory=root/stage["stage"]
        raw=(directory/"deployment.json").read_bytes()
        assert sha256(raw).hexdigest()==stage["deployment_sha256"]
        deployment=json.loads(raw)
        assert stage["generation"]==manifest["scope"]["first_generation"]+index
        for name,seal in deployment["payloads"].items():
            data=(directory/name).read_bytes()
            assert len(data)==seal["bytes"] and sha256(data).hexdigest()==seal["sha256"]
            files+=1
        for call in deployment["calls"]:
            assert (call["target"],*call["service_signature"],call["required_completion"]) in signatures
            if "address" in call:
                # Descriptors are stored in call order in each sealed native page.
                data=(directory/"descriptors.bin").read_bytes()
                entry=deployment["calls"].index(call)
                row=data[128*entry:128*(entry+1)]
                assert sha256(row).hexdigest()==call["sha256"]
                assert zlib.crc32(row[:124])==int.from_bytes(row[124:],"little")
            calls+=1
        for group,name in deployment["local_images"].items():
            data=(directory/name).read_bytes()
            adapter=deployment["adapter"]
            if adapter and any(c["group"]==group and c["target"]==3 for c in deployment["calls"]):
                header=image.compact.unpack_header(data[:128])
                assert header["native_abi_id"]==0x01930001 and header["topology_id"]==25001
                assert header["program_image_id"]==adapter["legacy_image"]
                assert header["total_bytes"]==len(data) and len(data)<=4096
                count=header["instruction_count"]
                begin=header["instruction_offset"]
                length=image.compact.section_size(count,header["version"])
                program=image.compact.unpack_program(data[begin:begin+length],count,"local",header["version"])
                assert program[-1]["op"]=="L_END" and len(program)==header["max_steps"]
                assert all(p["op"] in ("L_EXEC","L_WAIT","L_END") for p in program)
                assert header["execution_count"]==(len(program)-1)//2
                for i in range(0,len(program)-1,2):
                    assert program[i]["op"]=="L_EXEC" and program[i+1]["op"]=="L_WAIT"
            else:
                assert data[:8]==b"LBCISA01" and struct.unpack_from("<I",data,12)[0]==len(data)
                assert struct.unpack_from("<I",data,64)[0]==25001
        mother=(directory/"mother.bin").read_bytes()
        assert mother[:8]==b"LBCISA01" and struct.unpack_from("<I",mother,12)[0]==len(mother)
    assert len(manifest["stages"])==291 and calls==13898
    assert manifest["stages"][-1]["generation"]==manifest["scope"]["last_generation"]
    result={"status":"diagnostic_structure_passed","whole_graph_compilation":False,"delivery_accepted":False,"stages":291,"logical_calls":calls,"verified_payloads":files}
    (root/"validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(root,result)


if __name__=="__main__":
    for argument in sys.argv[1:]:
        check(Path(argument))
