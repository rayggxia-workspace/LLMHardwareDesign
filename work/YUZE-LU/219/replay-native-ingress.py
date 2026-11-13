"""Execute one emitted prompt Gather using the #260 timed DDR and SRAM backend."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zlib import crc32

from event_request_ingress import gather_input, input_index_table
from export_native_tlm_pages import write_tlm_page_tables
import native_program_runtime as runtime
from export_tlm_mother_program import audit_calls, export
from native_tlm_local import descriptor_key, run_page
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler, Transfer, embedding


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('linked', 'memory', 'layout', 'library', 'dram_config', 'out'):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    source = args.linked
    hashes = dict(reversed(line.split('  ', 1)) for line in (source/'proof.sha256').read_text().splitlines())

    def checked(name):
        data = (source/name).read_bytes()
        assert sha256(data).hexdigest() == hashes[name]
        return data

    native = json.loads(checked('compile.json'))['outputs']['program']
    manifest = json.loads(checked('deployment.json'))
    descriptors = checked('descriptors.bin')
    layout = json.loads(args.layout.read_bytes())
    prompt = layout['regions']['prompt:0']
    output = args.out
    output.mkdir()
    tables = output/'pages'
    context = dict(position=0, prompt_base=prompt['base'], prompt_tokens=prompt['tokens'])
    seal = write_tlm_page_tables(source, tables, pm_base=0x10000000, runtime=runtime,
                                prompt_ingress={'program': native, **context})
    page, = export(tables, seal, 0)
    calls = audit_calls(tables, seal)
    index = gather_input(native, manifest, descriptors, step=0, page=page['page'], **context)
    assert (tables/'input-index.tsv').read_bytes() == input_index_table([index])
    _, row = (tables/'input-index.tsv').read_text().splitlines()
    _, _, _, mode, burst, destination, offset = [int(field, 16) for field in row.split()]
    assert mode == 1

    core_ps = 3334
    clock = Clock()
    sram = S128(clock, core_ps=core_ps)
    images = Images(args.memory)
    dram = Dram(clock, args.library, args.dram_config, output, credits=32, core_ps=core_ps)
    descriptor_base = manifest['descriptor_base']
    pm_base = 0x11000000
    local_data = checked(next(iter(manifest['local_images'].values())))
    _, _, original_local = runtime.parse_pm_image(local_data + bytes(-len(local_data) % 64), source/'local-0.bin', base=pm_base,
                                                   count=len(local_data), crc=crc32(local_data),
                                                   role='local', topology=manifest['topology'])

    def read(address):
        if descriptor_base <= address < descriptor_base + len(descriptors):
            start = address - descriptor_base
            return descriptors[start:start+64]
        return images(address)

    scheduler = Scheduler(clock, dram, read, core_ps=core_ps)
    visible = []

    def input_ready():
        payload = images(burst)
        remaining = iter(range(4))

        def store(_):
            word = next(remaining, None)
            if word is None:
                visible.append(clock.now)
                return
            sram.access(destination + word, store, payload[16*word:16*(word+1)])

        store(None)

    dram.submit(Transfer(burst), input_ready)
    clock.until(lambda: bool(visible))
    scheduler.install_pm(pm_base, len(local_data), mother=False)
    scheduler.bind_local(3, original_local)
    scheduler.install_pm(page['program_base'], page['program_bytes'], mother=True)
    events = []
    provider_key = (3, *descriptor_key(descriptors, manifest['topology']))
    run_page(page, topology=manifest['topology'], descriptor_base=descriptor_base,
             descriptor_bytes=len(descriptors), scheduler=scheduler,
             providers={provider_key: embedding(sram, dram, images)},
             timing=lambda key, issue, launch, done: events.append((key, issue, launch, done)))
    terminal = clock.now
    token, = unpack_from('<i', images(burst), offset)
    table, rows, _, result_address = unpack_from('<QIHH', descriptors, 16)
    backing = layout['regions']['constant:model.embed_tokens.weight']
    assert table == backing['base'] and 8192*rows == backing['bytes'] and 0 <= token < rows
    with Path(backing['source']).open('rb') as stream:
        stream.seek(8192 * token)
        expected = stream.read(8192)
    actual = b''.join(sram.words[result_address + n] for n in range(512))
    assert len(expected) == 8192 and actual == expected and len(events) == 1
    assert dram.stats['reads'] == dram.stats['callbacks'] == 141
    assert sram.stats['write_beats'] == 516 and sram.stats['read_beats'] == 1
    assert visible[0] < events[0][1] < events[0][2] < events[0][3] < terminal
    dram.close()
    result = {'scope': 'old topology, one timed native prompt Gather', 'proof_sha256': seal,
              'input_table_sha256': sha256((tables/'input-index.tsv').read_bytes()).hexdigest(),
              'row_sha256': sha256(actual).hexdigest(), 'sram_writes': sram.stats['write_beats'],
              'terminal_ps': terminal, 'input_visible_ps': visible[0], 'provider': events[0],
              'ddr': dict(dram.stats), 'calls': calls}
    (output/'report.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
