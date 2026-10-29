"""Capture one immutable completed receipt without duplicating all prior trials.

Run locally. Large physical files remain source-indexed. Every captured native
file is checked against the completed receipt before lossless gzip storage.
"""
from pathlib import Path,PurePosixPath
import argparse,datetime,gzip,hashlib,json,re,shlex,subprocess

REMOTE='/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027'
HOST='yuzelu@10.129.166.172'


def fetch(relative,name,out):
    parts=PurePosixPath(relative).parts
    assert parts and all(re.fullmatch(r'[A-Za-z0-9_.-]+',p) and p not in ['.','..'] for p in parts)
    assert re.fullmatch(r'[A-Za-z0-9_-]+',name)
    source=REMOTE+'/'+relative
    def raw(filename):
        path=PurePosixPath(filename)
        assert not path.is_absolute() and path.parts and all(re.fullmatch(r'[A-Za-z0-9_.-]+',part) and part not in ['.','..'] for part in path.parts)
        return subprocess.check_output(['ssh',HOST,'cat -- '+shlex.quote(source+'/'+filename)])
    receipt=raw('execution.json');q=json.loads(receipt)
    completion_field='completed_utc' if q.get('completed_utc') else 'finished_utc'
    assert q.get(completion_field),'An active receipt is not terminal evidence'
    index_field='files' if 'files' in q else 'outputs'
    assert isinstance(q.get(index_field),dict),'Closed native file index missing'
    dest=Path(out)/name;dest.mkdir(parents=True,exist_ok=False)
    records=[]
    def save(filename,data):
        p=dest/(filename+'.gz');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(data,mtime=0))
        records.append({'name':filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                        'stored_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    save('execution.json',receipt)
    for filename,meta in sorted(q[index_field].items()):
        if filename=='execution.json':continue
        selected_native_gzip=filename in ['target_pin_access.tsv.gz','before_actual_target.tsv.gz','after_actual_target.tsv.gz','branch_access.tsv.gz','whole_access.tsv.gz','before_access.tsv.gz','after_access.tsv.gz','actual_restored_bit433.tsv.gz']
        if (Path(filename).suffix not in ['.json','.tcl','.log','.txt','.tsv','.csv','.drc','.guide','.v','.ys'] and not selected_native_gzip) or meta['bytes']>8*1024*1024:continue
        if any(s in filename for s in ['.cells.','.pdn.']):continue
        data=raw(filename)
        assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256'],filename
        save(filename,data)
    assert raw('execution.json')==receipt,'Closed receipt changed during capture'
    manifest={'source':source,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_completed_utc':q[completion_field],'receipt_completion_field':completion_field,'receipt_file_index':index_field,'records':records,'full_qualification':False,
              'scope':'LOSSLESS_CLOSED_TERMINAL_EVIDENCE_ONLY; physical acceptance remains in the native receipt'}
    (dest/'capture.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('CLOSED_TERMINAL_CAPTURED',name,len(records),'SHA-verified raw files; not full physical qualification')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--relative',required=True);p.add_argument('--name',required=True);p.add_argument('--out',required=True);a=p.parse_args();fetch(a.relative,a.name,a.out)
