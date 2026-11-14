"""Replay unmodified request KVR1 descriptors with independently sealed KV values."""
from bisect import bisect_right
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import sys
from zlib import crc32


def digest(data):
    return sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def hex_words(path, records):
    path.write_text(''.join(record[::-1].hex()+'\n' for record in records))


def prepare(request, kv, captured, out):
    seal = {name: sig for sig,name in (line.split('  ',1) for line in (request/'proof.sha256').read_text().splitlines())}
    kv_proof = read(kv)
    if kv_proof['request_sha256'] != digest((request/'proof.sha256').read_bytes()):
        raise ValueError('KV receipt and program differ')
    capture_proof = {name: sig for sig,name in (line.split('  ',1) for line in (captured/'proof.sha256').read_text().splitlines())}
    capture_table = (captured/'generated/witness.json').read_bytes()
    capture_data = (captured/'generated/expected.bin').read_bytes()
    if any(digest(data) != capture_proof[name] for name,data in
           [('generated/witness.json',capture_table),('generated/expected.bin',capture_data)]):
        raise ValueError('captured KV witness changed')
    old = json.loads(capture_table)
    streams = old['streams']
    bases = [stream['base'] for stream in streams]
    payloads = {(row['stream'],row['position']): capture_data[i*512:(i+1)*512]
                for i,row in enumerate(old['records'])}
    if len(payloads) != len(old['records']) or len(capture_data) != len(payloads)*512:
        raise ValueError('captured KV payload count differs')
    position_set = set(old['positions'])
    phases = [phase for phase in kv_proof['phase_records'] if phase['first'] in position_set]
    if [phase['first'] for phase in phases] != old['positions'] or any(p['rows'] != 1 for p in phases):
        raise ValueError('captured KV positions differ from deployable phases')
    source_manifest = (request/'witness.json').read_bytes()
    if digest(source_manifest) != seal['witness.json']:
        raise ValueError('request witness changed')
    witness = json.loads(source_manifest)
    descriptor_base = (witness['allocation_end']+127)&~127
    records, descriptors, contents, used = [], [], [], set()
    tags = set()
    for phase in phases:
        step = phase['step']
        path = f'phase-{step}/descriptors.bin'
        data = (request/path).read_bytes()
        if digest(data) != seal[path] or len(data)%128:
            raise ValueError(f'changed compiled descriptor arena in phase {step}')
        for offset in range(0,len(data),128):
            raw = data[offset:offset+128]
            if raw[:4] != b'KVR1':
                continue
            schema, size, opcode, abi, topology = unpack_from('<IHHII',raw)
            word, = unpack_from('<H',raw,16)
            address,tag = unpack_from('<QQ',raw,24)
            i = bisect_right(bases,address)-1
            if (crc32(raw[:124]) != unpack_from('<I',raw,124)[0] or i < 0
                    or (size, abi, topology) != (128,0x02500002,witness['topology'])
                    or opcode != 1+(streams[i]['kind']=='v') or word+32>1024
                    or address != bases[i]+phase['first']*512):
                raise ValueError(f'KVR1 identity or range differs at {step}:{offset}')
            commit = i,phase['first']
            bursts = set(range(tag,tag+8))
            if commit in used or tags & bursts:
                raise ValueError('duplicate KV row or DDR tag')
            used.add(commit)
            tags.update(bursts)
            descriptors.append(raw)
            contents.append(payloads[commit])
            records.append(dict(stream=i,position=phase['first'],address=address,tag=tag,
                                phase=step,source_offset=offset,source_sram_word=word))
    if used != set(payloads) or len(streams) != kv_proof['streams']:
        raise ValueError('actual descriptors do not cover the captured rows')
    out.mkdir()
    (out/'descriptors.bin').write_bytes(b''.join(descriptors))
    (out/'expected.bin').write_bytes(b''.join(contents))
    hex_words(out/'descriptors.hex', descriptors)
    hex_words(out/'rows.hex', (row[i:i+16] for row in contents for i in range(0,512,16)))
    report = dict(old, records=records, descriptor_base=descriptor_base, first_step=phases[0]['step'],
                  request_sha256=kv_proof['request_sha256'], kv_program_receipt_sha256=digest(kv.read_bytes()),
                  source_data_sha256=digest(capture_data), descriptor_sha256=digest(b''.join(descriptors)))
    (out/'witness.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(descriptor_base)


if __name__ == '__main__':
    prepare(*(Path(value) for value in sys.argv[1:]))
