"""Link the native phase/page sequence to the sealed KV and Gather plans."""
import argparse
from collections import Counter
import json
from pathlib import Path

from publish_native_request_handoff import hash_file, read, read_seal, require
from handoff import verify_handoff


def build(request, handoff, kv_path, vocabulary_path, locals_path):
    package = hash_file(request / 'proof.sha256')
    seal = read_seal(request / 'proof.sha256')
    witness_path = request / 'witness.json'
    require(hash_file(witness_path) == seal['witness.json'], 'request witness changed')
    witness = read(witness_path)
    spec = read(handoff / 'algorithm2-input.json')
    verify_handoff(spec, handoff)
    program = read(handoff / 'program.json')
    source = program['source']
    kv = read(kv_path)
    vocab = read(vocabulary_path)
    local_rows = read(locals_path)
    locals_by_page = {(row['step'], row['page']): row for row in local_rows}
    require(len(locals_by_page) == len(local_rows), 'duplicate Gather local sidecar')
    phases = witness['phases']
    require(package == source['package_proof_sha256'] == kv['request_sha256'] == vocab['package_sha256']
            and witness['topology'] == source['topology'] == kv['topology']
            and source['base_sha256'] == kv['base_sha256']
            and hash_file(handoff / 'program.json') == kv['program_sha256'],
            'phase providers use different requests or target bases')
    replacements = {}
    for row in program['replacement_pages']:
        key = row['step'], row['page']
        require(key not in replacements, 'page replacement is ambiguous')
        local = locals_by_page[key]
        require(row['local_pm_sha256'] == local['pm_sha256'] and row['position'] == local['position']
                and row['stage_proof'] == local['original_stage_proof'], 'Gather local sidecar differs')
        if row['dispatch_prerequisite'] is not None:
            replacements[key] = row
    require(len(replacements) == vocab['feedback_edges'] == len(phases)-1,
            'incomplete dependent Gather coverage')

    require(len(phases) == len(kv['phase_records']) == len(vocab['pages']),
            'phase providers differ in length')
    covered = Counter()
    bindings = []
    generation = 0
    kv_end = 0
    for step, (p, k, v) in enumerate(zip(phases, kv['phase_records'], vocab['pages'])):
        pages = p['page_count']
        require(p['step'] == k['step'] == v['step'] == step and p['graph_sha256'] == k['graph_sha256']
                and 0 < pages <= 0xffffffff-generation and v['page'] == pages-1
                and p['source_proofs'][v['page']] == v['stage_proof'],
                f'phase {step} has inconsistent page, KV, or vocabulary identity')
        require(k['first'] == kv_end and k['rows'] > 0
                and k['first'] + k['rows'] == k['exclusive_end']
                and sum(k['stores'].values()) == k['rows'] * kv['streams'],
                f'phase {step} KV row coverage differs')
        kv_end = k['exclusive_end']
        index = None
        if step:
            producer = vocab['pages'][step-1]
            consumer = producer['consumer']
            key = (step, consumer['page'])
            row = replacements[key]
            local = locals_by_page[key]
            link = local['input_source']
            prereq = row['dispatch_prerequisite']
            require(consumer['step'] == step and consumer['local_pm_sha256'] == row['local_pm_sha256']
                    and 0 <= row['page'] < v['page'] and row['stage_proof'] == p['source_proofs'][row['page']]
                    and prereq['step'] == producer['step'] and prereq['terminal_page'] == producer['page']
                    and prereq['terminal_source_proof'] == producer['stage_proof']
                    and row['gather_prerequisite'] == link['prerequisite'] == 'retired_token_sram_commit_ack'
                    and link['kind'] == 'previous_retired_token' and link['retired_step'] == step-1
                    and link['target_completion'] == 'LINK_RECEIVE' and link['lane_offset'] == 8
                    and 0 <= link['word'] < 1024, f'phase {step} index dependency differs')
            index = dict(page=row['page'], generation=generation+row['page']+1, word=link['word'],
                         target=row['target'], local_pm_sha256=row['local_pm_sha256'])
            covered[key] += 1
        bindings.append(dict(step=step, pages=pages, first_generation=generation+1,
                             vocabulary_generation=generation+pages, vocabulary_page=v['page'],
                             vocabulary_version=v['version'], vocabulary_size=v['logits'],
                             graph_sha256=p['graph_sha256'],
                             kv_first=k['first'], kv_rows=k['rows'], kv_end=k['exclusive_end'],
                             kv_commits=sum(k['stores'].values()), index=index))
        generation += pages
    require(set(covered) == replacements.keys() and generation == program['pages']
            and vocab['pages'][-1]['consumer'] is None, 'page generation or final coverage differs')
    return dict(schema='native-request-phase-bindings/1', phases=bindings,
                kv_streams=kv['streams'], total_pages=generation, feedback_edges=len(covered),
                request_sha256=package, base_sha256=source['base_sha256'],
                program_sha256=hash_file(handoff / 'program.json'),
                kv_sha256=hash_file(kv_path), vocabulary_sha256=hash_file(vocabulary_path),
                gather_local_sha256=hash_file(locals_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('request', 'handoff', 'kv', 'vocabulary', 'locals', 'output'):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    binding = build(args.request, args.handoff, args.kv, args.vocabulary, args.locals)
    args.output.mkdir()
    (args.output / 'phase-bindings.json').write_text(json.dumps(binding, sort_keys=True, indent=2) + '\n')
    fields = ('step', 'pages', 'kv_first', 'kv_rows', 'kv_end', 'kv_commits', 'vocabulary_page')
    with (args.output / 'phase-bindings.tsv').open('w') as f:
        for phase in binding['phases']:
            index = phase['index']
            row = (*(phase[k] for k in fields), int(index is not None),
                   index['page'] if index else 0, index['word'] if index else 0)
            print(*row, file=f)


if __name__ == '__main__':
    main()
