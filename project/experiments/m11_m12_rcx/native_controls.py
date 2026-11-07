"""Numerical controls for owner partition, common-potential grouping and threads."""
import json
from pathlib import Path
import subprocess
from native_scene import write


def controls(binary, out, reference=None, broken_binary=None):
    out.mkdir()
    masters = out/'masters.txt'
    masters.write_text('0\n')

    def run(name, names, boxes, threads=4):
        scene = out/(name+'.bin')
        write(scene, names, boxes)
        with (out/(name+'.jsonl')).open('xb') as stdout, (out/(name+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(scene),str(masters),str(threads),'262144','.125','99991'],
                           stdout=stdout,stderr=stderr,check=True)
        return json.loads((out/(name+'.jsonl')).read_text())

    split = [(0,0,[-10,-1,12.89,0,1,14.89]),(0,1,[0,-1,12.89,10,1,14.89]),
             (1,1,[-10,4,12.89,10,6,14.89])]
    one = run('split-one',['target','neighbor'],split,1)
    many = run('split-many',['target','neighbor'],split,4)
    assert one == many, 'Field results depend on thread count'
    total = one['total_ff']
    left, ls, right, rs = one['values'][0][2:]
    assert abs(left-right) <= 5*(ls+rs)+.005*total, 'Reflection symmetry failed'
    single = run('single-owner',['target','neighbor'],
                 [(n,0 if n==0 else owner,b) for n,owner,b in split])
    assert abs(single['values'][0][4]) < 1e-12, 'Absent native group has nonzero charge'
    assert single['total_ff'] == one['total_ff'], 'Owner labels changed the solved field'
    separate = [(0,0,[-10,-1,12.89,10,1,14.89]),
                (1,1,[-10,4,12.89,10,6,14.89]),(2,1,[-10,-6,12.89,10,-4,14.89])]
    a = run('separate-neighbors',['target','a','b'],separate)
    b = run('common-potential',['target','combined'],[(min(n,1),o,box) for n,o,box in separate])
    assert abs(a['total_ff']-b['total_ff']) <= 5*(a['sigma_ff']+b['sigma_ff'])
    assert abs(sum(a['values'][i][0] for i in [1,2])-b['values'][1][0]) <= 5*(sum(a['values'][i][1] for i in [1,2])+b['values'][1][1])
    if reference:
        for name in ['split-one','split-many','single-owner','separate-neighbors','common-potential']:
            assert json.loads((out/(name+'.jsonl')).read_text()) == json.loads((reference/(name+'.jsonl')).read_text()), ('Surface-index change altered control',name)
    disjoint=[(0,0,[0,0,2,2,2+1e-12,4]),
              (0,1,[10,0,2,12,2,4]),(1,1,[5,-2,2,7,4,4])]
    fixed=run('disjoint-near-equal-coordinates',['target','middle'],disjoint)
    assert fixed['total_ff']>0
    lv,ls,rv,rs=fixed['values'][0][2:]
    assert abs(lv-rv)<5*(ls+rs), 'Separated symmetric bodies have inconsistent source charge'
    old_rejected=False
    if broken_binary:
        with (out/'disjoint-old.log').open('xb') as log:
            old=subprocess.run([str(broken_binary),str(out/'disjoint-near-equal-coordinates.bin'),
                 str(masters),'1','262144','.125','99991'],stdout=log,stderr=subprocess.STDOUT)
        old_rejected=old.returncode!=0 and 'another conductor touches' in (out/'disjoint-old.log').read_text()
        assert old_rejected, 'Regression did not reproduce original false merge'
    result=dict(passed=True, thread_invariant=True, reflected_halves=True,
                owner_labels_leave_field_unchanged=True, zero_native_group=True,
                common_zero_potential_grouping=True,
                exact_match_unoptimized_controls=bool(reference),
                disjoint_near_equal_coordinates=True,
                original_false_merge_reproduced=old_rejected,
                disjoint_control_total_ff=fixed['total_ff'],
                limitation='These controls do not independently qualify finite-offset local conductor charge or distributed SPEF nodes.')
    (out/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(controls(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]) if len(sys.argv)>3 else None,
                              Path(sys.argv[4]) if len(sys.argv)>4 else None)))
