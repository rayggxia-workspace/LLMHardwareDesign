"""Bounded source, arithmetic and complete mapping tasks for the block library."""
import json
from pathlib import Path


TOPS = ('block_v1_m8', 'block_v1_vs', 'block_v1_s16k', 'transaction6k')


def source_probe(root, out, cpus, run):
    from make_library import generate
    assert cpus == 16
    result = generate(root, check=True)
    script = 'read_verilog -sv '+ ' '.join(str(p) for p in sorted((root/'project/rtl').rglob('*.sv')))+'\n'
    script += 'hierarchy -check -top block_v1_reassembled\nproc\ncheck -assert\nstat\n'
    (out/'source-check.ys').write_text(script)
    run(['yosys', '-s', str(out/'source-check.ys')], 'source-check.log')
    result['native_yosys_hierarchy_and_process_check'] = True
    result['functional_equivalence_qualified'] = False
    (out/'library-source-probe.json').write_text(json.dumps(result, indent=2)+'\n')


def map_block(root, out, cpus, run, top):
    from io_slots import file_sha
    from make_library import generate
    assert cpus == 16 and top in TOPS
    generate(root, check=True)
    lib = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    sources = sorted((root/'project/rtl').rglob('*.sv'))
    script = 'read_liberty -lib {'+str(lib)+'}\nread_verilog -sv '+' '.join(map(str, sources))+'\n'
    script += 'hierarchy -check -top '+top+'\nsynth -top '+top+' -noabc\n'
    script += 'dfflibmap -liberty {'+str(lib)+'}\nabc -liberty {'+str(lib)+'}\nclean\ncheck -assert\nstat -liberty {'+str(lib)+'}\n'
    script += 'write_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (out/'map.ys').write_text(script); run(['yosys', '-s', str(out/'map.ys')], 'map.log')
    mapped = json.loads((out/'mapped.json').read_text()); module = mapped['modules'][top]
    types = {}
    for cell in module['cells'].values():
        name = cell['type']; assert not name.startswith('$'), name
        types[name] = types.get(name, 0)+1
    ports = {name: dict(direction=p['direction'], bits=len(p['bits'])) for name, p in module['ports'].items()}
    result = dict(schema='block-v1-library-mapping/1', passed=True, top=top,
        liberty_sha256=file_sha(lib), mapped_verilog_sha256=file_sha(out/'mapped.v'),
        mapped_json_sha256=file_sha(out/'mapped.json'), cells=types, cell_count=sum(types.values()), ports=ports,
        all_storage_mapped=True, physical_implementation_completed=False, functional_equivalence_qualified=False,
        scope='Complete standard-cell mapping/inventory of this standalone block only; no physical area, routing, timing or final-netlist function pass')
    (out/'library-mapped.json').write_text(json.dumps(result, indent=2)+'\n')


def byte_probe(root, out, cpus, run):
    from io_slots import file_sha
    assert cpus == 16
    bench = r'''
#include "Vblock_v1_m8.h"
#include "verilated.h"
#include <cstdint>
#include <iostream>
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vblock_v1_m8 dut;
 uint64_t checks=0;
 for(unsigned a=0;a<256;++a)for(unsigned b=0;b<256;++b){
  uint64_t x=0,y=0;
  for(unsigned i=0;i<8;++i){x|=uint64_t((a+i)&255)<<(i*8);y|=uint64_t((b+3*i)&255)<<(i*8);}
  dut.a=x;dut.b=y;dut.eval();
  for(unsigned i=0;i<8;++i){
   int16_t expected=int16_t(int8_t((a+i)&255))*int16_t(int8_t((b+3*i)&255));
   uint16_t actual=(dut.product[i/2]>>((i%2)*16))&65535;
   if(actual!=uint16_t(expected)){std::cerr<<"lane mismatch "<<i<<" "<<a<<" "<<b;return 2;}
   ++checks;
  }
 }
 std::cout<<"{\"passed\":true,\"lane_pair_checks\":"<<checks<<"}\n";
}
'''
    (out/'byte-probe.cpp').write_text(bench)
    compiler = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    source = root/'project/rtl/block_library_v1/block_v1_m8.sv'
    run([compiler, '--cc', '--exe', '--build', '-j', str(cpus), '--top-module', 'block_v1_m8',
         '-Mdir', str(out/'obj'), str(source), str(out/'byte-probe.cpp')], 'byte-build.log')
    run([str(out/'obj/Vblock_v1_m8')], 'byte-result.json')
    result = json.loads((out/'byte-result.json').read_text()); assert result['passed'] and result['lane_pair_checks'] == 524288
    result.update(source_sha256=file_sha(source), physical_implementation_completed=False,
        scope='All65536 signed8 input pairs for each of eight lanes, driven concurrently; not enumeration of all128-bit joint inputs, timing or other block functionality')
    (out/'library-byte-probe.json').write_text(json.dumps(result, indent=2)+'\n')
