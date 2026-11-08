"""Check semantic output equality after memoizing ready masks and Dot lookup.

JSON object ordering is not semantic (site sets can enumerate differently).
Retain raw hashes too; never normalize the recovered original evidence bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path);a=p.parse_args()
    checks={}
    for left in sorted(a.before.glob('*.json')):
        if left.name=='summary.json':continue  # contains measured compile_seconds
        right=a.after/left.name;old=left.read_bytes();new=right.read_bytes()
        x,y=json.loads(old),json.loads(new)
        if x!=y:raise ValueError('semantic output differs: '+left.name)
        canonical=json.dumps(x,sort_keys=True,separators=(',',':')).encode()
        checks[left.name]={'before_sha256':hashlib.sha256(old).hexdigest(),
            'after_sha256':hashlib.sha256(new).hexdigest(),'semantically_equal':True,
            'canonical_sha256':hashlib.sha256(canonical).hexdigest()}
    print(json.dumps({'passed':True,'checks':checks}))


if __name__=='__main__':main()
