"""Check real linked ingress records and replay an independently verified Gather row."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from indexed_dma_records import BEAT_BYTES, ROW_BYTES, pair, prompt_pair, row_pairs
from native_tlm_timing import Clock, Dram, Images, S128, Transfer

def verify_pair(beats):
    first, second = beats
    # Independently check the v45 client 3 fixed, new and continuation predicates.
    assert first.tag & 1 == 0 and second.tag == first.tag + 1
    assert first.tag >> 1 == second.tag >> 1
    assert first.record_beats == second.record_beats == 2
    assert first.channel == second.channel and first.channel == (first.address >> 11) & 1
    assert first.address % 128 == 0 and second.address == first.address + 64

def rejects(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('malformed record was accepted')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('linked', 'input_table', 'memory', 'layout', 'dram_library', 'dram_config', 'out'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    args.out.mkdir()
    seals = dict(reversed(line.split('  ', 1))
                 for line in (args.linked/'proof.sha256').read_text().splitlines())
    descriptor = (args.linked/'descriptors.bin').read_bytes()
    assert sha256(descriptor).hexdigest() == seals['descriptors.bin']
    assert unpack_from('<IHHII', descriptor)[0:4] == (3, 128, 4, 7)
    table, rows, operand, output, bits = unpack_from('<QIHHH', descriptor, 16)
    assert len(descriptor) == 128 and bits == 32
    layout = json.loads(args.layout.read_bytes())
    prompt = layout['regions']['prompt:0']
    weights = layout['regions']['constant:model.embed_tokens.weight']
    assert weights['base'] == table and weights['bytes'] == rows * ROW_BYTES

    input_rows = args.input_table.read_text().splitlines()
    count = int(input_rows.pop(0))
    assert len(input_rows) == count == prompt['tokens'] + 127
    used_beats = Counter()
    prompt_records = {}
    previous = (-1, -1)
    for i, line in enumerate(input_rows):
        step, page, position, mode, burst, destination, lane = map(
            lambda token: int(token, 16), line.split())
        assert position == i and (step, page) > previous
        previous = (step, page)
        if position >= prompt['tokens']:
            assert step == position - prompt['tokens'] + 1 and mode == 2 and burst == 0
            continue
        assert mode == 1 and step == 0 and burst + lane == prompt['base'] + 4*i
        beats, used = prompt_pair(burst, 0)
        verify_pair(beats)
        assert beats[used].address == burst
        assert prompt['base'] <= beats[0].address < beats[1].address < prompt['base'] + prompt['bytes']
        used_beats[used] += 1
        prompt_records[i] = (beats, used, destination, lane)
    assert used_beats == {0: 256, 1: 256}

    rejects(lambda: pair(64, 0))
    rejects(lambda: pair(0, 1 << 31))
    rejects(lambda: prompt_pair(8, 0))
    rejects(lambda: row_pairs(table, rows, rows, first_record=1))
    rejects(lambda: row_pairs(table, rows, -rows - 1, first_record=1))
    rejects(lambda: row_pairs(table, rows, 0, first_record=(1 << 31) - 63))
    assert row_pairs(table, rows, -1, first_record=1) == row_pairs(table, rows, rows - 1, first_record=1)

    clock = Clock()
    ddr = Dram(clock, args.dram_library, args.dram_config, args.out, credits=32, core_ps=3334)
    memory = Images(args.memory)
    sram = S128(clock, core_ps=3334)
    received = Counter()

    def read_pair(beats, deliver, done):
        # A two-beat v45 record is two distinct request handshakes. Dispatch only
        # these two addresses, observe each return, and do not send explicit CLOSE.
        verify_pair(beats)
        def receive(beat):
            received[beat.channel] += 1
            deliver(beat, memory(beat.address))
            if all(b.tag in tags for b in beats):
                done()
        tags = set()
        for beat in beats:
            def returned(current=beat):
                assert current.tag not in tags
                tags.add(current.tag)
                receive(current)
            ddr.submit(Transfer(beat.address), returned, channel=beat.channel)

    def write_words(first, data, done):
        assert len(data) % 16 == 0
        def word(offset):
            if offset == len(data):
                done()
            else:
                sram.access(first + offset//16, lambda _: word(offset+16), data[offset:offset+16])
        word(0)

    beats, used, destination, lane = prompt_records[0]
    assert destination*16 + lane == operand
    returned = {}
    publish = []
    def publish_index():
        write_words(destination, returned[beats[used].tag], lambda: publish.append(clock.now))
    read_pair(beats, lambda beat, data: returned.update({beat.tag: data}), publish_index)
    clock.until(lambda: len(publish) == 1)
    token = []
    sram.access(operand//16, lambda data: token.append(unpack_from('<i', data, operand % 16)[0]))
    clock.until(lambda: len(token) == 1)

    completion = []
    start_addresses = row_pairs(table, rows, token[0], first_record=1)
    def load_record(i):
        if i == len(start_addresses):
            completion.append(clock.now)
            return
        beats = start_addresses[i]
        pending = {}
        def commit():
            data = b''.join(pending[beat.tag] for beat in beats)
            write_words(output + 8*i, data, lambda: load_record(i+1))
        read_pair(beats, lambda beat, data: pending.update({beat.tag: data}), commit)
    load_record(0)
    clock.until(lambda: len(completion) == 1)
    ddr.close()
    actual = b''.join(sram.words[output+i] for i in range(ROW_BYTES//16))
    with Path(weights['source']).open('rb') as stream:
        stream.seek((token[0] % rows) * ROW_BYTES)
        expected = stream.read(ROW_BYTES)
    assert len(expected) == ROW_BYTES and actual == expected
    assert ddr.stats['callbacks'] == ddr.stats['reads'] == 130
    assert sram.stats['write_beats'] == 516 and sram.stats['read_beats'] == 1
    row_counts = Counter(each[0].channel for each in start_addresses)
    report = {
        'scope': 'real assets and DDR callbacks with v45 client request formatting and SRAM model commits',
        'input_table_sha256': sha256(args.input_table.read_bytes()).hexdigest(),
        'gather_descriptor_sha256': sha256(descriptor).hexdigest(),
        'output_row_sha256': sha256(actual).hexdigest(),
        'prompt_positions_checked': sum(used_beats.values()), 'decode_source_records_checked': 127,
        'prompt_pair_lane_counts': used_beats, 'row_records_by_channel': row_counts,
        'real_ddr_callbacks': ddr.stats['callbacks'], 'received_by_channel': received,
        'committed_output_words': sram.stats['write_beats'] - 4,
        'malformed_format_rejections': 6, 'destination_commit_ps': completion[0],
        'main_v2_executable': False,
    }
    (args.out/'report.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))

if __name__ == '__main__':
    main()
