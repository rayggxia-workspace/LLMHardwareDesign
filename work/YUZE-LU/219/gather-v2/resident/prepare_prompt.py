"""Compile the prompt index address into a local Gather descriptor."""
import json
from importlib.util import spec_from_file_location, module_from_spec
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
import sys

from image import pack_image
from resident_gather_contract import local_image

checker, archive, index_table, layout, out = map(Path, sys.argv[1:6])
position = int(sys.argv[6])
sys.path.insert(0, str(checker.parent))
spec = spec_from_file_location('check_native_ingress',checker)
module = module_from_spec(spec)
spec.loader.exec_module(module)
program, _, _, seal = module.row_read(archive, position)
command, = next(iter(program['locals'].values()))
step, page, pos, mode, burst, word, lane = map(lambda n: int(n, 16),
    index_table.read_text().splitlines()[position + 1].split())
assert (step, mode, pos) == (0, 1, position)
assert 16 * word + lane == command['read'][0]['address']
address = burst + lane
image = local_image(command, topology=0x02500031, image_id=1, pack_image=pack_image,
                    prompt_address=address)
regions = json.loads(layout.read_bytes())['regions']
prompt = regions['prompt:0']
table = regions['constant:model.embed_tokens.weight']
prompt_bytes = Path(prompt['source']).read_bytes()
assert sha256(prompt_bytes).hexdigest() == prompt['sha256']
assert address == prompt['base'] + position * 4
offset = (address & ~127) - prompt['base']
assert 0 <= offset <= len(prompt_bytes) - 128
index = unpack_from('<i', prompt_bytes, position * 4)[0]
assert 0 <= index < table['bytes'] // 8192
with Path(table['source']).open('rb') as weights:
    weights.seek(index * 8192)
    row = weights.read(8192)
assert len(row) == 8192
if position == 0:
    assert sha256(row).hexdigest() == '14868690d2b0ea49d89af4a1c417c3a125c417e0f415068c5d9df58fe9c845fb'
assert len(image) == 352 and unpack_from('<Q', image, len(image)-48)[0] == address | (1 << 48)
for name, data, width in (('image', image, 16), ('row', row, 16),
                          ('index', prompt_bytes[position*4:position*4+4], 4),
                          ('prompt', prompt_bytes[offset:offset+128], 16)):
    (out/f'{name}.hex').write_text(''.join(data[i:i+width][::-1].hex()+'\n'
                                        for i in range(0,len(data),width)))
(out/'local.pm').write_bytes(image)
(out/'address').write_text(format(address & ~127,'x')+'\n')
(out/'assets.json').write_text(json.dumps({
    'position':position, 'index':index, 'index_address':address,
    'archived_stage_sha256':seal, 'source_plan':program['source']['plan_sha256'], 'program_sha256':sha256(image).hexdigest(),
    'prompt_sha256':prompt['sha256'], 'table_sha256':table['sha256'], 'row_sha256':sha256(row).hexdigest(),
},indent=2)+'\n')
