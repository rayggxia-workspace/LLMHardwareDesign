"""Independent NExp-only extension of the frozen run15 model generator.

No frozen generator, source lock, matrix worker, port rule, or trace is edited.
The optional compiled profile is an actual passed integrated-RTL receipt.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from audit import read_calibration


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('round1 generator anchor count: ' + old[:90])
    return text.replace(old, new)


def header(profile):
    costs = [0] + [r['charge_cycles'] for r in profile['rows']] if profile else [0]*9
    result_sha = profile['result_sha256'] if profile else ''
    commit = profile['source_commit'] if profile else ''
    text = r'''#pragma once
#include <array>
namespace iteration1 {
constexpr bool profile_available=PROFILE_AVAILABLE;
constexpr std::array<U,9> frame_cycles{{FRAME_CYCLES}};
constexpr const char* result_sha256="RESULT_SHA";
constexpr const char* rtl_source_commit="RTL_COMMIT";
std::array<U,9> frames{},qualified_frames{},fallback_frames{};
U operations=0,values=0,old_service_cycles=0,candidate_service_cycles=0,charged_service_cycles=0;
U qualified_operations=0,qualified_values=0,fallback_operations=0,fallback_values=0;
U supplemental_service(U count,bool enabled,bool qualified){
 ++operations;values+=count;
 const U full=count/8,tail=count%8;frames[8]+=full;if(tail)++frames[tail];
 auto& selected_frames=qualified?qualified_frames:fallback_frames;
 selected_frames[8]+=full;if(tail)++selected_frames[tail];
 if(qualified){++qualified_operations;qualified_values+=count;}else{++fallback_operations;fallback_values+=count;}
 const U old_cost=count*16,new_cost=qualified?full*frame_cycles[8]+frame_cycles[tail]:old_cost;
 old_service_cycles+=old_cost;candidate_service_cycles+=new_cost;
 const U cost=enabled?new_cost:old_cost;charged_service_cycles+=cost;return cost;
}
void emit(std::ostream& out,bool enabled){
 out<<",\"iteration_study\":{\"enabled\":"<<(enabled?"true":"false")
    <<",\"scope\":\"replace supplemental NExp service only; original vector_region S/cache/DDR/E service retained\""
    <<",\"payload_contract\":\"signed low16 of each S32 container, U16 zeroextend to S32\""
    <<",\"calibration_result_sha256\":\""<<result_sha256<<"\",\"calibration_source_commit\":\""<<rtl_source_commit<<"\""
    <<",\"profile_available\":"<<(profile_available?"true":"false")
    <<",\"input_format_policy\":\"optimize S32-to-S32; S16-to-S32 remains legacy service\""
    <<",\"native_profile_used\":"<<((enabled&&qualified_operations)?"true":"false")
    <<",\"operations\":"<<operations<<",\"values\":"<<values
    <<",\"qualified_operations\":"<<qualified_operations<<",\"qualified_values\":"<<qualified_values
    <<",\"fallback_operations\":"<<fallback_operations<<",\"fallback_values\":"<<fallback_values
    <<",\"old_service_cycles\":"<<old_service_cycles
    <<",\"candidate_service_cycles\":"<<candidate_service_cycles
    <<",\"charged_service_cycles\":"<<charged_service_cycles
    <<",\"frames_by_count\":[";
 for(int i=0;i<9;++i){out<<(i?",":"")<<frames[i];}
 out<<"],\"qualified_frames_by_count\":[";
 for(int i=0;i<9;++i){out<<(i?",":"")<<qualified_frames[i];}
 out<<"],\"fallback_frames_by_count\":[";
 for(int i=0;i<9;++i){out<<(i?",":"")<<fallback_frames[i];}
 out<<"],\"frame_cycles\":[";
 for(int i=0;i<9;++i){out<<(i?",":"")<<frame_cycles[i];}
 out<<"],\"physical_clock_qualified\":false,\"full_LLM_RTL_numeric_proof\":false}";
}
}
'''
    return text.replace('PROFILE_AVAILABLE', 'true' if profile else 'false').replace('FRAME_CYCLES', ','.join(map(str,costs))).replace('RESULT_SHA', result_sha).replace('RTL_COMMIT', commit)


def generate(repo, out, calibration=None):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):raise ValueError('generation directory must be empty')
    profile = read_calibration(calibration) if calibration else None
    frozen = repo/'project/experiments/sram_port_compare'
    sys.path.insert(0, str(frozen))
    spec = importlib.util.spec_from_file_location('frozen_round1_generate_policy', frozen/'generate_policy.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source = module.generate(out)
    old_generated = {p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')}
    # Keep the exact baseline body for byte-identity evidence and review.
    (out/'frozen-model.cpp').write_bytes(source.encode())
    source = once(source, '#include "detail.hpp"', '#include "detail.hpp"\n#include "iteration1.hpp"')
    source = once(source, 'struct Config {', 'struct Config {\n bool iteration1_nexp=false;')
    source = once(source, 'e_work+=o.elements*16*C;cycles(o.elements*16);',
        'const bool nexp_qualified=o.in.size()==1&&tensors[o.in[0]].bits==32&&tensors[o.out].bits==32;const U nexp_extra=iteration1::supplemental_service(o.elements,cfg.iteration1_nexp,nexp_qualified);e_work+=nexp_extra*C;cycles(nexp_extra);')
    source = once(source, 'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11)',
                  'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12)')
    source = once(source, 'if(argc==11){', 'if(argc>=11){')
    source = once(source, 'Study s("study",c,argv[1]);', '''if(argc==12){
  const std::string value=argv[11];
  if(value!="0"&&value!="1"){std::cerr<<"invalid iteration1 NExp flag\\n";return 2;}
  c.iteration1_nexp=value=="1";
  if(c.iteration1_nexp&&(!iteration1::profile_available||
     (c.name!="queued_pipe_w8"&&c.name!="queued_pipe_w16"))){
   std::cerr<<"iteration1 requires a passed calibrated profile and queued-pipeline workload\\n";return 2;
  }
 }
 Study s("study",c,argv[1]);''')
    source = once(source, 'emit_hardware();emit_compare();emit_policy();',
                  'emit_hardware();emit_compare();emit_policy();iteration1::emit(std::cout,cfg.iteration1_nexp);')
    (out/'iteration1.hpp').write_bytes(header(profile).encode())
    (out/'model.cpp').write_bytes(source.encode())
    protected = {name:digest for name,digest in old_generated.items() if name!='model.cpp'}
    for name,digest in protected.items():
        if sha(out/name) != digest: raise ValueError('round1 changed frozen non-model source '+name)
    result = dict(frozen_generated_sha256=old_generated,unchanged_generated_sha256=protected,
        generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')},
        calibration=profile,scope='NExp supplemental service replacement only; no M, S, DDR, U vector-region or cache change')
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--calibration',type=Path);a=p.parse_args()
    print(json.dumps(generate(a.repo,a.out,a.calibration),indent=2))
