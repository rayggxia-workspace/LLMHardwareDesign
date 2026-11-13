"""Emit a small RTL equivalence probe for simulation-only array segmentation.

Checks actual $fread ordering, physical-channel scatter, every word, and writes
across all quarter boundaries. Controller logic is outside this unit probe.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from segment_peer_memory import transform


def extract(text, name, phys):
    start = text.index('  // the image\'s words, as otpu_native_mem:') if 'mem_lo [H]' in text else text.index('  // Simulation storage only:')
    end = text.index('  // clocks', start)
    storage = text[start:end]
    start = text.index('  string dir;')
    end = text.index('  always @(posedge clk) if (dump)', start)
    loader = text[start:end]
    return ('module %s;\nlocalparam int WORDS=1024,PHYS=%d,SID=0;\n'
            'localparam bit CHASH=1;\nlongint n_rd[2],n_wr[2],n_miss[2];\n' % (name, phys)
            + storage + loader + 'endmodule\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('original', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    original = a.original.read_text(encoding='utf-8')
    changed = transform(original)
    # The clock, bridge, command and controller sections must be byte identical.
    def controller(t):
        return t[t.index('  // clocks'):t.index('  string dir;')]
    assert controller(original) == controller(changed)
    assert original[original.index('  always @(posedge clk) if (dump)'):] == changed[changed.index('  always @(posedge clk) if (dump)'):]
    (a.output / 'original.sv').write_text(original, encoding='utf-8')
    (a.output / 'segmented.sv').write_text(changed, encoding='utf-8')
    values = [(i * 1234567 + 0x89abcdef) & 0xffffffff for i in range(1024)]
    (a.output / 'dram_0.bin').write_bytes(b''.join(struct.pack('>I', v) for v in values))
    for c in range(2):
        words = []
        for j in range(512):
            m = j // 16
            lb = m * 2 + (c ^ (m.bit_count() & 1))
            words.append(values[lb * 16 + j % 16])
        (a.output / ('ch%d.bin' % c)).write_bytes(b''.join(struct.pack('>I', v) for v in words))
    parts = [extract(original, 'base%d' % p, p) + extract(changed, 'seg%d' % p, p) for p in range(2)]
    parts.append('''module tb;
base0 b0(); seg0 s0(); base1 b1(); seg1 s1();
initial begin
 logic [31:0] expected, value;
 #1;
 for(int i=0;i<1024;i++)begin
  expected=32'(i)*32'd1234567+32'h89abcdef;
  if(b0.rdw(i)!==expected||s0.rdw(i)!==expected||b1.rdw(i)!==expected||s1.rdw(i)!==expected)
   $fatal(1,"load mismatch word %0d",i);
 end
 for(int i=0;i<1024;i++)begin
  value=32'(i)*32'd7411+32'h12345678;
  b0.wrw(i,value);s0.wrw(i,value);b1.wrw(i,value);s1.wrw(i,value);
 end
 for(int i=0;i<1024;i++)begin
  expected=32'(i)*32'd7411+32'h12345678;
  if(b0.rdw(i)!==expected||s0.rdw(i)!==expected||b1.rdw(i)!==expected||s1.rdw(i)!==expected)
   $fatal(1,"write mismatch word %0d",i);
 end
 $display("MEMORY_EQUIVALENCE words=1024 phys=0,1 all_quarters=passed");
 $finish;
end
endmodule
''')
    (a.output / 'probe.sv').write_text('\n'.join(parts), encoding='utf-8')
    (a.output / 'inputs.json').write_text(json.dumps({
        'original_sha256': hashlib.sha256(a.original.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'transform_sha256': hashlib.sha256(Path(__file__).with_name('segment_peer_memory.py').read_bytes()).hexdigest(),
        'controller_text_identical': True, 'dump_text_identical': True,
        'scope': '1024-word storage probe; not full controller or full-model evidence',
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
