"""Compile a next-token Gather and audit its archived retirement fixture."""
import json
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from struct import unpack_from
import sys

import compact
from image import pack_image
from resident_gather_contract import GATHER, LINK_RECEIVE, LINK_RESERVE, local_image


def verify_file(path, revision):
    data = path.read_bytes()
    if sha256(data).hexdigest() != revision:
        raise ValueError(f'archive hash mismatch: {path}')
    return data


def write_words(path, data):
    assert len(data) % 16 == 0
    path.write_text(''.join(data[i:i + 16][::-1].hex() + '\n' for i in range(0, len(data), 16)))


def main():
    checker, archive, index_plan, layout, vocab, out = map(Path, sys.argv[1:])
    source = spec_from_file_location('check_native_ingress', checker)
    check = module_from_spec(source)
    sys.path.insert(0, str(checker.parent))
    source.loader.exec_module(check)

    position = 638
    step, page, pos, mode, burst, word, lane = map(lambda n: int(n, 16),
        index_plan.read_text().splitlines()[position + 1].split())
    assert (step, page, pos, mode, burst, lane) == (127, 0, position, 2, 0, 8)
    program, _, _, seal = check.row_read(archive, position)
    command, = next(iter(program['locals'].values()))
    source = {'word': word, 'lane_offset': lane}
    image = local_image(command, topology=0x02500031, image_id=1,
                        pack_image=pack_image, retired_index=source)
    header = compact.unpack_header(image[:128])
    commands = compact.unpack_program(image[128:header['task_offset']],
                                      header['instruction_count'], 'local', 2)
    assert header['execution_count'] == 3 and header['instruction_count'] == 7
    assert [item['op'] for item in commands] == ['L_EXEC', 'L_WAIT'] * 3 + ['L_END']
    assert [item['c'] for item in commands if item['op'] == 'L_EXEC'] == [0, 1, 2]
    start = header['execution_offset']
    assert [unpack_from('<H', image, start + 128*i + 4)[0] for i in range(3)] == [
        LINK_RESERVE, LINK_RECEIVE, GATHER]
    assert unpack_from('<I', image, start + 64)[0] == word

    proof = dict(reversed(line.split(None, 1)) for line in (vocab/'proof.sha256').read_text().splitlines())
    logits = verify_file(vocab/'generated/reference.hex', proof['generated/reference.hex'])
    log = verify_file(vocab/'replay-1.log', proof['replay-1.log'])
    audit = json.loads((vocab/'vocabulary-audit.json').read_bytes())
    assert len(logits.splitlines()) == 37984
    numeric = audit['numeric']['1']
    assert numeric['logits'] == 151936 and b'NATIVE_VOCAB_INDEX_COMMIT step=126 ' in log
    token = numeric['token']
    assert f'VOCAB_TOKEN id={token} '.encode() in log
    table = json.loads(layout.read_bytes())['regions']['constant:model.embed_tokens.weight']
    with Path(table['source']).open('rb') as weights:
        weights.seek(token * 8192)
        row = weights.read(8192)
    assert len(row) == 8192 and sha256(row).hexdigest() == numeric['embedding_sha256']
    write_words(out/'image.hex', image)
    write_words(out/'row.hex', row)
    (out/'logits.hex').write_bytes(logits)
    (out/'local.pm').write_bytes(image)
    (out/'assets.json').write_text(json.dumps({
        'archived_stage_sha256': seal, 'source_plan': program['source']['plan_sha256'],
        'program_sha256': sha256(image).hexdigest(), 'pm_bytes': len(image),
        'position': position, 'retired_step': step - 1, 'next_step': step,
        'logit_trace_sha256': sha256(logits).hexdigest(), 'retired_token': token,
        'expected_embedding_sha256': sha256(row).hexdigest(),
        'index_word': word, 'index_lane_offset': lane,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
