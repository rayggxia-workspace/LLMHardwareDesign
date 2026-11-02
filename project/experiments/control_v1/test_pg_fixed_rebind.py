"""A changed physical input must never inherit an early PG calculation."""
import hashlib
from pathlib import Path
import tempfile
from pg_fixed_rebind import FILES,match_files


def main():
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory()as temporary:
        root=Path(temporary);candidate={};accepted={}
        for name in FILES:
            for label,rows in [('candidate',candidate),('accepted',accepted)]:
                p=root/label/name;p.parent.mkdir(exist_ok=True);p.write_bytes((name+' original geometry input').encode())
                rows[name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        assert len(match_files(candidate,accepted,sha))==6
        rejected=0
        for name in FILES:
            p=Path(accepted[name]['path']);before=p.read_bytes()
            p.write_bytes(bytes([before[0]^1])+before[1:])
            try:match_files(candidate,accepted,sha)
            except AssertionError:rejected+=1
            else:raise AssertionError('Changed actual input accepted: '+name)
            p.write_bytes(before)
            digest=accepted[name]['sha256'];accepted[name]['sha256']='0'*64
            try:match_files(candidate,accepted,sha)
            except AssertionError:rejected+=1
            else:raise AssertionError('Mismatched declared input accepted: '+name)
            accepted[name]['sha256']=digest
        assert len(match_files(candidate,accepted,sha))==6 and rejected==12
    print('PASS: exact six-file identity; 12 changed-byte/declared-digest cases rejected')


if __name__=='__main__':main()
