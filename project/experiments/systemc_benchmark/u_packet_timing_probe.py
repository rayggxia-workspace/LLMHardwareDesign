"""Audit independent SystemC U service/S timing against actual RTL events.

The input contains no measured service times. This serialized packet recipe
qualifies neither concurrent E/N contention nor LC, physical timing or energy.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def events(path):
    result=[]
    for line in path.read_text().splitlines():
        if line.startswith('EV '):
            m=re.fullmatch(r'EV (\d+) (S_REQ|S_RSP|CMD|DONE|TAKE) ([0-3])',line)
            if not m:
                raise ValueError('malformed event')
            cycle,kind,client=m.groups()
            result.append((int(cycle),kind,int(client)))
    if not result or any(a[0]>b[0]for a,b in zip(result,result[1:])):
        raise ValueError('empty or nonmonotone events')
    return result


def main():
    p=argparse.ArgumentParser()
    for n in ('source','rtl_run','systemc_run','output'):
        p.add_argument(n,type=Path)
    p.add_argument('--bank-source',type=Path,required=True)
    p.add_argument('--systemc-library',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    identity=json.loads((a.source/'source-identity.json').read_text())
    for name,digest in identity['files_sha256'].items():
        if sha(a.source/name)!=digest:
            raise ValueError('source snapshot changed')
    generation=json.loads((a.rtl_run/'fixture/generation.json').read_text())
    if not generation['timing_trace'] or sha(a.rtl_run/'fixture/tb_n_exp_packet.sv')!=generation['instrumented_fixture_sha256']:
        raise ValueError('unqualified instrumented fixture')
    if generation['native_fixture_sha256']!='f2b456fdcb537d8cf770467af41a7c486621148c8d86c20fc9b7db3720d66a9b':
        raise ValueError('unqualified reference fixture set')
    if sha(a.bank_source)!='1871109017b197e12c03beb0a1f2a1bd9f0387898858a831535cf300744fe10e':
        raise ValueError('qualified functional bank changed')
    if sha(a.systemc_library)!='930767c0ec7a203c38552201a22fa2a27a319c47d4d9019096457a674bca0848':
        raise ValueError('SystemC runtime changed')
    log=a.systemc_run/'systemc.log';reference=events(log)
    result,=[json.loads(x[7:])for x in log.read_text().splitlines()if x.startswith('RESULT ')]
    counts=dict(Counter(x[1]for x in reference))
    if counts!={'S_REQ':88,'S_RSP':88,'CMD':55,'DONE':55,'TAKE':55}or result['elapsed_ps']!=2796667 or result['events']!=341:
        raise ValueError('SystemC operation sequence incomplete')
    files=[log,a.source/'source-identity.json',a.rtl_run/'fixture/generation.json',
           a.rtl_run/'fixture/tb_n_exp_packet.sv',a.rtl_run/'fixture/packet-fixtures.tsv',
           a.systemc_run/'systemc-u-packet',a.rtl_run/'obj/Vtb_n_exp_packet',
           a.systemc_run/'build.log',a.rtl_run/'build.log',a.bank_source,a.systemc_library]
    comparisons=[]
    for seed in ('1-143','2-143','2-144'):
        native=a.rtl_run/('run-'+seed+'.log');text=native.read_text()
        if 'PASS N_EXP_PACKET services=11 clock_hz=300000000 elapsed_ps=2796667' not in text:
            raise ValueError('native functional/clock checks missing')
        actual=events(native)
        if actual!=reference:
            different=next((i for i,(x,y)in enumerate(zip(actual,reference))if x!=y),None)
            raise ValueError('native/SystemC event mismatch: '+str((seed,different,len(actual),len(reference))))
        files.append(native);comparisons.append({'initialization':seed,'events':len(actual),'passed':True})
    negative=subprocess.run([str(a.systemc_run/'systemc-u-packet'),'unsupported-latency-table'],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    (a.output/'invalid-input.stdout').write_text(negative.stdout)
    (a.output/'invalid-input.stderr').write_text(negative.stderr)
    if negative.returncode!=1 or 'no input latency table or trace accepted' not in negative.stderr:
        raise ValueError('unsupported input accepted')
    r={'scope':__doc__,'passed':True,'SystemC_version':'3.0.1','clock_hz':300000000,
       'SystemC_input_contains_measured_service_latency':False,
       'events_per_initialization':341,'native_event_comparisons':1023,'event_counts':counts,
       'native_comparisons':comparisons,'testbench_elapsed_ps':2796667,
       'elapsed_includes_artificial_backpressure_and_readback':True,
       'validated_components':['four-client round-robin S arbiter','registered SRAM response and finite two-response capacity',
           'E service read/execute/write/ACK FSM and E13 pipeline','N service read/execute/write/ACK FSM and softmax command pipelines',
           'shared private S service arbitration on the serialized recipe','source hold and completion backpressure'],
       'not_qualified':['simultaneous E/N request contention','LC programs and PM/deployment','payload arithmetic in SystemC',
            'physical STA','full-model integer KV sequence','full-model timing','energy'],
       'hardware_changed':False,'invalid_input_rejected':True,
       'source_identity':identity,'files_sha256':{str(f):sha(f)for f in files},
       'audit_source_sha256':sha(Path(__file__))}
    (a.output/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'passed':True,'native_event_comparisons':1023,'full_model_qualified':False}))


if __name__=='__main__':
    main()
