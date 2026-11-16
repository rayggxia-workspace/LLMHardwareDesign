"""Instrument accepted U RTL tests, without altering the qualified source.

Profiles describe this exact untimed-client RTL driver and SRAM bank model,
not measured DRAM, top-level timing, or all possible LC instruction streams.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re


def main():
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    original = a.source / 'project/experiments/pu_leaf_base/tb_pu_u_group.sv'
    text = original.read_text()
    # Keep the original arithmetic, error and ACK assertions, including its
    # explicitly injected backpressure. Record durations, not assumed cycles.
    text = text.replace('task automatic execute(input integer lane,', 'task automatic execute(input integer lane,')
    marker = '        cmd_meta[64*lane+:64]=meta;'
    assert text.count(marker) == 1
    text = text.replace(marker, '        time began;\n        began=$time;\n' + marker)
    marker = '        done_ready[lane]=0;\n    endtask'
    assert text.count(marker) == 1
    text = text.replace(marker, '''        done_ready[lane]=0;
        $display("PROFILE kind=service lane=%0d meta=%0h sources=%0d store=%0d ticks=%0d", lane,meta,n,store,($time-began)/10);
    endtask''')
    for begin, end, name in [
        ('        rx_addr=addr;', '        rx_stored_ready=0;\n    endtask', 'write'),
        ('        tx_addr=addr;', '        tx_take=0;\n    endtask', 'read')]:
        assert text.count(begin) == text.count(end) == 1
        if name == 'write':
            text = text.replace(begin, '        time io_began;\n        io_began=$time;\n' + begin)
        else:
            # start_read/release_read are deliberately a pair in this driver.
            text = text.replace('    reg [127:0] answer;', '    time read_began;\n    reg [127:0] answer;')
            text = text.replace(begin, '        read_began=$time;\n' + begin)
        clock = 'io_began' if name == 'write' else 'read_began'
        text = text.replace(end, end.replace('\n    endtask',
            f'\n        $display("PROFILE kind=io direction={name} ticks=%0d",($time-{clock})/10);\n    endtask'))
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / original.name).write_text(text)
    (a.output / 'instrumentation.json').write_text(json.dumps({
        'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
        'instrumented_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'scope': 'accepted U group RTL plus four real SRAM banks; original test commands; no LC or off-chip timing claims'
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
