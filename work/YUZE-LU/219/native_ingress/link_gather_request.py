"""Link resident U Gather images to the archived request's exact pages."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import pack_into, unpack_from
from zlib import crc32

from assemble_cases import END, call, image, wait
from audit_native_v2_dispatch import hash_file, seal, unpack_mother
from compact import unpack_header
from resident_gather_contract import GATHER, LINK_RECEIVE, LINK_RESERVE


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hex_rows(path):
    with path.open(encoding='ascii') as f:
        count = int(next(f))
        rows = [tuple(int(part, 16) for part in line.split()) for line in f]
    require(len(rows) == count, f'row count changed in {path.name}')
    return rows


def selected_rows(path, expected, page_counts):
    selected = {}
    with path.open(encoding='ascii') as f:
        require(int(next(f)) == sum(page_counts), f'page count changed in {path.name}')
        for step, count in enumerate(page_counts):
            for page in range(count):
                row = next(f, '').split()
                require(len(row) >= 3 and tuple(int(part, 16) for part in row[:2]) == (step, page),
                        f'page identity changed in {path.name} at {step}/{page}')
                if (step, page) in expected:
                    selected[step, page] = row[2:]
        require(not next(f, None), f'extra page in {path.name}')
    return selected


def check_local(data, local, mode, burst, word, lane):
    header = unpack_header(data[:128])
    start = header['execution_offset']
    count = header['execution_count']
    require(header['total_bytes'] == len(data) and header['topology_id'] == local['target_topology'],
            'local Gather image header disagrees with its sidecar')
    opcodes = tuple(unpack_from('<H', data, start + 128*i + 4)[0] for i in range(count))
    index = local['input_source']
    if mode == 1:
        require(opcodes == (GATHER,) and index['kind'] == 'prompt_ddr' and
                index['address'] == burst + lane and
                unpack_from('<Q', data, start + 80)[0] == ((1 << 48) | index['address']),
                'prompt index operand changed')
    else:
        require(opcodes == (LINK_RESERVE, LINK_RECEIVE, GATHER) and
                index['kind'] == 'previous_retired_token' and
                (index['word'], index['lane_offset']) == (word, lane) and
                index['prerequisite'] == 'retired_token_sram_commit_ack' and
                unpack_from('<I', data, start + 64)[0] == word,
                'retired index operand changed')
    need = unpack_from('<IIII', data, start + 128*(count-1) + 64)
    require(need[1] >> 16 == 16*word + lane, 'index address changed in Gather')
    return (need[0] | (need[1] & 0xffff) << 32, need[2], need[1] >> 16, need[3]), header


def checked_descriptor(path, offset, size, checksum, cache):
    if path not in cache:
        require(hash_file(path) == checksum, f'archived descriptor file changed: {path.name}')
        cache.add(path)
    with path.open('rb') as source:
        source.seek(offset)
        raw = source.read(size)
        require(len(raw) == size, f'descriptor extent changed: {path}')
        return raw


def link(package, lowered, direct_audit, output):
    package_seal = package/'proof.sha256'
    hashes = seal(package_seal)
    package_hash = hash_file(package_seal)

    def checked(name):
        path = package/name
        require(hash_file(path) == hashes[name], f'archived file changed: {name}')
        return path

    witness = json.loads(checked('witness.json').read_bytes())
    signature_file = checked('service-signatures.json')
    signatures = json.loads(signature_file.read_bytes())
    audit = json.loads(direct_audit.read_bytes())
    require(audit['package_proof_sha256'] == package_hash, 'direct CALL audit is from a different request')
    sig_fields = ('target', 'schema', 'abi', 'opcode')
    expected = Counter()
    for row in signatures:
        expected[tuple(row[k] for k in sig_fields)] += row['calls']
    audited = {tuple(row[k] for k in sig_fields): row for row in audit['signatures']}
    require(Counter({k: row['calls'] for k, row in audited.items()}) == expected,
            'direct CALL audit does not cover this package')

    phases = witness['phases']
    page_counts = [p['page_count'] for p in phases]
    require(all(p['step'] == i for i, p in enumerate(phases)), 'phase ordering changed')
    sidecar = lowered/'local-sidecars.json'
    plans = json.loads(sidecar.read_bytes())
    inputs = hex_rows(checked('input-index.tsv'))
    require(len(inputs) == len(plans), 'every index must have one lowered plan')
    keys = {(step, page) for step, page, *_ in inputs}
    require(len(keys) == len(inputs), 'duplicate Gather page identity')
    page_sources = selected_rows(checked('mother-pages.tsv'), keys, page_counts)
    targets = selected_rows(checked('mother-targets.tsv'), keys, page_counts)
    descriptors = selected_rows(checked('mother-descriptors.tsv'), keys, page_counts)
    base, capacity, arena = checked('mother-packed.tsv').read_text().split()
    require(arena == 'mother-programs.ddr.bin', 'expected archived packed mother arena')
    base, capacity = int(base), int(capacity)
    replacements, descriptor_checks = [], set()
    mother = None

    with checked(arena).open('rb') as original:
        for plan, (step, page, position, mode, burst, word, lane) in zip(plans, inputs, strict=True):
            key = (step, page)
            phase = phases[step]
            require((plan['step'], plan['page'], plan['position'], plan['source_mode']) ==
                    (step, page, position, mode) and phase['source_proofs'][page] == plan['original_stage_proof'],
                    f'Gather plan does not bind archived page {step}/{page}')
            require((mode == 1 and step == 0) or
                    (mode == 2 and step > 0 and plan['input_source']['retired_step'] == step-1),
                    f'wrong token dependency for {step}/{page}')
            address, extent, crc, padded, offset, asset = page_sources[key]
            address, extent, padded = int(address, 16), int(extent), int(padded)
            require(asset == arena and offset == '0' and
                    0 <= address-base <= capacity-padded and padded == (extent + 63)//64*64,
                    f'bad archived PM extent for {step}/{page}')
            original.seek(address-base)
            raw = original.read(padded)
            require(len(raw) == padded and crc32(raw[:extent]) == int(crc, 16) and not any(raw[extent:]),
                    f'bad archived PM payload for {step}/{page}')
            calls = unpack_mother(raw[:extent], witness['topology'])
            ref, size = descriptors[key]
            ref, size = int(ref, 16), int(size)
            require(len(calls) == 1 and calls[0]['reference'] == ref and calls[0]['target'] == 3 and
                    size == 128 and targets[key] == ['008'] and phase['target_masks'][page] == 8,
                    f'archived page {step}/{page} is not a U0-only Gather CALL')
            descriptor_path = f'phase-{step}/descriptors.bin'
            desc = checked_descriptor(package/descriptor_path, ref-phase['descriptor_base'], size,
                                      hashes[descriptor_path], descriptor_checks)
            gather_key = (3, 3, 7, 4)
            expected_desc = (gather_key[1], size, gather_key[3], gather_key[2], witness['topology'])
            require(unpack_from('<IHHII', desc) == expected_desc and crc32(desc[:124]) == unpack_from('<I', desc, 124)[0],
                    f'archived descriptor {step}/{page} is not a Gather')

            local = (lowered/(plan['pm_sha256'] + '.pm')).read_bytes()
            require(sha256(local).hexdigest() == plan['pm_sha256'], f'local image changed at {step}/{page}')
            fields, header = check_local(local, plan, mode, burst, word, lane)
            table, rows, index, dest, bits = unpack_from('<QIHHH', desc, 16)
            require(fields == (table, rows, index, dest) and bits == 32, f'Gather mapping changed at {step}/{page}')
            # The four-flit CALL transports the accepted U image ID in its
            # target snapshot. The 8 task registers stay clear for this service.
            code = [call(3, 9), wait(1 << 9), END]
            pm = bytearray(image(code, max_steps=len(code)))
            pack_into('<II', pm, 60, header['program_image_id'], header['topology_id'])
            require(mother is None or pm == mother, 'mother image identity changed across equivalent pages')
            mother = pm
            prerequisite = None
            if mode == 2:
                prior = phases[step-1]
                prerequisite = {'service':'vocabulary_token_retired', 'step':step-1,
                                'terminal_page':prior['page_count']-1,
                                'terminal_source_proof':prior['source_proofs'][-1],
                                'token_source_bound':False}
            replacements.append({'step':step, 'page':page, 'position':position, 'target':3,
                                 'descriptor_sha256':sha256(desc).hexdigest(),
                                 'archived_mother_sha256':sha256(raw[:extent]).hexdigest(),
                                 'local_pm_sha256':plan['pm_sha256'], 'source_plan_sha256':plan['plan_sha256'],
                                 'stage_proof':plan['original_stage_proof'], 'local_image_id':header['program_image_id'],
                                 'dispatch_prerequisite':prerequisite,
                                 'gather_prerequisite':plan['input_source'].get('prerequisite'),
                                 'completion':'destination_commit_ack'})

    require(replacements and len(replacements) == expected[gather_key], 'full Gather coverage differs')
    remaining = [{k: row[k] for k in (*sig_fields, 'completion', 'calls')} |
                 {'direct_header_status':audited[tuple(row[k] for k in sig_fields)]['status']}
                 for row in signatures if tuple(row[k] for k in sig_fields) != gather_key]
    report = {'schema':'block-v2-gather-request-link/1', 'status':'partial', 'package_sha256':package_hash,
              'direct_audit_sha256':hash_file(direct_audit), 'sidecar_sha256':hash_file(sidecar),
              'mother_pm_sha256':sha256(mother).hexdigest(), 'mother_pm_bytes':len(mother),
              'request_pages':sum(page_counts), 'request_calls':sum(expected.values()),
              'replaced_calls':len(replacements), 'remaining_calls':sum(row['calls'] for row in remaining),
              'remaining_signatures':remaining, 'pages':replacements}
    output.mkdir()
    (output/'mother.pm').write_bytes(mother)
    (output/'mother.hex').write_text(''.join(mother[i:i+16][::-1].hex()+'\n' for i in range(0,len(mother),16)))
    (output/'request-link.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pages','remaining_signatures')},sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package','lowered','direct_audit','output'):
        parser.add_argument(name, type=Path)
    link(**vars(parser.parse_args()))
