"""Three requested archive negatives; all mutations stay in this D-drive folder."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from verify import verify

SOURCE=Path('D:/Projects/LLMHardwareDesign-partition/project/experiments/operator_partition/results/issue-21-run01/evidence.zip')
EXPECTED='f85b1f120065f91d13df95cdf343d35eb48640d9a56d2755b46da5c6ed82306d'
sha=lambda data:hashlib.sha256(data).hexdigest()


def package(name, members):
    dest=HERE/name
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for member,data in members.items():
            info=zipfile.ZipInfo(member,date_time=(2026,10,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    return dest,sha(dest.read_bytes())


def reject(label,path,expected,error,message,mutation,manifest_rehashed):
    try:verify(path,expected)
    except error as exc:
        if str(exc)!=message:raise AssertionError((label,'wrong rejection',str(exc)))
        return {'case':label,'status':'REJECTED_AS_EXPECTED','path':str(path),
                'supplied_sha256':expected,'actual_sha256':sha(path.read_bytes()),
                'manifest_rehashed':manifest_rehashed,'mutation':mutation,
                'exception_type':type(exc).__name__,'reason':str(exc)}
    else:raise AssertionError(label+' unexpectedly accepted')


def main():
    original=SOURCE.read_bytes()
    assert sha(original)==EXPECTED,'original source archive mismatch'
    with zipfile.ZipFile(SOURCE) as z:
        members={n:z.read(n) for n in z.namelist()}
    checks=[]
    checks.append(reject('archive_sha_mismatch',SOURCE,'0'*64,ValueError,'archive SHA mismatch',
                         'Archive unchanged; deliberately supply a wrong external expected SHA',False))
    bad_member=dict(members)
    bad_member['rows.json']+=b'\n'
    path,digest=package('negative-member-index.zip',bad_member)
    checks.append(reject('member_manifest_mismatch',path,digest,ValueError,'member SHA mismatch',
                         'Append newline to rows.json; leave manifest digest unchanged; recompute outer ZIP SHA',False))
    bad_events=dict(members)
    lines=bad_events['events.jsonl'].splitlines()
    first=json.loads(lines[0])
    event=next(e for e in first['events'] if e['kind']=='compute')
    previous=event['read'];event['read']+=4
    lines[0]=json.dumps(first,sort_keys=True,separators=(',',':')).encode()
    bad_events['events.jsonl']=b'\n'.join(lines)+b'\n'
    manifest=json.loads(bad_events['manifest.json'])
    manifest['artifacts']['events.jsonl']=sha(bad_events['events.jsonl'])
    bad_events['manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    path,digest=package('negative-event-ledger.zip',bad_events)
    checks.append(reject('event_accounting_mismatch',path,digest,AssertionError,'counter mismatch',
                         f'First compute.read {previous} -> {previous+4}; rows unchanged; rehash events member in manifest and outer ZIP SHA',True))
    assert sha(SOURCE.read_bytes())==EXPECTED,'original archive changed during checks'
    result={'status':'PASS','observed_utc':datetime.now(timezone.utc).isoformat(),
            'trusted_original_sha256':EXPECTED,'original_archive_unchanged':True,
            'checks':checks,'source_snapshot':'source-snapshot.json',
            'script_sha256':sha(Path(__file__).read_bytes()),
            'scope':'Three specified rejection controls, not exhaustive hostile archive validation or fresh numerical/physical qualification'}
    out=HERE/'negative-archive-results.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':[{k:c[k] for k in ['case','status','reason']} for c in checks],
                      'script_sha256':result['script_sha256'],'result_sha256':sha(out.read_bytes())}))


if __name__=='__main__':main()
