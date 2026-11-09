"""Read server logs, require all positive cases and a genuine failing negative."""
import argparse
import json
from pathlib import Path
import re


def check(positive,negative,negative_exit):
    text=positive.read_text(encoding='utf-8')
    records=[]
    expression=r'ELASTIC_CASE_PASS width=(\d+) old=(\d+) cycles=(\d+) throughput_beats=(\d+) sent=(\d+) received=(\d+) reset_discarded=(\d+) stalls=(\d+) full_cycles=(\d+) simultaneous=(\d+)'
    for match in re.finditer(expression,text):
        values=list(map(int,match.groups()))
        row=dict(zip(('width','old','cycles','throughput_beats','sent','received','reset_discarded','stalls','full_cycles','simultaneous'),values))
        if row['cycles']!=256 or row['throughput_beats']!=(128 if row['old'] else 256):
            raise ValueError('throughput receipt mismatch '+str(row))
        if row['sent']!=row['received']+row['reset_discarded'] or not row['stalls'] or not row['reset_discarded']:
            raise ValueError('conservation/coverage mismatch '+str(row))
        if not row['old'] and (row['full_cycles']==0 or row['simultaneous']<256):
            raise ValueError('elastic full/simultaneous coverage absent')
        records.append(row)
    if {(r['width'],r['old']) for r in records}!={(135,0),(135,1),(517,0),(517,1)} or len(records)!=4:
        raise ValueError('missing/duplicate cases')
    if 'ELASTIC_COMPARE_PASS cases=4 load_explicit_empty=1 widths=135,517' not in text or 'LOAD_EXPLICIT_EMPTY_PASS negative_ready_predicate_exercised=1' not in text:
        raise ValueError('positive completion proof missing')
    failure=negative.read_text(encoding='utf-8')
    if negative_exit==0 or 'EXPECTED_NEGATIVE_READY_AS_EMPTY_DETECTED' not in failure or 'LOAD_COMPLETION_BEFORE_OUTPUT_RETIREMENT' not in failure:
        raise ValueError('unsafe completion gate did not fail for the expected reason')
    return dict(passed=True,cases=records,negative_exit=negative_exit,
                negative='using not-full/ready as empty rejected before output retirement',
                scope='isolated link throughput and functional protocol only; not whole-P or token/s/physical acceptance')


def main():
    p=argparse.ArgumentParser();p.add_argument('--positive',type=Path,required=True)
    p.add_argument('--negative',type=Path,required=True);p.add_argument('--negative-exit',type=int,required=True)
    a=p.parse_args();print(json.dumps(check(a.positive,a.negative,a.negative_exit),indent=2))


if __name__=='__main__':main()
