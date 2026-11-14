"""Extract the first sealed prompt index and its expected embedding row."""
import json
import sys
from hashlib import sha256
from pathlib import Path

def write_words(path, data, size):
    if len(data) % size:
        raise ValueError("unaligned fixture")
    path.write_text(''.join(data[i:i+size][::-1].hex() + '\n' for i in range(0, len(data), size)))

def main():
    pm, layout, out = map(Path, sys.argv[1:])
    regions = json.loads(layout.read_bytes())['regions']
    prompt = regions['prompt:0']
    table = regions['constant:model.embed_tokens.weight']
    prompt_data = Path(prompt['source']).read_bytes()
    assert sha256(prompt_data).hexdigest() == prompt['sha256']
    index = int.from_bytes(prompt_data[:4], 'little', signed=True)
    assert 0 <= index < table['bytes'] // 8192
    with Path(table['source']).open('rb') as stream:
        stream.seek(index * 8192)
        row = stream.read(8192)
    expected = '14868690d2b0ea49d89af4a1c417c3a125c417e0f415068c5d9df58fe9c845fb'
    assert len(row) == 8192 and sha256(row).hexdigest() == expected
    program = pm.read_bytes()
    assert len(program) == 352
    write_words(out/'image.hex', program, 16)
    write_words(out/'row.hex', row, 16)
    write_words(out/'index.hex', prompt_data[:4], 4)
    (out/'assets.json').write_text(json.dumps({
        'program_sha256': sha256(program).hexdigest(), 'prompt_sha256': prompt['sha256'],
        'table_asset_sha256': table['sha256'], 'index': index, 'row_sha256': expected,
    }, indent=2) + '\n')

if __name__ == '__main__':
    main()

