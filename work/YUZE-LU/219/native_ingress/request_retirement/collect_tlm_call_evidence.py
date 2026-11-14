"""Locate sealed per-CALL completion evidence for explicitly selected source archives."""

import argparse
from collections import Counter
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from struct import Struct
from tarfile import TarError, open as open_tar
from zlib import crc32

HEADER = Struct('<IHHII')
DESCRIPTOR_BYTES = 128
SIGNATURE_FIELDS = ('target', 'schema', 'abi', 'opcode', 'completion')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def seals(raw):
    rows = [line.split('  ', 1) for line in raw.decode('ascii').splitlines()]
    entries = {name: digest for digest, name in rows}
    require(len(entries) == len(rows), 'duplicate proof entry')
    return entries


def checked_file(root, name, proof):
    path = root / name
    checksum = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            checksum.update(chunk)
    require(checksum.hexdigest() == proof.get(name), f'request proof mismatch for {name}')
    return path


def read_members(archive):
    entries = {}
    for entry in archive:
        path = PurePosixPath(entry.name)
        require(not path.is_absolute() and '..' not in path.parts,
                f'invalid path in source archive: {entry.name}')
        if not entry.isdir():
            require(entry.isfile() and path not in entries,
                    f'unsupported or duplicate source archive member: {entry.name}')
            entries[path] = entry

    def read(path):
        with archive.extractfile(entries[PurePosixPath(path)]) as member:
            return member.read()

    return read


def descriptor_extents(path, selected, total):
    extents = {}
    with path.open(encoding='ascii') as rows:
        require(int(next(rows)) == total, 'request descriptor table count differs')
        for line in rows:
            step, page, address, size = line.split()
            key = int(step, 16), int(page, 16)
            if key in selected:
                require(key not in extents, f'duplicate request descriptor row for {key}')
                extents[key] = int(address, 16), int(size)
    require(extents.keys() == selected, 'request is missing a selected descriptor row')
    return extents


def source_page(read, stage, phase, page, topology):
    location = phase['step'], page
    root = PurePosixPath(stage['root'])
    bundle = root / stage['bundle']
    proof = read(root / 'proof.sha256')
    require(sha256(proof).hexdigest() == phase['source_proofs'][page] == stage['proof_sha256'],
            f'source stage proof mismatch at {location}')
    entries = seals(proof)

    def member(path):
        raw = read(path)
        key = stage.get('manifest_member_prefix', '') + path.relative_to(root).as_posix()
        require(sha256(raw).hexdigest() == entries.get(key),
                f'source member proof mismatch at {location}: {key}')
        return raw

    witness = json.loads(member(root / 'witness.json'))
    require(witness['graph_sha256'] == phase['graph_sha256'],
            f'source graph mismatch at {location}')
    deployment = json.loads(member(bundle / 'deployment.json'))
    raw = member(bundle / 'descriptors.bin')
    metadata = deployment['payloads']['descriptors.bin']
    require(deployment['topology'] == topology and len(raw) == metadata['bytes']
            and sha256(raw).hexdigest() == metadata['sha256'],
            f'source deployment metadata mismatch at {location}')
    return deployment, raw


def checked_calls(deployment, raw, relocated, phase, page, topology):
    location = phase['step'], page
    calls = deployment['calls']
    require(raw == relocated and len(raw) == len(calls) * DESCRIPTOR_BYTES and calls,
            f'relocated descriptors differ from source deployment at {location}')
    require(sum(1 << target for target in {call['target'] for call in calls})
            == phase['target_masks'][page], f'source target mask differs at {location}')
    for index, call in enumerate(calls):
        offset = index * DESCRIPTOR_BYTES
        descriptor = raw[offset:offset + DESCRIPTOR_BYTES]
        schema, length, opcode, abi, owner = HEADER.unpack_from(descriptor)
        digest = sha256(descriptor).hexdigest()
        require(length == DESCRIPTOR_BYTES and owner == topology
                and deployment['descriptor_base'] + offset == call['address']
                and digest == call['sha256']
                and tuple(call['service_signature']) == (schema, abi, opcode)
                and crc32(descriptor[:124]) == int.from_bytes(descriptor[124:], 'little'),
                f'descriptor evidence mismatch at {location}/{index}')
        yield (call['target'], schema, abi, opcode, call['required_completion']), index, digest


def collect(request, archives):
    """Return completion-specific samples for the supplied step/page archive spans."""
    request = Path(request)
    proof = (request / 'proof.sha256').read_bytes()
    entries = seals(proof)
    witness = json.loads(checked_file(request, 'witness.json', entries).read_bytes())
    require(witness['schema'] == 'native-graph-request-pages/1', 'unsupported request witness')
    phases = {phase['step']: phase for phase in witness['phases']}
    extents_path = checked_file(request, 'mother-descriptors.tsv', entries)
    selected, archive_receipts, counts, examples = {}, [], Counter(), {}
    with ExitStack() as stack:
        for step, first_page, path in sorted(archives):
            path = Path(path)
            read = read_members(stack.enter_context(open_tar(path)))
            receipt = json.loads(read('stages.json'))
            stages = receipt['stages']
            require(step in phases and stages and 0 <= first_page <=
                    phases[step]['page_count'] - len(stages), f'archive span outside request: {path.name}')
            require(receipt['graph_sha256'] == phases[step]['graph_sha256'],
                    f'archive graph mismatch: {path.name}')
            for page, stage in enumerate(stages, first_page):
                require((step, page) not in selected, f'overlapping archive span at {(step, page)}')
                selected[step, page] = read, stage
            archive_receipts.append(dict(step=step, first_page=first_page, pages=len(stages), archive=path.name))
        require(bool(selected), 'supply at least one source archive')
        extents = descriptor_extents(extents_path, selected.keys(),
                                     sum(phase['page_count'] for phase in phases.values()))
        arenas = {}
        for (step, page), (read, stage) in sorted(selected.items()):
            phase = phases[step]
            if step not in arenas:
                name = f'phase-{step}/descriptors.bin'
                arenas[step] = stack.enter_context(checked_file(request, name, entries).open('rb'))
            arena = arenas[step]
            address, size = extents[step, page]
            offset = address - phase['descriptor_base']
            require(0 <= offset <= phase['descriptor_bytes'] - size, f'invalid page extent at {(step, page)}')
            arena.seek(offset)
            deployment, raw = source_page(read, stage, phase, page, witness['topology'])
            for signature, index, digest in checked_calls(
                    deployment, raw, arena.read(size), phase, page, witness['topology']):
                counts[signature] += 1
                examples.setdefault(signature, dict(step=step, page=page, descriptor_index=index,
                                                    descriptor_sha256=digest, stage_proof=stage['proof_sha256'],
                                                    source_stage=stage['root']))
    return dict(schema='algo1-call-evidence/1', package_proof_sha256=sha256(proof).hexdigest(),
                pages=len(selected), calls=sum(counts.values()), archives=archive_receipts,
                signatures=[dict(zip(SIGNATURE_FIELDS, signature), covered_calls=count, sample=examples[signature])
                            for signature, count in sorted(counts.items())])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--archive', action='append', nargs=3, required=True, metavar=('STEP', 'FIRST_PAGE', 'TAR'))
    args = parser.parse_args()
    try:
        archives = [(int(step), int(page), Path(path)) for step, page, path in args.archive]
        result = collect(args.request, archives)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError, TarError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()

