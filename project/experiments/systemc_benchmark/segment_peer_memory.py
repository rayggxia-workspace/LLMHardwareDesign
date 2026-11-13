"""Simulation-only quartering of openTPU's large unpacked DRAM arrays.

Preserves four-GiB addressing, data, I/O order and all controller logic. This
works around Verilator 5.042's individual array-range limit, not FPGA capacity.
Only apply to a fresh task-owned Qwen2 overlay, never the frozen source peer.
"""
import argparse
import hashlib
import json
from pathlib import Path


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('unexpected pinned memory source: ' + old[:90])
    return text.replace(old, new)


def transform(text):
    start = text.index('  // the image\'s words, as otpu_native_mem:')
    end = text.index('  // the logical beat of channel', start)
    text = text[:start] + '''  // Simulation storage only: four equal contiguous quarters.
  localparam int H = WORDS / 2;
  localparam int Q = WORDS / 4;
  logic [31:0] mem_q0 [Q], mem_q1 [Q], mem_q2 [Q], mem_q3 [Q];
  function automatic logic [31:0] rdw(input int i);
    if (i < Q) return mem_q0[i];
    if (i < 2*Q) return mem_q1[i-Q];
    if (i < 3*Q) return mem_q2[i-2*Q];
    return mem_q3[i-3*Q];
  endfunction
  task automatic wrw(input int i, input logic [31:0] v);
    if (i < Q) mem_q0[i] = v;
    else if (i < 2*Q) mem_q1[i-Q] = v;
    else if (i < 3*Q) mem_q2[i-2*Q] = v;
    else mem_q3[i-3*Q] = v;
  endtask
''' + text[end:]
    text = once(text, '  logic [31:0] chm [WORDS / 2];',
                '  logic [31:0] chm_lo [Q], chm_hi [Q];')
    text = once(text, "    for (int i = 0; i < H; i++) mem_lo[i] = '0;\n    for (int i = 0; i < WORDS - H; i++) mem_hi[i] = '0;",
                "    if (WORDS < 4 || WORDS % 4 != 0) $fatal(1, \"quarter memory requires WORDS divisible by four\");\n"
                "    for (int i = 0; i < Q; i++) begin\n"
                "      mem_q0[i] = '0; mem_q1[i] = '0; mem_q2[i] = '0; mem_q3[i] = '0;\n    end")
    text = once(text, '          nread = $fread(mem_lo, fd);  // the second continues where the first stopped\n          nread = $fread(mem_hi, fd);',
                '\n'.join('          nread = $fread(mem_q%d, fd);' % i for i in range(4)))
    text = once(text, "          for (int i = 0; i < WORDS / 2; i++) chm[i] = '0;",
                "          for (int i = 0; i < Q; i++) begin chm_lo[i] = '0; chm_hi[i] = '0; end")
    text = once(text, '            nread = $fread(chm, fd);',
                '            nread = $fread(chm_lo, fd);\n            nread = $fread(chm_hi, fd);')
    text = once(text, 'wrw(lbeat(j / 16, c) * 16 + j % 16, chm[j]);',
                'wrw(lbeat(j / 16, c) * 16 + j % 16, j < Q ? chm_lo[j] : chm_hi[j-Q]);')
    return text


def main():
    p = argparse.ArgumentParser()
    p.add_argument('overlay', type=Path)
    a = p.parse_args()
    if not (a.overlay / 'qwen2-overlay.json').is_file():
        raise ValueError('task-owned Qwen2 overlay required')
    path = a.overlay / 'sim/verilator/otpu_ldc_mem.sv'
    before = path.read_bytes()
    after = transform(before.decode('utf-8')).encode('utf-8')
    receipt = a.overlay / 'memory-segmentation.json'
    if receipt.exists():
        raise ValueError('fresh unsegmented overlay required')
    path.write_bytes(after)
    receipt.write_text(json.dumps({
        'scope': 'simulation array representation only; same address/data/controller behavior required',
        'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'capacity_downgraded': False, 'controller_timing_changed': False,
        'full_model_qualified': False,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
