"""Pack linked mother pages in the format read by the PR #260 TLM exporter."""
from hashlib import sha256
import json
from pathlib import Path
from zlib import crc32

from route_contract import require


def write_tlm_page_tables(bundle, output, *, pm_base, runtime, prompt_ingress=None):
    manifest_bytes = (bundle / 'deployment.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    schema = manifest['schema']
    require(schema in ('block-native-deployment/1', 'block-native-deployment/2'),
            'unsupported linked native deployment')
    require(type(pm_base) is int and 0 <= pm_base < 1 << 48 and pm_base % 64 == 0,
            'mother program base must be a 64-byte-aligned DDR address')

    def payload(name):
        require(Path(name).name == name, 'invalid linked payload name')
        data = (bundle / name).read_bytes()
        record = manifest['payloads'][name]
        require(len(data) == record['bytes'] and sha256(data).hexdigest() == record['sha256'],
                'linked native payload differs: ' + name)
        return data

    descriptors = payload('descriptors.bin')
    descriptor_base = manifest['descriptor_base']
    require(descriptors and len(descriptors) == 128 * len(manifest['calls']),
            'linked native descriptor extent differs from the calls')
    for index, call in enumerate(manifest['calls']):
        descriptor = descriptors[index * 128:(index + 1) * 128]
        require(call['address'] == descriptor_base + index * 128
                and call['sha256'] == sha256(descriptor).hexdigest(),
                'linked native descriptor identity differs from the call list')
    page_specs = (manifest['mother_pages'] if schema == 'block-native-deployment/2'
                  else [{'file': 'mother.bin', 'descriptor_base': descriptor_base,
                         'call_count': len(manifest['calls'])}])
    packed = bytearray()
    pages = []
    page_ranges = []
    next_descriptor = descriptor_base
    name = 'mother-programs.ddr.bin'
    for spec in page_specs:
        span = spec['call_count'] * 128
        require(span > 0 and spec['descriptor_base'] == next_descriptor,
                'native page descriptor ranges must be contiguous')
        image = payload(spec['file'])
        padded = image + bytes(-len(image) % 64)
        page, _, _ = runtime.parse_pm_image(
            padded, output / name, base=pm_base + len(packed), count=len(image),
            crc=crc32(image), role='mother', topology=manifest['topology'])
        pages.append({**page, 'packed': True, 'descriptor_base': next_descriptor, 'descriptor_bytes': span})
        packed.extend(padded)
        page_ranges.append((next_descriptor, next_descriptor + span))
        next_descriptor += span
    descriptor_end = descriptor_base + len(descriptors)
    require(next_descriptor == descriptor_end, 'native pages do not cover the descriptor arena')
    require(pm_base + len(packed) <= descriptor_base or descriptor_end <= pm_base,
            'packed mother image overlaps the descriptor arena')
    schedule = [{'step': 0, 'pages': pages,
                 'descriptors': {'base': descriptor_base, 'bytes': len(descriptors)}}]
    assets = {
        name: bytes(packed),
        'mother-packed.tsv': f'{pm_base}\t{len(packed)}\t{name}\n'.encode('ascii'),
        'mother-pages.tsv': runtime.mother_page_table_bytes(output, schedule),
        'mother-targets.tsv': runtime.mother_target_table_bytes(output, schedule),
        'mother-descriptors.tsv': runtime.mother_descriptor_table_bytes(output, schedule),
        'descriptors.bin': descriptors,
    }
    if prompt_ingress is not None:
        from event_request_ingress import gather_input, indexed_call_address, input_index_table

        program = prompt_ingress['program']
        call_address = indexed_call_address(program, manifest)
        page, = (i for i, (left, right) in enumerate(page_ranges) if left <= call_address < right)
        index = gather_input(program, manifest, descriptors, step=0, page=page,
                             position=prompt_ingress['position'], prompt_tokens=prompt_ingress['prompt_tokens'],
                             prompt_base=prompt_ingress['prompt_base'])
        require(pages[page]['target_mask'] == 1 << 3, 'indexed page selects a different native target')
        assets['input-index.tsv'] = input_index_table([index])
    source = {'source': manifest['source'], 'deployment_sha256': sha256(manifest_bytes).hexdigest(),
              'topology': manifest['topology']}
    assets['page-source.json'] = json.dumps(source, sort_keys=True, separators=(',', ':')).encode()
    proof = ''.join(f'{sha256(data).hexdigest()}  {name}\n' for name, data in sorted(assets.items())).encode()
    output.mkdir()
    for name, data in assets.items():
        (output / name).write_bytes(data)
    (output / 'proof.sha256').write_bytes(proof)
    return sha256(proof).hexdigest()
