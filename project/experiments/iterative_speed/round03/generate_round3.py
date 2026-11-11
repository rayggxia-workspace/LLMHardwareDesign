"""Independent finite-M extension; frozen R2 generation remains byte preserved."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from audit import read_calibration, sha, SCOPE

HERE=Path(__file__).resolve().parent

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('R3 anchor count: '+old[:120])
    return text.replace(old,new)

def header(profile):
    source=(HERE/'iteration3.hpp.in').read_text(encoding='utf8')
    values={'AVAILABLE':'true' if profile else 'false','READ_ACK':str(profile['read_ack_cycles'] if profile else 0),
            'WRITE_ACK':str(profile['write_ack_cycles'] if profile else 0),'RESULT_SHA':profile['result_sha256'] if profile else '',
            'COMMIT':profile['source_commit'] if profile else '', 'SCOPE':SCOPE}
    fields='old_tiles final_outputs old_adapter_cycles old_M_cycles commands leaf_accepts commits completions read_requests read_acks write_requests write_acks core_active_cycles control_cycles wall_subcycles alignment_subcycles read_calendar_stalls write_calendar_stalls peak_buffers peak_reads peak_completions peak_calendar_intervals'.split()
    values['FIELDS']='\n'.join('  out<<",\\"'+name+'\\":"<<s.'+name+';' for name in fields)
    for key,value in values.items():source=source.replace('@'+key+'@',value)
    if '@' in source:raise ValueError('unsubstituted R3 header')
    return source

def generate(repo,out,r1_calibration,r2_calibration,calibration=None):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('R3 output must be empty')
    command=[sys.executable,'-B',str(repo/'project/experiments/iterative_speed/round02/generate_round2.py'),
             '--repo',str(repo),'--out',str(out),'--r1-calibration',str(Path(r1_calibration).resolve()),'--calibration',str(Path(r2_calibration).resolve())]
    process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if process.returncode:raise RuntimeError('frozen R2 generation failed '+process.stderr)
    previous=json.loads(process.stdout);profile=read_calibration(calibration) if calibration else None
    for name in ('model.cpp','matrix.inc','context_worker.inc'):
        (out/('round2-'+name)).write_bytes((out/name).read_bytes())
    source=(out/'model.cpp').read_text(encoding='utf8')
    source=once(source,'#include "iteration2.hpp"','#include "iteration2.hpp"\n#include "finite_control.hpp"\n#include "iteration3.hpp"')
    source=once(source,'struct Config {','struct Config {\n int iteration3_buffers=0;')
    source=once(source,'std::vector<std::shared_ptr<Burst>> pending;};','std::vector<std::shared_ptr<Burst>> pending;unsigned finite_a=0,finite_b=0;};')
    source=once(source,' void p_result_store(int group,U bytes){','#include "native_service.inc"\n void p_result_store(int group,U bytes){')
    source=once(source,'emit_hardware();emit_compare();','emit_hardware();emit_compare();emit_finite();')
    source=once(source,'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12&&argc!=13)',
                'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=12&&argc!=13&&argc!=14)')
    source=once(source,'if(argc==13){','if(argc>=13){')
    source=once(source,'Study s("study",c,argv[1]);','''if(argc==14){
  const std::string value=argv[13];
  if(value!="0"&&value!="1"&&value!="2"){std::cerr<<"invalid iteration3 buffer count\\n";return 2;}
  c.iteration3_buffers=value[0]-'0';
  if(c.iteration3_buffers&&(!iteration3::profile_available||!c.iteration1_nexp||!c.iteration2_nexp||
     c.pbytes!=16384||c.p_port_quarters!=4||c.contexts!=8||c.mcount!=2)){
   std::cerr<<"iteration3 requires passed finite service profile, R1/R2,16KiB and fixed ports/contexts\\n";return 2;
  }
 }
 Study s("study",c,argv[1]);''')
    for name in ('matrix.inc','context_worker.inc'):
        path=out/name;text=path.read_text(encoding='utf8')
        anchor='U start=now(),send=store[worker].reserve(start,s_port_duration(cfg,worker,p->abytes+p->bbytes));'
        tail='pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);'
        start=text.index(anchor);end=text.index(tail,start)+len(tail);old=text[start:end]
        ctx='static_cast<unsigned>(slot)' if name=='context_worker.inc' else '0'
        text=text[:start]+'if(finite_target(o,*p)){finite_service(o,*p,worker,'+ctx+');}else{\n'+old+'\n   }'+text[end:]
        text=once(text,'p_result_store(worker,bytes);','if(!finite_target(o,*p)){p_result_store(worker,bytes);}')
        if name=='matrix.inc':
            text=once(text,'buffer.ready.write(new Tile{r,n,k,batch,rr,col,kk,seq++%2,kk+k==o.k,abytes,bbytes,std::move(pending)});',
                '''auto* finite_tile=new Tile{r,n,k,batch,rr,col,kk,seq++%2,kk+k==o.k,abytes,bbytes,std::move(pending)};
     if(finite_target(o,*finite_tile)){
      const U apad=ceildiv(U(limit)*a.bits/8,64)*64,bpad=ceildiv(U(8)*limit*bbits/8,64)*64;
      finite_tile->finite_a=static_cast<unsigned>(resident?U(kk)*4:kk<cache_k?U(kk)*4:prefix_bytes+finite_tile->bank*apad);
      finite_tile->finite_b=static_cast<unsigned>((resident?full_a:prefix_bytes+2*apad)+finite_tile->bank*bpad);
      finite_layout(*finite_tile,resident,full_a,prefix_bytes,apad,bpad);
     }
     buffer.ready.write(finite_tile);''')
        else:
            text=once(text,'task->slot=slot;task->abank=abank;task->bbank=bbank;',
                '''if(finite_target(o,task->tile)){
        const U apad=ceildiv(U(limit)*a.bits/8,64)*64,bpad=ceildiv(U(8)*limit*bbits/8,64)*64;
        task->tile.finite_a=static_cast<unsigned>(prefix?U(kk)*4:prefix_bytes+abank*apad);
        task->tile.finite_b=static_cast<unsigned>(prefix_bytes+2*apad+bbank*bpad);
        finite_layout(task->tile,false,full_a,prefix_bytes,apad,bpad);
       }
       task->slot=slot;task->abank=abank;task->bbank=bbank;''')
        path.write_bytes(text.encode())
    (out/'model.cpp').write_bytes(source.encode())
    (out/'finite_control.hpp').write_bytes((HERE/'finite_control.hpp').read_bytes())
    (out/'native_service.inc').write_bytes((HERE/'native_service.inc').read_bytes())
    (out/'iteration3.hpp').write_bytes(header(profile).encode())
    protected={name:digest for name,digest in previous['generated_sha256'].items() if name not in ('model.cpp','matrix.inc','context_worker.inc')}
    for name,digest in protected.items():
        if sha(out/name)!=digest:raise ValueError('R3 changed frozen unrelated source '+name)
    result=dict(round2_generated_sha256=previous['generated_sha256'],unchanged_generated_sha256=protected,
                R1_calibration=previous['r1_calibration'],R2_calibration=previous['r2_calibration'],R3_calibration=profile,
                generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')},scope=SCOPE,
                frozen_generator_command=command)
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--r1-calibration',type=Path,required=True);p.add_argument('--r2-calibration',type=Path,required=True);p.add_argument('--calibration',type=Path)
    a=p.parse_args();print(json.dumps(generate(a.repo,a.out,a.r1_calibration,a.r2_calibration,a.calibration),indent=2))
