"""Stage main64 unchanged sources, then expose/gate native service boundaries for R8.4."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BOOT=ROOT/'project/control_main64_boot_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def instrument(path,pu):
    text=path.read_text();before=text
    ports="""    input wire halt_i,
    output wire request_seen_o,response_seen_o,
    output wire [1023:0] request_descriptor_o,
    output wire [130:0] request_identity_o,
    output wire [15:0] response_status_o,
    output wire [31:0] response_reads_o,response_writes_o,
"""
    first=re.search(r'\binput wire',text).start();text=text[:first]+'\n'+ports+text[first:]
    names=('svc_valid','svc_ready','rsp_valid','rsp_ready') if pu else ('svc_req_valid_o','svc_req_ready_i','svc_rsp_valid_i','svc_rsp_ready_o')
    raw=('raw_service_valid','raw_service_ready','raw_response_valid','raw_response_ready')
    # Only the controller connection changes; adapters retain their original native logic.
    for pin,old,new in zip(('svc_req_valid_o','svc_req_ready_i','svc_rsp_valid_i','svc_rsp_ready_o'),names,raw):
        pattern=r'(\.'+pin+r'\()'+old+r'(\))'
        text,n=re.subn(pattern,lambda m:m[1]+new+m[2],text);assert n==1,(path.name,pin,n)
    valid,ready,rsp,take=names
    descriptor='descriptor' if pu else 'svc_req_descriptor_o'
    ident=('{request_job,request_epoch,request_task_sequence,request_sequence,request_token}' if pu else
           '{svc_req_job_o,svc_req_epoch_o,svc_req_task_sequence_o,svc_req_sequence_o,svc_req_token_o}')
    status='status' if pu else 'svc_rsp_status_i'
    reads='read_bytes' if pu else 'svc_rsp_read_bytes_i'
    writes='write_bytes' if pu else 'svc_rsp_write_bytes_i'
    guard=f"""
    wire raw_service_valid,raw_service_ready,raw_response_valid,raw_response_ready;
    assign {valid}=raw_service_valid && !halt_i;
    assign raw_service_ready={ready} && !halt_i;
    assign raw_response_valid={rsp} && !halt_i;
    assign {take}=raw_response_ready || halt_i;
    assign request_seen_o={valid} && {ready};
    assign response_seen_o={rsp} && {take};
    assign request_descriptor_o={descriptor};
    assign request_identity_o={ident};
    assign response_status_o={status};
    assign response_reads_o={reads};
    assign response_writes_o={writes};
"""
    text=text.replace('endmodule',guard+'endmodule',1)
    path.write_text(text,encoding='utf-8',newline='\n')
    return dict(before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=sha(path),scope='native service ingress halted; accepted native response drains; LC and native recipes unchanged')

def stage(out):
    sys.path.insert(0,str(BOOT))
    spec=importlib.util.spec_from_file_location('r84_boot_stage',BOOT/'stage.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.stage(out)
    reports={}
    for letter in 'pufcj':
        folder=out/'generated'/letter
        path=folder/('lc/pu_'+letter+'_controlled_64.sv' if letter in 'pu' else 'cfj_group_'+letter+'.sv')
        reports[letter]=instrument(path,letter in 'pu')
    data=json.loads((out/'sources.json').read_text())
    remove={'main64_endpoint.sv','main64_control_top.sv','main64_boot_top.sv'}
    data['sources']=[s for s in data['sources'] if Path(s).name not in remove]
    data['sources'] += [str(HERE/(s+'.sv')) for s in ('main64_guarded_link','main64_recovery_endpoint','main64_recovery_control','main64_recovery_engine','main64_recovery_supervisor','main64_recovery_top')]
    (out/'sources.json').write_text(json.dumps(data,indent=2)+'\n')
    (out/'recovery-manifest.json').write_text(json.dumps(dict(schema='main64-recovery-stage/1',instrumentation=reports,
        sources_sha256={s:sha(s) for s in data['sources']},main_raw_sources_unchanged=True),indent=2)+'\n')
    print('PASS R8.4 staged main64 service guards',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();stage(a.out.resolve())

