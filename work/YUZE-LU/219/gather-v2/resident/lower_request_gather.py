"""Translate each sealed Gather plan into a resident U local image."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from image import pack_image
from compact import unpack_header
from resident_gather_contract import local_image, GATHER

# Archived row verification retains the original compiler and descriptor seals.
from importlib.util import spec_from_file_location, module_from_spec

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('archive_reader', 'rows', 'input_table', 'output'):
        parser.add_argument(arg, type=Path)
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    spec = spec_from_file_location('archived_index_check', args.archive_reader)
    archive = module_from_spec(spec)
    spec.loader.exec_module(archive)
    rows = args.input_table.read_text().splitlines()
    count = int(rows.pop(0))
    assert len(rows)==count
    args.output.mkdir()
    images = {}

    def lower(item):
        i, fields = item
        step, page, position, mode, burst, dest, lane = map(lambda x:int(x,16),fields.split())
        assert i==position and mode in (1,2)
        program, linked, descriptor, seal = archive.row_read(args.rows,position)
        call, = linked['calls']
        command, = program['locals'][call['group']]
        assert command['read'][0]['address']==16*dest+lane
        assert call['binding_id']==command['binding_id']
        topology = 0x02500031
        if mode == 1:
            if burst % 64 or lane not in range(0, 64, 4):
                raise ValueError('invalid sealed prompt DDR placement')
            source = {'kind': 'prompt_ddr', 'address': burst + lane,
                      'record_address': (burst + lane) & ~127, 'record_bytes': 128}
        else:
            if burst or lane != 8:
                raise ValueError('invalid sealed retired token placement')
            source = {'kind': 'previous_retired_token', 'retired_step': step - 1,
                      'word': dest, 'lane_offset': lane,
                      'prerequisite': 'retired_token_sram_commit_ack',
                      'transport': 'u-stored-link',
                      'target_completion': 'LINK_RECEIVE'}
        local = local_image(command, topology=topology, image_id=1, pack_image=pack_image,
                            prompt_address=source.get('address'),
                            retired_index={k:source[k] for k in ('word', 'lane_offset')} if mode == 2 else None)
        header = unpack_header(local[:128])
        d = header['execution_offset']
        if mode == 2:
            if (header['execution_count'] != 3 or
                    tuple(unpack_from('<H', local, d+i*128+4)[0] for i in range(3)) != (0x103, 0x102, GATHER)
                    or unpack_from('<I', local, d+64)[0] != dest):
                raise ValueError('retired index wait does not bind the planned destination word')
            d += 256
        table, table_rows, offset, target, bits = unpack_from('<QIHHH',descriptor,16)
        a, b, c, e = unpack_from('<IIII',local,d+64)
        assert (a|(b&0xffff)<<32,c,b>>16,e)==(table,table_rows,offset,target) and bits==32
        assert unpack_from('<H',local,d+4)==(GATHER,)
        source_bits, = unpack_from('<Q', local, d+80)
        expected_source = (1 << 48) | source['address'] if mode == 1 else 0
        if source_bits != expected_source:
            raise ValueError('resident PM does not encode the selected index source')
        checksum = sha256(local).hexdigest()
        record = {'step':step, 'page':page, 'position':position, 'source_mode':mode, 'input_source':source,
                  'original_stage_proof':seal, 'plan_sha256':program['source']['plan_sha256'],
                  'pm_sha256':checksum, 'target_topology':topology, 'completion':'destination_commit_ack'}
        return checksum, local, record

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for checksum, local, record in pool.map(lower, enumerate(rows)):
            if checksum not in images:
                (args.output/f'{checksum}.pm').write_bytes(local)
                images[checksum] = len(local)
            records.append(record)
    (args.output/'local-sidecars.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n')
    report = {'source_gather_plans':len(records),'prompt_index_plans':sum(x['source_mode']==1 for x in records),
              'previous_token_plans':sum(x['source_mode']==2 for x in records),'unique_local_images':len(images),
              'prompt_dma_bytes':sum(x['input_source'].get('record_bytes', 0) for x in records),
              'decode_requires_token_owner_binding':True,
              'bytes_by_image':images,'mother_integration':False,'target_executed':False}
    (args.output/'summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,sort_keys=True))

if __name__ == '__main__':
    main()
