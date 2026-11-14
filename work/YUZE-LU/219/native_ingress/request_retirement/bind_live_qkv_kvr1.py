"""Use the whole-request KVR1 records in the live QKV component replay."""
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import sys
from zlib import crc32


def sha(data):
    return sha256(data).hexdigest()


def stores(data):
    if len(data)%128:
        raise ValueError('truncated descriptor arena')
    result = {}
    for off in range(0,len(data),128):
        raw = data[off:off+128]
        if raw[:4] != b'KVR1':
            continue
        address,tag = unpack_from('<QQ',raw,24)
        if crc32(raw[:124]) != unpack_from('<I',raw,124)[0] or address in result:
            raise ValueError('invalid or duplicate KVR1 descriptor')
        result[address] = off, raw, tag
    return result


def bind(archive, request, output):
    program = json.loads((archive/'program.json').read_bytes())
    step = program['step']
    seals = {name: h for h,name in (x.split('  ',1) for x in (request/'proof.sha256').read_text().splitlines())}
    source_name = f'phase-{step}/descriptors.bin'
    source = (request/source_name).read_bytes()
    original = (archive/'descriptors.bin').read_bytes()
    if sha(source) != seals[source_name]:
        raise ValueError('whole-request descriptor seal differs')
    rows = stores(original)
    native = stores(source)
    if {r['ddr_address'] for r in program['kv_stores']} != rows.keys() or not rows:
        raise ValueError('replay does not declare its KVR1 stores')
    replaced = bytearray(original)
    coverage = []
    for store in program['kv_stores']:
        address = store['ddr_address']
        off, old, old_tag = rows[address]
        native_off, raw, tag = native[address]
        if old[:32] != raw[:32] or old[40:124] != raw[40:124] or store['first_tag'] != old_tag:
            raise ValueError('whole-request KVR1 changed more than tag and CRC')
        replaced[off:off+128] = raw
        store['first_tag'] = tag
        coverage.append(dict(replay_offset=off, source_offset=native_off, address=address,
                             archived_tag=old_tag, actual_tag=tag, sha256=sha(raw)))
    # The four rows identify the linked layer page. Bind that exact arena slice.
    allowed = set(r['source_offset'] for r in coverage)
    from struct import unpack
    witness = json.loads((request/'witness.json').read_bytes())
    phase = witness['phases'][step]
    table_name = 'mother-descriptors.tsv'
    table = (request/table_name).read_bytes()
    if sha(table)!=seals[table_name]:
        raise ValueError('whole-request page table changed')
    selected = []
    for line in table.decode('ascii').splitlines()[1:]:
        raw_step, page, address, size = line.split()
        if int(raw_step,16)!=step:
            continue
        offset = int(address,16)-phase['descriptor_base']
        end = offset+int(size)
        if set(range(offset,end,128)) & allowed:
            selected.append((int(page,16),offset,end))
    if len(selected)!=1:
        raise ValueError('live QKV stores do not identify a single whole-request page')
    page,begin,end=selected[0]
    exact=source[begin:end]
    if len(exact)!=len(replaced):
        raise ValueError('live QKV control does not cover the whole descriptor page')
    p_key = set()
    old_keys = set()
    for off in range(0,len(exact),128):
        old,raw=bytes(replaced[off:off+128]),exact[off:off+128]
        if old == raw:
            continue
        if (old[:4] != b'\x01PP\x02' or old[:16]!=raw[:16] or old[24:124]!=raw[24:124]
                or crc32(raw[:124])!=unpack_from('<I',raw,124)[0]):
            raise ValueError(f'live QKV authority differs outside P input ownership: {off}')
        old_keys.add(unpack('<4I',old[16:32]))
        p_key.add(unpack('<4I',raw[16:32]))
    if len(p_key)!=1 or len(old_keys)!=1:
        raise ValueError('live P pages disagree on input ownership')
    before,=old_keys
    after,=p_key
    sv=(archive/'test_native_projection_live.sv').read_text()
    def key_literal(key):
        return "{"+",".join(f"32'd{n}" for n in reversed(key))+"}"
    old_text="FIRST_INPUT_KEY="+key_literal(before)
    if sv.count(old_text)!=1:
        raise ValueError('replay input key differs from descriptor')
    (output/'test_native_projection_live.sv').write_text(
        sv.replace(old_text,"FIRST_INPUT_KEY="+key_literal(after)))
    replaced=exact
    if len({r['actual_tag'] for r in coverage})!=len(coverage):
        raise ValueError('duplicate live write tag')
    (output/'descriptors.bin').write_bytes(replaced)
    (output/'program.json').write_text(json.dumps(program,sort_keys=True,indent=2)+'\n')
    (output/'kv-stores.tsv').write_text(''.join(
        f"{r['ddr_address']}\t512\t{r['first_tag']}\n" for r in sorted(program['kv_stores'],key=lambda r:r['ddr_address'])))
    receipt = dict(step=step, page=page, phase_descriptor_offset=begin, input_key=after,
                   source_sha256=sha(source), original_sha256=sha(original),
                   patched_sha256=sha(replaced), request_sha256=sha((request/'proof.sha256').read_bytes()),
                   stores=coverage)
    (output/'same-plan-kvr1.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')


if __name__ == '__main__':
    bind(*(Path(x) for x in sys.argv[1:]))
