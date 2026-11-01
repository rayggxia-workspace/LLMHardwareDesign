"""RTL-only integration. Generated wiring is a test fixture, not a physical macro.

Both S implementations are frozen in the source manifest. The SRAM stand-in is
explicitly enabled only for simulation. No synthesis/PPA qualification is implied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MODULES = {
    'dma': 'project/rtl/external_memory/finite_dma.sv',
    's': 'project/rtl/block_feed_v1/block_feed_s_macro.sv',
    'm': 'project/rtl/block_v2/block_v2_m.sv',
    'n': 'project/rtl/block_v2/block_v2_n.sv',
    'r': 'project/rtl/block_library_v1/block_v1_r.sv',
    't': 'project/rtl/block_v1/transaction6k.sv',
}
EXTRA = [
    'project/rtl/block_feed_v1/block_feed_s16k.sv',
    'project/rtl/block_feed_v1/block_feed_loader.sv',
    'project/rtl/block_v2/block_v2_n_group.sv',
    'project/rtl/s_sram/block_feed_s_macro_sram.sv',
    'project/rtl/s_sram/block_feed_s16k_sram.sv',
    'project/rtl/s_sram/s_sram_256x128_freepdk45.sim.sv',
]


def ports(path):
    text = re.sub(r'//[^\n]*', '', path.read_text(encoding='utf-8-sig'))
    name, header = re.search(r'module\s+(\w+)\s*\((.*?)\);', text, re.S).groups()
    result = []
    direction = width = None
    for field in header.split(','):
        field = field.strip()
        match = re.fullmatch(r'(input|output)\s+(?:wire\s+|reg\s+)?(\[[^]]+\]\s*)?(\w+)', field)
        if match:
            direction, width, pname = match.groups()
            width = (width or '').strip()
        else:
            assert re.fullmatch(r'\w+', field), field
            pname = field
        result.append((pname, direction, width))
    return name, result


def fixture():
    """Flatten actual ports; only arbitration and wires live in this fixture."""
    external = ['input wire clk,reset']
    wires = []
    instances = []
    feed = {'a_valid','a_ready','a_bank','a_row','a_tile','a_wide','a_data',
            'b_valid','b_ready','b_bank','b_tile','b_wide','b_half','b_data'}
    ordinary = {'req','wr','addr','din','ready','valid','take','dout'}
    for prefix, source in MODULES.items():
        name, fields = ports(ROOT/source)
        connections = []
        for pname, direction, width in fields:
            net = f'{prefix}_{pname}'
            internal = False
            if pname in ('clk','reset'):
                net = pname
            elif prefix in ('s','m') and pname in feed:
                net = 'feed_'+pname
                internal = True
                if prefix == 's':
                    wires.append(f'wire {width} {net};')
            elif prefix == 's' and pname in ordinary:
                net = 'mem_'+pname
                internal = True
                wires.append(f'wire {width} {net};')
            elif prefix == 'dma' and (pname.startswith('s_') or pname.startswith('stream_')):
                internal = True
                wires.append(f'wire {width} {net};')
            elif prefix == 't' and pname in ('read_valid','read_take','read_data','read_last'):
                net = 'dma_stream_'+{'read_valid':'valid','read_take':'ready','read_data':'data','read_last':'last'}[pname]
                internal = True
            if pname not in ('clk','reset') and not internal:
                external.append(f'{direction} wire {width} {net}')
            connections.append(f'.{pname}({net})')
        instance = name+' '+prefix+'('+','.join(connections)+');'
        if prefix == 's':
            instance = '`ifdef TEST_SRAM\n'+instance.replace(name+' ', 'block_feed_s_macro_sram ',1)+'\n`else\n'+instance+'\n`endif'
        instances.append(instance)
    external += [f'input wire cpu_{x}' for x in ('req','wr','take')]
    external += ['input wire [9:0] cpu_addr','input wire [127:0] cpu_din',
                 'output wire cpu_ready,cpu_valid','output wire [127:0] cpu_dout',
                 'output wire monitor_a_fire,monitor_b_fire,monitor_s_wait']
    glue = '''
assign mem_req=dma_busy?dma_s_req:cpu_req;
assign mem_wr=dma_busy?dma_s_wr:cpu_wr;
assign mem_addr=dma_busy?dma_s_addr:cpu_addr;
assign mem_din=dma_busy?dma_s_din:cpu_din;
assign mem_take=dma_busy?dma_s_take:cpu_take;
assign dma_s_ready=dma_busy&&mem_ready;
assign dma_s_valid=dma_busy&&mem_valid;
assign dma_s_dout=mem_dout;
assign cpu_ready=!dma_busy&&mem_ready;
assign cpu_valid=!dma_busy&&mem_valid;
assign cpu_dout=mem_dout;
assign monitor_a_fire=feed_a_valid&&feed_a_ready;
assign monitor_b_fire=feed_b_valid&&feed_b_ready;
assign monitor_s_wait=mem_req&&!mem_ready;
'''
    return 'module external_memory_fixture(\n'+',\n'.join(external)+'\n);\n'+'\n'.join(wires+instances)+glue+'endmodule\n'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--verilator',default='verilator')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args()
    out=a.out.resolve()
    # Verilator's generated makefiles escape non-ASCII paths incompatibly with
    # GNU make. Compile identical bytes in a private ASCII temporary directory.
    if not str(ROOT).isascii():
        assert not out.exists(), out
        with tempfile.TemporaryDirectory(prefix='llmhw156-') as temporary:
            stage=Path(temporary)
            files=list(MODULES.values())+EXTRA+[
                'project/rtl/block_v2/block_v2_n_exp.svh',
                'project/experiments/external_memory/run.py',
                'project/experiments/external_memory/test.cpp']
            for relative in files:
                target=stage/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/relative,target)
            tool=Path(a.verilator)
            if tool.is_absolute() and not str(tool).isascii():
                install=stage/'tool'
                shutil.copytree(tool.parent.parent,install)
                tool=install/'bin'/tool.name
            command=['python3',stage/'source/project/experiments/external_memory/run.py',
                     '--verilator',str(tool),'--out',stage/'results','--jobs',str(a.jobs)]
            try:
                subprocess.run(list(map(str,command)),check=True)
            finally:
                if (stage/'results').exists():
                    shutil.copytree(stage/'results',out)
        return
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    tool=Path(a.verilator).resolve() if '/' in a.verilator else a.verilator
    if isinstance(tool,Path) and (tool.parent.parent/'share/verilator').exists():
        env['VERILATOR_ROOT']=str(tool.parent.parent/'share/verilator')
        assert (Path(env['VERILATOR_ROOT'])/'verilator_bin').is_file(), 'Prepare an isolated tool installation first'
    commands=[]
    def call(argv,name):
        argv=list(map(str,argv));commands.append(argv)
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        with (out/name).open('w') as f:
            subprocess.run(argv,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    call([tool,'--version'],'tool.txt')
    generated=out/'external_memory_fixture.sv';generated.write_text(fixture())
    sources=[ROOT/x for x in list(MODULES.values())+EXTRA]
    call([tool,'--lint-only','-Wall','--top-module','finite_dma',ROOT/MODULES['dma']],
         'dma-strict-lint.log')
    results={}
    for s in ('cell','sram'):
        flags=['--top-module','external_memory_fixture','-I'+str(ROOT/'project/rtl/block_v2'),
               '-DS_SRAM_SIM',*(['-DTEST_SRAM'] if s=='sram' else []),*sources,generated]
        call([tool,'--lint-only','-Wall','-Wno-fatal',*flags],s+'-lint.log')
        call([tool,'--cc','--exe','--build','-Wno-fatal','-j',a.jobs,'--x-initial','unique','--x-assign','unique',
              '--Mdir',out/(s+'-obj'),'-CFLAGS','-std=c++17 -O1',*flags,HERE/'test.cpp'],s+'-build.log')
        results[s]=[]
        for init,seed in ((1,156),(2,156),(2,157)):
            filename=f'{s}-{init}-{seed}.json'
            call([out/(s+'-obj')/'Vexternal_memory_fixture',f'+verilator+rand+reset+{init}',
                  f'+verilator+seed+{seed}'],filename)
            row=json.loads((out/filename).read_text())
            assert row['passed'] and row['initial_reset']==init and row['initial_seed']==seed
            results[s].append(row)
    sources += [HERE/'test.cpp',Path(__file__).resolve(),ROOT/'project/rtl/block_v2/block_v2_n_exp.svh']
    manifest={str(v.relative_to(ROOT)):hashlib.sha256(v.read_bytes()).hexdigest() for v in sources}
    result=dict(passed=True,scope='RTL only; SRAM simulation stand-in, no physical qualification',
                results=results,source_sha256=manifest,tool=(out/'tool.txt').read_text().strip())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,tool=result['tool'],
         runs={k:[dict(checks=x['checks'],cycles=x['cycles'])for x in v]for k,v in results.items()}),indent=2))


if __name__=='__main__':
    main()
