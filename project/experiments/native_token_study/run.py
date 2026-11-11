"""Allocated-server full-graph conditional timing with measured native-P gates."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

from model import generate
from lowering import analyse
import audit

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(command, log, cwd, expected=0):
    command=[str(v) for v in command]
    result=subprocess.run(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(result.stdout)
    if result.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(result.returncode)+'\n'+result.stdout.decode(errors='replace')[-3000:])
    return result.stdout.decode()


def calibration_gate(root,out,generated):
    path=root/'run13-result.json'
    if sha(path)!='fa7674d19f36f8b743d8101664a0b3f40aa35aa5f2ea233a77447374a204beb9':
        raise ValueError('native P calibration evidence drift')
    measured=json.loads(path.read_text())
    if not measured['passed'] or len(measured['runs'])!=6:
        raise ValueError('calibration did not pass six actual RTL runs')
    for name,value in measured['source_sha256'].items():
        if sha(root/'source'/name)!=value:raise ValueError('current native RTL differs from measured '+name)
    for name,value in measured['helper_sha256'].items():
        if sha(HERE/'calibration'/name)!=value:raise ValueError('current timing calibration helper drift '+name)
    # Compile and execute the very header used by the model, then compare it
    # with actual P events. Python does not duplicate the header recurrence.
    probe=out/'timing_probe.cpp'
    probe.write_text('''#include <iostream>
#include <algorithm>
#include <stdexcept>
#include <cstdint>
using U=std::uint64_t; constexpr U C=1000;
U ceildiv(U a,U b){return (a+b-1)/b;}
void require(bool v,const char* m){if(!v)throw std::runtime_error(m);}
#include "native_contract.hpp"
int main(){
 for(int bw=0;bw<2;++bw)for(int t=1;t<=4;++t){
  for(int rows: {1,3})std::cout<<"M "<<rows<<" "<<t<<" "<<bw<<" "<<native_model::leaf_latency(rows,t,true,bw)<<"\\n";
  for(int rows: {0,3})std::cout<<"L "<<rows<<" "<<t<<" "<<bw<<" "<<native_model::loader_done(rows,t,bw)<<"\\n";
 }
}
''')
    execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',probe,'-I'+str(generated),'-o',out/'timing_probe'],out/'timing-probe-build.log',out)
    output=execute([out/'timing_probe'],out/'timing-probe.log',out)
    predictions={tuple(x.split()[:4]):int(x.split()[4]) for x in output.splitlines()}
    checks=0
    for run in measured['runs']:
        for row in run['events']:
            if row['kind']=='load':
                key=('L',str(row['rows']),str(row['tiles']),str(row['Bwide']))
                if predictions[key]!=row['latency']:raise ValueError('measured LOAD timing mismatch '+str(row))
                checks+=1
            elif row['kind']=='command' and row['op'] in (10,13):
                key=('M',str(row['rows']),str((row['K']+7)//8),str(row['Bwide']))
                if predictions[key]!=row['leaf_latency']:raise ValueError('measured leaf timing mismatch')
                if row['latency']+2!=predictions[key]+4:raise ValueError('measured command acceptance interval')
                checks+=1
            elif row['kind']=='command':
                expected=12 if row['op']==5 and row['store'] else 4
                if row['latency']+2!=expected:raise ValueError('measured control/write ACK interval')
                checks+=1
            elif row['kind']=='io':
                if row['latency']+2!=6:raise ValueError('measured 128bit IO interval')
                checks+=1
    return dict(passed=True,checks=checks,source_commit=measured['source_commit'],result_sha256=sha(path),
                scope='actual RTL zero-stall leaf/load/control/IO timing; optional controller gaps and conditional adapter are separate')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();repo=root/'source';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('Slurm allocation required, max four cores')
    manifest=json.loads((root/'inputs.json').read_text())
    if not re.fullmatch('[0-9a-f]{40}',manifest['source_commit']):raise ValueError('real source commit required')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        for name,expected in manifest[field].items():
            if sha(base/name)!=expected:raise ValueError('deployment SHA drift '+name)
    lock=json.loads((HERE/'source.json').read_text())
    for name,expected in lock['native_RTL_sha256'].items():
        if sha(repo/name)!=expected:raise ValueError('native RTL lock drift '+name)
    for name,expected in lock['input_sha256'].items():
        if sha(root/'inputs'/name)!=expected:raise ValueError('trace input lock drift '+name)
    out.mkdir(exist_ok=False)
    result=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
        scope='conditional whole-graph timing with actual native-P command calibration; no native LLM generation/weights/quality/physical qualification',
        native_full_model_tokens_per_second=None,admission=[],cases=[],pairs=[],
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]))
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for name in ('decode128','decode512','decode2048','prefill2'):
            trace=root/'inputs'/(name+'.trace');inventory=analyse(trace)
            execute([sys.executable,'-B',HERE/'lowering.py','--trace',trace,'--require-native'],out/(name+'-native-rejected.log'),out,3)
            if inventory['native_admitted']:raise ValueError('unsupported native graph admitted')
            result['admission'].append(inventory)
        execute([sys.executable,'-B',HERE/'native_s32_oracle.py','--out',out/'numeric-oracle.json'],out/'numeric-oracle.log',out)
        result['numeric_oracle']=json.loads((out/'numeric-oracle.json').read_text())
        if not result['numeric_oracle']['passed']:raise ValueError('independent numeric oracle failed')
        generated=out/'generated';result['generation']=generate(repo,generated)
        result['calibration']=calibration_gate(root,out,generated)
        (out/'m-profile.log').write_bytes((root/'inputs/m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',generated/'model.cpp','-I'+str(generated),
                 '-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'model-build.log',out)
        execute([out/'model',root/'inputs/decode512.trace','native_invalid'],out/'reject-invalid-profile.log',out,2)
        jobs=[(work,route+'_'+weight) for work,weight in [('decode512','w8'),('decode512','w16'),('decode2048','w8'),('prefill2','w8')]
              for route in ('native_legacy','native_ctx8')]+[('decode512','native_ctx1_w8')]
        def case(item):
            workload,profile=item;name=workload+'-'+profile;trace=root/'inputs'/(workload+'.trace')
            command=[out/'model',trace,profile]
            text=execute(command,out/(name+'.log'),out)
            rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            if len(rows)!=1 or 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('invalid model receipt '+name)
            row=rows[0]
            checked=audit.check(row,trace,profile)
            record=dict(workload=workload,profile=profile,result=row,audit=checked,command=[str(x) for x in command],log_sha256=sha(out/(name+'.log')))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
            print('CONDITIONAL_CASE '+name+' token/s='+str(row['conditional_tokens_per_second']),flush=True)
            return record
        with ThreadPoolExecutor(max_workers=cpus) as pool:
            for record in pool.map(case,jobs):result['cases'].append(record);save()
        for work,weight in [('decode512','w8'),('decode512','w16'),('decode2048','w8'),('prefill2','w8')]:
            pair=[next(c for c in result['cases'] if c['workload']==work and c['profile']==route+'_'+weight)['result'] for route in ('native_legacy','native_ctx8')]
            checked=audit.check_pair(*pair,root/'inputs'/(work+'.trace'))
            result['pairs'].append(dict(workload=work,weight=weight,audit=checked,
                before_conditional_tokens_s=pair[0]['conditional_tokens_per_second'],after_conditional_tokens_s=pair[1]['conditional_tokens_per_second'],
                speedup=pair[0]['seconds']/pair[1]['seconds']))
        exemplar=next(c for c in result['cases'] if c['workload']=='decode512' and c['profile']=='native_ctx8_w8')
        rejected=[]
        for name,path,change in [
            ('unearned_native_admission',('native_study','native_admitted'),lambda v:True),
            ('hidden_S_expansion',('native_study','P_private_S_bytes'),lambda v:v+1024),
            ('dropped_release',('native_study','P',0,'release_commands'),lambda v:v-1),
            ('missing_weight_work',('native_study','P',0,'source_B_DDR_bytes'),lambda v:v-1),
            ('missing_bank_transaction',('native_study','P',0,'bank_operations',0),lambda v:v-1),
            ('inflated_rate',('conditional_tokens_per_second',),lambda v:v*1.01),
        ]:
            bad=deepcopy(exemplar['result']);target=bad
            for key in path[:-1]:target=target[key]
            target[path[-1]]=change(target[path[-1]])
            try:audit.check(bad,root/'inputs/decode512.trace',exemplar['profile'])
            except (AssertionError,ValueError):rejected.append(name)
            else:raise ValueError('independent audit accepted corrupted receipt '+name)
        result['audit_negative_rejections']=rejected
        result['passed']=True
    except Exception as error:
        result['error']=repr(error);result['traceback']=traceback.format_exc();raise
    finally:save()
    print('NATIVE_TOKEN_CONDITIONAL_PASS 9',flush=True)


if __name__=='__main__':main()
