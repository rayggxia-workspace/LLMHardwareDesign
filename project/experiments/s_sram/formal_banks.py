"""Strict mapped-to-routed S equivalence at every actual SRAM pin boundary.

The same four physical memories are cut into independent symbolic response
inputs and command outputs, including their clocks. No RAM output is tied to
zero or assumed to match by instance name alone. Macro transistor LVS and real
model functional tests remain separate requirements.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
TOP='block_feed_s_macro_sram'
BANK='s_sram_256x128_freepdk45'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cut(data):
    m=data['modules'][TOP]
    banks=sorted(n for n,c in m['cells'].items() if c['type']==BANK)
    assert len(banks)==4
    expected={'clk0':('input',1),'csb0':('input',1),'web0':('input',1),
              'addr0':('input',8),'din0':('input',128),'dout0':('output',128)}
    proof={}
    for i,name in enumerate(banks):
        c=m['cells'].pop(name);assert not c.get('parameters')
        assert set(c['connections'])==set(expected)
        proof[name]={}
        for pin,(direction,width) in expected.items():
            bits=c['connections'][pin]
            assert len(bits)==width and c['port_directions'][pin]==direction
            port=f'__sram_{i}_{pin}'
            assert port not in m['ports'] and port not in m['netnames']
            # Memory commands are observed outputs; responses are unconstrained
            # symbolic inputs. Actual bank clock and all control bits are kept.
            m['ports'][port]=dict(direction='output' if direction=='input' else 'input',bits=bits[:])
            m['netnames'][port]=dict(hide_name=0,bits=bits[:],attributes={})
            proof[name][pin]=dict(port=port,bits=width,direction=m['ports'][port]['direction'])
    return proof

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--physical',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();assert os.environ.get('SLURM_JOB_ID')
    folder=a.physical.resolve();out=a.out.resolve();out.mkdir(exist_ok=False,parents=True)
    result=dict(passed=False,qualified=False,commands=[],inputs={})
    def save():(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,log,allow_failure=False):
        argv=list(map(str,argv))
        with (out/log).open('w') as f:p=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        result['commands'].append(dict(argv=argv,returncode=p.returncode,log=log,sha256=sha(out/log)));save()
        if not allow_failure:assert p.returncode==0,(log,p.returncode)
        return p.returncode
    try:
        pr=json.loads((folder/'receipt.json').read_text());assert pr['passed'] and pr['pipeline_completed']
        odb=Path(pr['final_files']['6_final.odb']['path'])
        assert sha(odb)==pr['final_files']['6_final.odb']['sha256']
        gold=folder/'input.v';seeded=odb.parent/'1_2_yosys.v'
        if 'resumed_producer' in pr:
            # A separate immutable DRC completion copies the final six files,
            # while the protected synthesis seed stays with its actual route.
            origin=Path(pr['resumed_producer']['path'])
            origin_receipt=origin/'receipt.json'
            assert sha(origin_receipt)==pr['resumed_producer']['receipt_sha256']
            producer=json.loads(origin_receipt.read_text())
            original_odb=Path(producer['final_files']['6_final.odb']['path'])
            assert sha(original_odb)==producer['final_files']['6_final.odb']['sha256']==sha(odb)
            gold=origin/'input.v';seeded=original_odb.parent/'1_2_yosys.v'
            result['inputs'][str(origin_receipt)]=sha(origin_receipt)
            result['inputs'][str(original_odb)]=sha(original_odb)
        assert sha(gold)==sha(seeded)
        assert not seeded.stat().st_mode & 0o222, 'The actual checked synthesis seed must remain read-only'
        gen=next(Path(p) for p in pr['inputs'] if p.endswith('/generation.json'))
        assert sha(gen)==pr['inputs'][str(gen)]
        g=json.loads(gen.read_text());ramlib=Path(g['views']['lib']['path'])
        assert sha(ramlib)==g['views']['lib']['sha256']
        std=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        tool=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
        for p in [folder/'receipt.json',odb,gold,seeded,gen,ramlib,std,tool]:result['inputs'][str(p)]=sha(p)
        full=out/'full-final.v'
        script=f'read_liberty {{{std}}}\nread_liberty {{{ramlib}}}\nread_db {{{odb}}}\n'
        script+='set remove {}\nforeach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0; foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}; if {!$signal} {lappend remove [$master getName]}}}\n'
        script+=f'write_verilog -remove_cells $remove {{{full}}}\n'
        (out/'export.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'export.tcl'],'export.log')
        from native_logic_projection import project
        from structural_view import compare
        from native_formal import inspect
        parsed={};boundaries={}
        for name,source in [('gold',gold),('gate',full)]:
            ys=f'read_liberty -lib {std}\nread_liberty -lib {ramlib}\nread_verilog {source}\nhierarchy -check -top {TOP}\nwrite_json {name}-physical.json\n'
            (out/(name+'.ys')).write_text(ys);run(['yosys','-s',out/(name+'.ys')],name+'-parse.log')
            data=json.loads((out/(name+'-physical.json')).read_text())
            data,projection=project(data,std.read_text())
            if name=='gold':assert projection['removed_count']==0
            else:assert projection['removed_count']>0
            boundaries[name]=cut(data);parsed[name]=data
            result[name+'_protection_projection']=projection
        assert boundaries['gold']==boundaries['gate'],'Physical bank identity, port, direction or width changed'
        result['bank_boundaries']=boundaries['gold']
        negative=copy.deepcopy(parsed['gate']);m=negative['modules'][TOP]
        port='__sram_0_addr0';old=m['ports'][port]['bits'][0]
        ids=[b for n in m['netnames'].values() for b in n['bits'] if isinstance(b,int)]
        bit=max(ids)+1;cell='__negative_address_inverter';assert cell not in m['cells']
        m['cells'][cell]=dict(type='INV_X1',parameters={},attributes={},
                             port_directions={'A':'input','ZN':'output'},connections={'A':[old],'ZN':[bit]})
        m['ports'][port]['bits'][0]=bit;m['netnames'][port]['bits'][0]=bit
        parsed['negative']=negative
        for name,data in parsed.items():
            (out/(name+'-cut.json')).write_text(json.dumps(data)+'\n')
            ys=f'read_json {name}-cut.json\nwrite_verilog -noattr -noexpr -norename {name}-cut.v\n'
            ys+=f'design -reset\nread_liberty -lib {std}\nread_verilog {name}-cut.v\nhierarchy -check -top {TOP}\nwrite_json {name}-readback.json\n'
            (out/(name+'-emit.ys')).write_text(ys);run(['yosys','-s',out/(name+'-emit.ys')],name+'-emit.log')
            result[name+'_readback']=compare(data,json.loads((out/(name+'-readback.json')).read_text()))
        result['formal']={}
        for name in ('gate','negative'):
            log=out/(name+'-kepler.log')
            config=f'format: verilog\ninput_paths:\n  - {out/"gold-cut.v"}\n  - {out/(name+"-cut.v")}\nliberty_files:\n - {std}\nlog_file: {log}\n'
            cfg=out/(name+'.yml');cfg.write_text(config)
            rc=run([tool,'--config',cfg],name+'-command.log',allow_failure=True)
            text=log.read_text();received=inspect(text);received['returncode']=rc
            result['formal'][name]=received;save()
            if name=='gate':assert rc==0 and received['passed']
            else:
                assert not received['passed']
                assert 'Found difference' in text or re.search(r'SAT solver finished: SAT\s*$',text,re.M)
        assert all(sha(p)==h for p,h in result['inputs'].items())
        result.update(passed=True,scope='Strict all-state-boundary mapped-to-routed equivalence with all four memories cut at every clock/control/address/data pin and arbitrary response inputs; actual one-address-bit inversion rejected. SRAM transistor LVS and real model/final function remain separate.')
    except Exception as e:result['failure']=repr(e);raise
    finally:save()

if __name__=='__main__':main()
