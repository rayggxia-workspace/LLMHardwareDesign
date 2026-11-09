"""R4 lane4 service only, generated from frozen best-R2 sources."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from audit import read_calibration,sha,SCOPE,MODE,IMPLEMENTATION

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('R4 anchor count '+old[:100])
    return text.replace(old,new)

def header(base,old_profile,profile):
    source=once(base,'namespace iteration1 {','namespace iteration4_profile {')
    source=once(source,'constexpr bool profile_available=true;','constexpr bool profile_available='+('true' if profile else 'false')+';')
    old=[0]+[r['charge_cycles'] for r in old_profile['rows']];new=[0]+[r['charge_cycles'] for r in profile['rows']] if profile else [0]*9
    source=once(source,'frame_cycles{{'+','.join(map(str,old))+'}}','frame_cycles{{'+','.join(map(str,new))+'}}')
    source=once(source,'result_sha256="'+old_profile['result_sha256']+'"','result_sha256="'+(profile['result_sha256'] if profile else '')+'"')
    source=once(source,'rtl_source_commit="'+old_profile['source_commit']+'"','rtl_source_commit="'+(profile['source_commit'] if profile else '')+'"')
    extra=r'''
namespace iteration4 {
U supplemental_service(U count,bool r1,bool r2,bool enabled,bool qualified){
 const U old_cost=iteration2::supplemental_service(count,r1,r2,qualified);
 const U new_cost=iteration4_profile::supplemental_service(count,r1,qualified);
 return enabled?new_cost:old_cost;
}
bool active(bool enabled){return enabled&&iteration1::qualified_operations!=0;}
void emit_all(std::ostream& out,bool r1,bool r2,bool enabled){
 const bool selected=active(enabled);
 if(selected){
  iteration4_profile::emit(out,r1);
  std::ostringstream baseline;iteration2::emit(baseline,r1,r2);
  std::string text=baseline.str();const std::string key="iteration2_study";
  const auto found=text.find(key);if(found==std::string::npos){throw std::runtime_error("R2 ledger key missing");}
  text.replace(found,key.size(),"iteration2_baseline_study");out<<text;
 }else{iteration2::emit_active(out,r1,r2);iteration2::emit(out,r1,r2);}
 const U old_cost=r2?iteration2_profile::charged_service_cycles:iteration1::charged_service_cycles;
 const U candidate=iteration4_profile::candidate_service_cycles;
 const U charged=selected?iteration4_profile::charged_service_cycles:old_cost;
 out<<",\"iteration4_study\":{\"enabled\":"<<(enabled?"true":"false")
    <<",\"R1_enabled\":"<<(r1?"true":"false")<<",\"R2_enabled\":"<<(r2?"true":"false")
    <<",\"scope\":\"@SCOPE@\",\"implementation\":\"@IMPLEMENTATION@\",\"profile_mode\":\"@MODE@\""
    <<",\"direct_lanes\":4,\"new_profile_available\":"<<(iteration4_profile::profile_available?"true":"false")
    <<",\"native_profile_used\":"<<(selected?"true":"false")
    <<",\"active_profile\":\""<<(selected?"R4_lanes4":r2?"R2_baseline":r1?"R1_four_command":"legacy_scalar")<<"\""
    <<",\"old_calibration_result_sha256\":\""<<iteration2_profile::result_sha256<<"\""
    <<",\"new_calibration_result_sha256\":\""<<iteration4_profile::result_sha256<<"\""
    <<",\"new_calibration_source_commit\":\""<<iteration4_profile::rtl_source_commit<<"\""
    <<",\"default_lanes2_compatibility_verified\":"<<(iteration4_profile::profile_available?"true":"false")
    <<",\"op12_lanes4_execution_verified\":"<<(iteration4_profile::profile_available?"true":"false")
    <<",\"R2_service_cycles\":"<<old_cost<<",\"candidate_service_cycles\":"<<candidate
    <<",\"charged_service_cycles\":"<<charged<<",\"delta_cycles\":"<<(static_cast<long long>(charged)-static_cast<long long>(old_cost))
    <<",\"physical_clock_qualified\":false,\"full_LLM_RTL_numeric_proof\":false}";
}
}
'''
    for key,value in dict(SCOPE=SCOPE,IMPLEMENTATION=IMPLEMENTATION,MODE=MODE).items():extra=extra.replace('@'+key+'@',value)
    return source+extra

def generate(repo,out,r1_calibration,r2_calibration,calibration=None):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('R4 output must be empty')
    command=[sys.executable,'-B',str(repo/'project/experiments/iterative_speed/round02/generate_round2.py'),
        '--repo',str(repo),'--out',str(out),'--r1-calibration',str(Path(r1_calibration).resolve()),'--calibration',str(Path(r2_calibration).resolve())]
    process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if process.returncode:raise RuntimeError('frozen best-R2 generation failed '+process.stderr)
    previous=json.loads(process.stdout);profile=read_calibration(calibration,repo) if calibration else None
    source=(out/'model.cpp').read_text(encoding='utf8');(out/'round2-model.cpp').write_bytes(source.encode())
    source=once(source,'#include "iteration2.hpp"','#include "iteration2.hpp"\n#include <sstream>\n#include "iteration4.hpp"')
    source=once(source,'bool iteration2_nexp=false;','bool iteration2_nexp=false;bool iteration4_nexp=false;')
    source=once(source,'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12&&argc!=13)',
        'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12&&argc!=13&&argc!=14)')
    source=once(source,'if(argc==13){','if(argc>=13){')
    source=once(source,'iteration2::supplemental_service(o.elements,cfg.iteration1_nexp,cfg.iteration2_nexp,nexp_qualified)',
        'iteration4::supplemental_service(o.elements,cfg.iteration1_nexp,cfg.iteration2_nexp,cfg.iteration4_nexp,nexp_qualified)')
    source=once(source,'iteration2::emit_active(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp);iteration2::emit(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp);',
        'iteration4::emit_all(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp,cfg.iteration4_nexp);')
    source=once(source,'Study s("study",c,argv[1]);','''if(argc==14){
  const std::string value=argv[13];
  if(value!="0"&&value!="1"){std::cerr<<"invalid iteration4 NExp flag\\n";return 2;}
  c.iteration4_nexp=value=="1";
  if(c.iteration4_nexp&&(!c.iteration1_nexp||!c.iteration2_nexp||!iteration4_profile::profile_available)){
   std::cerr<<"iteration4 requires R1/R2 enabled and a passed four-lane calibrated profile\\n";return 2;
  }
 }
 Study s("study",c,argv[1]);''')
    (out/'iteration4.hpp').write_bytes(header((out/'iteration1.hpp').read_text(encoding='utf8'),previous['r1_calibration'],profile).encode())
    (out/'model.cpp').write_bytes(source.encode())
    protected={name:digest for name,digest in previous['generated_sha256'].items() if name!='model.cpp'}
    for name,digest in protected.items():
        if sha(out/name)!=digest:raise ValueError('R4 changed protected R2 source '+name)
    result=dict(round2_generated_sha256=previous['generated_sha256'],unchanged_generated_sha256=protected,
        R1_calibration=previous['r1_calibration'],R2_calibration=previous['r2_calibration'],R4_calibration=profile,
        generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')},scope=SCOPE,frozen_generator_command=command)
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--r1-calibration',type=Path,required=True);p.add_argument('--r2-calibration',type=Path,required=True);p.add_argument('--calibration',type=Path)
    a=p.parse_args();print(json.dumps(generate(a.repo,a.out,a.r1_calibration,a.r2_calibration,a.calibration),indent=2))
