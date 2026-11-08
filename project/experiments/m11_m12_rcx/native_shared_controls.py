"""A shared landing alone must not create a false native-capacitance change."""
import json
import os
from pathlib import Path
import subprocess

from native_scene import write
from native_shared_reference import shared


def main():
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    binary=Path(os.environ['COUPLING_SHARED_SOLVER'])
    native=(0,1,0.,-1.,2.,4.,1.,3.)
    upper=[0.,-1.,2.,1.,1.,3.]
    intersections=list(shared(native,[(0,upper)]))
    assert intersections==[(0,tuple(upper))]
    assert not list(shared(native,[(0,[0.,-1.,3.,1.,1.,4.])]))
    masters=out/'masters.txt';masters.write_text('0\n')

    def run(name,boxes):
        scene=out/(name+'.bin');write(scene,['signal'],boxes)
        with (out/(name+'.jsonl')).open('xb') as stdout,(out/(name+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(scene),str(masters),os.environ['COUPLING_THREADS'],
                            '262144','.125','222029'],stdout=stdout,stderr=stderr,check=True)
        return json.loads((out/(name+'.jsonl')).read_text())

    original=run('unpartitioned-native',[(0,1,list(native[2:]))])
    after=run('upper-already-contained',[(0,1,list(native[2:])),(0,0,upper)])
    before=run('consistent-native-reference',[(0,1,list(native[2:])),*[(n,0,list(b)) for n,b in intersections]])
    assert before==after,'Identical physical scene and ownership must produce zero change'
    assert abs(original['total_ff']-after['total_ff'])<5*(original['sigma_ff']+after['sigma_ff'])
    naive=after['values'][0][4]-original['total_ff']
    assert abs(naive)>5*(after['values'][0][5]+original['sigma_ff']), 'Control did not expose the ownership error'
    report=dict(passed=True,conductor_union_unchanged=True,
                false_change_with_inconsistent_ownership_ff=naive,
                consistent_native_change_ff=after['values'][0][4]-before['values'][0][4],
                unpartitioned_total_ff=original['total_ff'],shared_pin_ff=before['values'][0][2],
                native_remainder_ff=before['values'][0][4],
                qualification='Shared-landing bookkeeping control; full-layout electrical and timing checks remain separate.')
    (out/'shared-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
