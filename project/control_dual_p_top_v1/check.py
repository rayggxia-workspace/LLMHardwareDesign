"""Check the synthesizable control shell and the new word/identity transport."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
CORE=PROJECT/'control_rtl_min_v0_1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(cmd,out):
    with out.open('wb') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--verilator',required=True);p.add_argument('--yosys',required=True)
    p.add_argument('--jobs',type=int,default=2);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=a.candidate.read_bytes()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!='3dd63bf7b07d7d5a10fefe3f6c557ed559aaf47b':
        raise ValueError('P candidate Git blob drift')
    stub=out/'pu_p_group.sv';stub.write_text(raw.decode().split(');',1)[0]+');\nendmodule\n')
    sources=[CORE/'lc_min_controller.sv',CORE/'mc_min_controller.sv',CORE/'two_local_link.sv',
             HERE/'dual_p_control_top.sv',HERE/'p_control_endpoint.sv',HERE/'p_word_link.sv',
             PROJECT/'control_native_v1/pj_native_service.sv',PROJECT/'control_native_v1/ucf_native_service.sv',
             PROJECT/'control_native_v1/stored_link.sv',PROJECT/'control_r4_v0_1/p_stored_ack_guard.sv']
    call([a.verilator,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module','dual_p_control_top',
          '-I'+str(CORE),stub,*sources],out/'lint.log')
    warnings=re.findall(r'%Warning-([A-Z0-9_]+)',(out/'lint.log').read_text())
    bad=set(warnings)&{'LATCH','MULTIDRIVEN','UNOPTFLAT','PINMISSING','WIDTHTRUNC'}
    if bad:raise ValueError('structural lint warnings: '+str(bad))
    script=out/'check.ys'
    script.write_text('read_verilog -lib '+json.dumps(str(stub))+'\nread_verilog -sv -I'+str(CORE)+' '+
        ' '.join(json.dumps(str(x)) for x in sources)+'\nhierarchy -check -top dual_p_control_top\n'+
        'synth -top dual_p_control_top -noabc\ncheck -assert\nwrite_json '+json.dumps(str(out/'control.json'))+'\n')
    call([a.yosys,'-s',script],out/'yosys.log')
    call([a.verilator,'--binary','--timing','--assert','--timescale-override','1ns/1ps','-Wno-fatal',
          '--top-module','tb_p_word_link','-j',a.jobs,'--Mdir',out/'obj',HERE/'p_word_link.sv',HERE/'tb_p_word_link.sv'],out/'unit-compile.log')
    call([out/'obj/Vtb_p_word_link'],out/'unit.log')
    if 'PASS p-word-link' not in (out/'unit.log').read_text():raise ValueError('unit pass missing')
    data={'schema':'dual-p-control-shell-check/1','synthesizable_control':True,
          'structural_lint':True,'warnings':{x:warnings.count(x) for x in sorted(set(warnings))},
          'word_link_scenarios':['reservation and wrong address','early ACK blocked','destination backpressure','ACK identity backpressure','reset and post-reset identity'],
          'synthesis_scope':'P group boundaries blackboxed; actual P datapaths separately executed in top regression',
          'source_sha256':{str(x.relative_to(PROJECT.parent)):sha(x) for x in sources},
          'artifacts_sha256':{x.name:sha(x) for x in out.iterdir() if x.is_file()}}
    (out/'report.json').write_text(json.dumps(data,indent=2)+'\n')
    print('PASS dual-P control shell synthesis/lint and five word-link scenarios')
if __name__=='__main__':main()
