"""Bind vocabulary output custody and feedback consumers to sealed request pages."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zlib import crc32

from audit_native_v2_dispatch import hash_file, seal, unpack_mother
from link_gather_request import require, selected_rows

P_SCOPE = (0x02505001, 128, 2, 0x02504d02)
WORD_BYTES = 16
S32_PER_WORD = WORD_BYTES // 4


def tiles(data, topology):
    """Decode exactly the S32 vocabulary subset supported by the terminal."""
    require(data and len(data) % 128 == 0, 'invalid vocabulary descriptor extent')
    next_col = 0
    request = None
    for off in range(0, len(data), 128):
        raw = data[off:off+128]
        require(unpack_from('<IHHII', raw) == (*P_SCOPE, topology) and
                crc32(raw[:124]) == unpack_from('<I', raw, 124)[0],
                f'vocabulary descriptor signature or CRC differs at {off}')
        length, first, stride, groups = unpack_from('<IIHB', raw, 64)
        version, = unpack_from('<I', raw, 40)
        k_width, k_begin, k_end = unpack_from('<HHH', raw, 76)
        output, = unpack_from('<H', raw, 86)
        key = raw[16:32].hex()
        args = (length, version, key, k_width)
        if request is None:
            request = args
        require(args == request, 'vocabulary identity changes between tiles')
        count = stride*groups
        require(raw[83] == 1 and raw[82] == 1 and stride == 8 and 0 < groups <= 16 and
                k_begin == 0 and k_end == k_width and version > 0 and first == next_col and
                first+count <= length and output + count//S32_PER_WORD <= 1024,
                f'vocabulary tile shape, order or SRAM window differs at {off}')
        next_col += count
        yield dict(first=first, count=count, length=length, version=version, input_key=key,
                   word=output, words=count//S32_PER_WORD)
    require(next_col == request[0], 'vocabulary does not cover its declared tensor')


def link(package, gather_link, admission, output):
    root_seal = package/'proof.sha256'
    hashes = seal(root_seal)

    def checked(name):
        path = package/name
        require(hash_file(path) == hashes[name], f'archived file changed: {name}')
        return path

    package_hash = hash_file(root_seal)
    witness = json.loads(checked('witness.json').read_bytes())
    gather = json.loads(gather_link.read_bytes())
    guards = json.loads(admission.read_bytes())
    require(gather['package_sha256'] == guards['package_sha256'] == package_hash,
            'Gather, P admission and vocabulary use different requests')
    phases = witness['phases']
    counts = [phase['page_count'] for phase in phases]
    require(all(phase['step'] == i for i, phase in enumerate(phases)), 'request phases are out of order')
    keys = {(i, n-1) for i,n in enumerate(counts)}
    target_rows = selected_rows(checked('mother-targets.tsv'), keys, counts)
    mother_rows = selected_rows(checked('mother-pages.tsv'), keys, counts)
    descriptor_rows = selected_rows(checked('mother-descriptors.tsv'), keys, counts)
    base, capacity, arena = checked('mother-packed.tsv').read_text().split()
    base, capacity = int(base), int(capacity)
    feedback = {}
    for row in gather['pages']:
        if row['dispatch_prerequisite'] is None:
            continue
        owner = row['dispatch_prerequisite']['step']
        require(row['step'] == owner+1 and owner not in feedback and
                row['gather_prerequisite'] == 'retired_token_sram_commit_ack',
                'invalid next-step token dependency')
        feedback[owner] = row
    require(set(feedback) == set(range(len(phases)-1)), 'a decode boundary is missing')
    topology = witness['topology']
    require(topology == guards['placed_topology'], 'P admission belongs to another topology')
    reports, volume = [], Counter()
    with checked(arena).open('rb') as mothers:
        for step, page in sorted(keys):
            phase = phases[step]
            source_proof = phase['source_proofs'][page]
            ref, size = descriptor_rows[step,page]
            ref, size = int(ref,16), int(size)
            path = checked(f'phase-{step}/descriptors.bin')
            offset = ref-phase['descriptor_base']
            with path.open('rb') as f:
                require(0 <= offset == phase['descriptor_bytes']-size, 'terminal is not the final descriptor range')
                f.seek(offset)
                raw = f.read(size)
            ranges = list(tiles(raw, topology))
            require(len(raw) == size, 'vocabulary descriptor payload is truncated')
            address, extent, crc, padded, row_offset, asset = mother_rows[step,page]
            address, extent, padded = int(address,16), int(extent), int(padded)
            require(asset == arena and row_offset == '0' and 0 <= address-base <= capacity-padded and
                    padded == ((extent+63)//64)*64, 'invalid vocabulary mother extent')
            mothers.seek(address-base)
            pm = mothers.read(padded)
            require(len(pm) == padded and not any(pm[extent:]) and crc32(pm[:extent]) == int(crc,16),
                    'invalid vocabulary mother checksum')
            calls = unpack_mother(pm[:extent], topology)
            require(target_rows[step,page] == ['001'] and len(calls) == len(ranges) and
                    all(call['target'] == 0 and call['reference'] == ref+128*i
                        for i,call in enumerate(calls)),
                    'vocabulary CALLs do not match the ordered P0 descriptor range')
            consumer = feedback.get(step)
            if consumer is not None:
                prereq = consumer['dispatch_prerequisite']
                require(prereq['terminal_page'] == page and prereq['terminal_source_proof'] == source_proof,
                        'decode page names a different vocabulary producer')
            first = ranges[0]
            expect = [(row['count'],row['word'],row['words']) for row in ranges]
            histogram = Counter(expect)
            report = dict(step=step, page=page, target=0, stage_proof=source_proof,
                          descriptor_sha256=sha256(raw).hexdigest(), mother_sha256=sha256(pm[:extent]).hexdigest(),
                          version=first['version'], input_key=first['input_key'], logits=first['length'],
                          tiles=len(ranges), s32_reads=sum(row['words'] for row in ranges),
                          window_histogram=[dict(values=n, word=w, words=words, calls=count)
                                            for (n,w,words),count in sorted(histogram.items())],
                          per_call_release='tile_consumed',
                          phase_release='vocabulary_token_retired',
                          consumer=None if consumer is None else
                          dict(step=consumer['step'],page=consumer['page'],local_pm_sha256=consumer['local_pm_sha256']))
            reports.append(report)
            volume['calls'] += report['tiles']
            volume['logits'] += report['logits']
            volume['sram_reads'] += report['s32_reads']
    guarded = [row for row in guards['records'] if row['vocabulary_marker']]
    require(guarded and not any(row['status'] for row in guarded) and
            sum(row['calls'] for row in guarded) == volume['calls'],
            'P admission coverage differs from terminal handoff')
    report = dict(schema='block-v2-vocabulary-retirement-link/1', status='requires_live_provider',
                  package_sha256=package_hash, gather_sha256=hash_file(gather_link),
                  admission_sha256=hash_file(admission), phases=len(reports), feedback_edges=len(feedback),
                  volume=volume, producer_role='P0 committed S32 logits and vocabulary terminal',
                  transport_commit='U0 local SRAM index commit', pages=reports)
    output.mkdir()
    (output/'retirement-link.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='pages'},sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package','gather_link','admission','output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    link(**vars(args))
