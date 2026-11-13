"""Verify generated runtime index tables against the sealed request and linked programs."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import file_digest, sha256
import json
from pathlib import Path
import tarfile

from event_request_ingress import gather_input, input_index_table


def hashes(raw):
    return {name: digest for digest, name in (line.split() for line in raw.decode().splitlines())}


def file_sha(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def row_read(rows, position):
    name = rows / f'row-{position}.tar'
    checksum, sealed = name.with_suffix('.tar.sha256').read_text().split()
    assert name.name == sealed and file_sha(name) == checksum, name
    with tarfile.open(name) as archive:
        names = {item.name.removeprefix('./'): item for item in archive if item.isfile()}
        def extract(member):
            with archive.extractfile(names[member]) as stream:
                return stream.read()
        root = hashes(extract('row-proof.sha256'))
        stages = extract('stages.json')
        assert sha256(stages).hexdigest() == root['stages.json']
        stage = json.loads(stages)['stages'][0]
        prefix = stage['root'] + '/'
        raw = extract(prefix + 'proof.sha256')
        assert sha256(raw).hexdigest() == stage['proof_sha256']
        members = hashes(raw)
        bundle = stage.get('bundle', '.').removeprefix('./')
        out = []
        for filename in ('compile.json', 'deployment.json', 'descriptors.bin'):
            relative = filename if filename == 'compile.json' or bundle == '.' or not bundle else bundle + '/' + filename
            data = extract(prefix + relative)
            assert sha256(data).hexdigest() == members[stage.get('manifest_member_prefix', '') + relative]
            out.append(data)
    compile_bytes, deployment, descriptors = out
    return json.loads(compile_bytes)['outputs']['program'], json.loads(deployment), descriptors, stage['proof_sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'request', 'layout', 'evidence', 'out'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    request = json.loads(args.request.read_bytes())
    layout = json.loads(args.layout.read_bytes())
    assert layout['source_sha256']['semantic'] == request['manifest_sha256']
    prompt = request['workload']['prompt_tokens']
    length = request['workload']['final_cache_length']
    prompt_image = layout['regions']['prompt:0']
    assert prompt_image['tokens'] == prompt and prompt_image['bytes'] >= prompt * 4
    assert file_sha(Path(prompt_image['source'])) == prompt_image['sha256']
    table = layout['regions']['constant:model.embed_tokens.weight']
    proof = hashes((args.evidence / 'proof.sha256').read_bytes())
    reference = {}
    for name in ('input-index.tsv', 'mother-descriptors.tsv', 'mother-targets.tsv'):
        data = (args.evidence / name).read_bytes()
        assert sha256(data).hexdigest() == proof[name]
        reference[name] = data
    schedule = {}
    for line in reference['mother-descriptors.tsv'].decode().splitlines()[1:]:
        step, page, base, count = line.split()
        schedule[(int(step, 16), int(page, 16))] = int(base, 16), int(count)
    targets = {}
    for line in reference['mother-targets.tsv'].decode().splitlines()[1:]:
        step, page, mask = line.split()
        targets[int(step, 16), int(page, 16)] = int(mask, 16)
    phase_starts = {}
    for step, page in schedule:
        if page == 0:
            phase_starts[step] = schedule[step, page][0]
    # Get the page identity from the scheduled set of confirmed stage proofs.
    witness_bytes = (args.evidence / 'witness.json').read_bytes()
    assert sha256(witness_bytes).hexdigest() == proof['witness.json']
    phase_records = json.loads(witness_bytes)['phases']
    assert len(phase_records) == len(request['graphs'])

    page_by_proof = {}
    for phase in phase_records:
        step = phase['step']
        assert phase['graph_sha256'] == request['graphs'][step]['sha256']
        for page, digest in enumerate(phase['source_proofs']):
            key = step, digest
            page_by_proof[key] = page if key not in page_by_proof else None

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for position, linked in enumerate(pool.map(lambda n: row_read(args.rows, n), range(length))):
            native, deploy, descriptors, stage_proof = linked
            step = 0 if position < prompt else position - prompt + 1
            page = page_by_proof[step, stage_proof]
            assert page is not None, f'ambiguous native page for input position {position}'
            call, = deploy['calls']
            assert targets[step, page] == 1 << call['target']
            assert len(descriptors) == schedule[step, page][1] == 128
            header = f'phase-{step}/descriptors.bin'
            with (args.evidence / header).open('rb') as stream:
                stream.seek(schedule[step, page][0] - phase_starts[step])
                assert stream.read(128) == descriptors
            selected, = native['locals'][call['group']]
            spec = selected['indexed_read']
            assert spec['table_address'] == table['base']
            assert spec['rows'] * spec['row_words'] * 16 == table['bytes']
            context = dict(step=step, page=page, position=position, prompt_tokens=prompt,
                           prompt_base=prompt_image['base'])
            rows.append(gather_input(native, deploy, descriptors, **context))
            if position == 0:
                sample = native, deploy, descriptors, context
    table_bytes = input_index_table(rows)
    assert table_bytes == reference['input-index.tsv']
    native, deploy, descriptors, context = sample
    invalid = deepcopy(native)
    invalid['locals'][deploy['calls'][0]['group']][0]['read'][0]['address'] += 4
    examples = [
        lambda: gather_input(invalid, deploy, descriptors, **context),
        lambda: gather_input(native, {**deploy, 'source': {}}, descriptors, **context),
        lambda: gather_input(native, deploy, descriptors[:-1] + bytes([descriptors[-1] ^ 1]), **context),
        lambda: gather_input(native, deploy, descriptors, **{**context, 'step': 1}),
        lambda: input_index_table([rows[0], rows[0]]),
    ]
    for reject in examples:
        try:
            reject()
        except ValueError:
            pass
        else:
            raise AssertionError('altered ingress was accepted')
    args.out.mkdir()
    (args.out / 'input-index.tsv').write_bytes(table_bytes)
    result = {'input_table_sha256': sha256(table_bytes).hexdigest(),
              'linked_pages': len(rows), 'sources': dict(Counter(x.source for x in rows)),
              'independent_negatives': len(examples), 'reference_topology': deploy['topology'],
              'physical_execution': False}
    (args.out / 'report.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
