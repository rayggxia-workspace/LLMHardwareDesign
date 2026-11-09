"""Independent R2 extension; frozen R1 is run in an isolated Python process."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from audit import read_calibration,sha,MODE,IMPLEMENTATION,SCOPE,PAYLOAD


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('R2 anchor count: '+old[:100])
    return text.replace(old,new)


def make_header(old_header,old_profile,new_profile):
    out=once(old_header,'namespace iteration1 {','namespace iteration2_profile {')
    out=once(out,'constexpr bool profile_available=true;','constexpr bool profile_available='+('true' if new_profile else 'false')+';')
    old_costs=[0]+[r['charge_cycles'] for r in old_profile['rows']]
    new_costs=[0]+[r['charge_cycles'] for r in new_profile['rows']] if new_profile else [0]*9
    out=once(out,'frame_cycles{{'+','.join(map(str,old_costs))+'}}','frame_cycles{{'+','.join(map(str,new_costs))+'}}')
    out=once(out,'result_sha256="'+old_profile['result_sha256']+'"','result_sha256="'+(new_profile['result_sha256'] if new_profile else '')+'"')
    out=once(out,'rtl_source_commit="'+old_profile['source_commit']+'"','rtl_source_commit="'+(new_profile['source_commit'] if new_profile else '')+'"')
    extra=r'''
namespace iteration2 {
U supplemental_service(U count,bool r1_enabled,bool enabled,bool qualified){
 const U old_cost=iteration1::supplemental_service(count,r1_enabled,qualified);
 const U new_cost=iteration2_profile::supplemental_service(count,r1_enabled,qualified);
 return enabled?new_cost:old_cost;
}
bool active(bool enabled){return enabled&&iteration1::qualified_operations!=0;}
void emit_active(std::ostream& out,bool r1_enabled,bool enabled){
 if(active(enabled)){iteration2_profile::emit(out,r1_enabled);}
 else{iteration1::emit(out,r1_enabled);}
}
void emit(std::ostream& out,bool r1_enabled,bool enabled){
 const bool selected=active(enabled);
 const U old_cost=iteration1::charged_service_cycles;
 const U candidate=iteration2_profile::candidate_service_cycles;
 const U charged=selected?iteration2_profile::charged_service_cycles:old_cost;
 out<<",\"iteration2_study\":{\"enabled\":"<<(enabled?"true":"false")
    <<",\"R1_enabled\":"<<(r1_enabled?"true":"false")
    <<",\"scope\":\"SCOPE\",\"implementation\":\"IMPLEMENTATION\""
    <<",\"profile_mode\":\"MODE\",\"payload_contract\":\"PAYLOAD\""
    <<",\"new_profile_available\":"<<(iteration2_profile::profile_available?"true":"false")
    <<",\"native_profile_used\":"<<(selected?"true":"false")
    <<",\"active_profile\":\""<<(selected?"R2_stateless":r1_enabled?"R1_four_command":"legacy_scalar")<<"\""
    <<",\"old_calibration_result_sha256\":\""<<iteration1::result_sha256<<"\""
    <<",\"new_calibration_result_sha256\":\""<<iteration2_profile::result_sha256<<"\""
    <<",\"new_calibration_source_commit\":\""<<iteration2_profile::rtl_source_commit<<"\""
    <<",\"stateless_context_preservation_verified\":"<<(iteration2_profile::profile_available?"true":"false")
    <<",\"old_batch_compatibility_verified\":"<<(iteration2_profile::profile_available?"true":"false")
    <<",\"R1_service_cycles\":"<<old_cost<<",\"candidate_service_cycles\":"<<candidate
    <<",\"charged_service_cycles\":"<<charged
    <<",\"delta_cycles\":"<<(static_cast<long long>(charged)-static_cast<long long>(old_cost))
    <<",\"physical_clock_qualified\":false,\"full_LLM_RTL_numeric_proof\":false}";
}
}
'''
    for old,new in [('SCOPE',SCOPE),('IMPLEMENTATION',IMPLEMENTATION),('MODE',MODE),('PAYLOAD',PAYLOAD)]:extra=extra.replace(old,new)
    return out+extra


def generate(repo,out,r1_calibration,calibration=None):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('R2 output must be empty')
    # A separate interpreter keeps frozen `from audit import ...` resolution exact.
    command=[sys.executable,'-B',str(repo/'project/experiments/iterative_speed/round01/generate_round1.py'),
             '--repo',str(repo),'--out',str(out),'--calibration',str(Path(r1_calibration).resolve())]
    process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if process.returncode:raise RuntimeError('frozen R1 generation failed: '+process.stderr)
    r1=json.loads(process.stdout);old_profile=r1['calibration'];new_profile=read_calibration(calibration) if calibration else None
    (out/'round1-generation.json').write_text(json.dumps(r1,indent=2)+'\n',encoding='utf-8')
    source=(out/'model.cpp').read_text(encoding='utf-8');(out/'round1-model.cpp').write_bytes(source.encode())
    source=once(source,'#include "iteration1.hpp"','#include "iteration1.hpp"\n#include "iteration2.hpp"')
    source=once(source,'bool iteration1_nexp=false;','bool iteration1_nexp=false;bool iteration2_nexp=false;')
    source=once(source,'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12)',
                'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12&&argc!=13)')
    source=once(source,'if(argc==12){','if(argc>=12){')
    source=once(source,'iteration1::supplemental_service(o.elements,cfg.iteration1_nexp,nexp_qualified)',
                'iteration2::supplemental_service(o.elements,cfg.iteration1_nexp,cfg.iteration2_nexp,nexp_qualified)')
    source=once(source,'iteration1::emit(std::cout,cfg.iteration1_nexp);',
                'iteration2::emit_active(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp);iteration2::emit(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp);')
    source=once(source,'Study s("study",c,argv[1]);','''if(argc==13){
  const std::string value=argv[12];
  if(value!="0"&&value!="1"){std::cerr<<"invalid iteration2 NExp flag\\n";return 2;}
  c.iteration2_nexp=value=="1";
  if(c.iteration2_nexp&&(!c.iteration1_nexp||!iteration2_profile::profile_available)){
   std::cerr<<"iteration2 requires R1 enabled and a passed stateless calibrated profile\\n";return 2;
  }
 }
 Study s("study",c,argv[1]);''')
    (out/'iteration2.hpp').write_bytes(make_header((out/'iteration1.hpp').read_text(encoding='utf-8'),old_profile,new_profile).encode())
    (out/'model.cpp').write_bytes(source.encode())
    protected={k:v for k,v in r1['generated_sha256'].items() if k!='model.cpp'}
    for name,digest in protected.items():
        if sha(out/name)!=digest:raise ValueError('R2 changed protected R1 source '+name)
    result=dict(round1_generated_sha256=r1['generated_sha256'],frozen_generated_sha256=r1['frozen_generated_sha256'],
                unchanged_generated_sha256=protected,r1_calibration=old_profile,r2_calibration=new_profile,
                generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')},
                scope=SCOPE,frozen_generator_command=command)
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--r1-calibration',type=Path,required=True);parser.add_argument('--calibration',type=Path)
    args=parser.parse_args();print(json.dumps(generate(args.repo,args.out,args.r1_calibration,args.calibration),indent=2))
