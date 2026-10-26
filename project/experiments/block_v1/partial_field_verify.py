"""Straight-wire local charge pilot; preserve every failed scientific gate.

FV instrumentation reports the original conductor-face flux, without changing
the Laplace matrix/solver. Gaussian bins must converge toward that flux.
This pilot cannot qualify branches, pairwise node coupling or whole blocks.
"""
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import types


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def fv_source(text):
    replacements=[
        ('    index = -np.ones(shape, dtype=np.int64)',
         '    free_x = np.broadcast_to(centers[0][:,None,None],shape)[free].copy()\n'
         '    index = -np.ones(shape, dtype=np.int64)'),
        ('    matrix = np.zeros((len(names), len(names) + 1))',
         '    partial = np.zeros((len(names),len(names)+1,2))\n'
         '    matrix = np.zeros((len(names), len(names) + 1))'),
        ('            matrix[master, net] = EPS0 * np.sum(wire_g[s] * (v - phi[wire_cell[s]]))',
         '            charge = EPS0 * wire_g[s] * (v - phi[wire_cell[s]])\n'
         '            matrix[master, net] = np.sum(charge)\n'
         '            left = free_x[wire_cell[s]] < 0\n'
         '            partial[net,master,0] = np.sum(charge[left])\n'
         '            partial[net,master,1] = np.sum(charge[~left])'),
        ('    return names, matrix, n',
         '    partial[:,-1,:] = -partial[:,:-1,:].sum(axis=1)\n'
         '    assert np.allclose(partial[:,:-1,:].sum(axis=2),matrix[:,:-1].T,rtol=1e-10,atol=1e-12)\n'
         '    return names, matrix, n, partial')]
    for before,after in replacements:
        assert text.count(before)==1,before;text=text.replace(before,after)
    return text


def grid(spec_path):
    spec=json.loads(Path(spec_path).read_text());prefix=Path(spec['prefix'])
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    import numpy as np
    import pyamg
    source=prefix/'source/fv3d_golden.py';assert sha(source)==spec['source_sha256']
    text=fv_source(source.read_text());module=types.ModuleType('research_fv_partial')
    module.__dict__['__file__']=str(source)
    exec(compile(text,'research-fv-partial.py','exec'),module.__dict__)
    original=pyamg.smoothed_aggregation_solver;residuals=[]
    def checked(matrix,**kwargs):
        solver=original(matrix,**kwargs)
        class Receiver:
            def solve(self,rhs,**options):
                solution=solver.solve(rhs,**options)
                residual=float(np.linalg.norm(matrix@solution-rhs)/np.linalg.norm(rhs))
                residuals.append(residual);assert residual<1e-8
                return solution
        return Receiver()
    pyamg.smoothed_aggregation_solver=checked
    names,matrix,cells,partial=module.solve(3.9,[],spec['boxes'],[],spec['h'],spec['far'])
    result=dict(names=names,matrix_ff=matrix.tolist(),partial_ff=partial.tolist(),free_cells=cells,
        h_um=spec['h'],far_um=spec['far'],linear_relative_residuals=residuals,
        upstream_source_sha256=sha(source),instrumented_source_sha256=hashlib.sha256(text.encode()).hexdigest())
    Path(spec['output']).write_text(json.dumps(result,indent=2)+'\n')


def fixture(geometry,pair):
    """Continuous target with an x=0 partition, never an exposed cut face.

    All target boxes have one electrical identity. Touching neighbor labels
    are both held at zero during the target solve, resolving their capture
    columns without introducing a dielectric gap or exciting adjacent parts.
    """
    assert geometry in ('straight','branch','via')
    target=[('target',[-3.2,-.4,12.89,0,.4,14.89]),
            ('target',[0,-.4,12.89,3.2,.4,14.89])]
    if geometry=='branch':
        assert pair
        target += [('target',[-.4,.4,12.89,0,3.2,14.89]),
                   ('target',[0,.4,12.89,.4,3.2,14.89])]
    elif geometry=='via':
        assert pair
        # Exact native M10 height/thickness, via10 dielectric gap, and M11.
        # The whole vertical junction lies in the right half of x=0.
        target=[('target',[-3.2,-.4,10.09,0,.4,12.09]),
                ('target',[0,-.4,10.09,3.2,.4,12.09]),
                ('target',[1.2,-.4,12.09,2.,.4,12.89]),
                ('target',[1.2,-.4,12.89,2.,3.2,14.89])]
    other=[('near',[-3.2,-.4,15.69,0,.4,17.69])]
    if pair:
        other=[('near_left',[-1.6,-.4,15.69,0,.4,17.69]),
               ('near_right',[0,-.4,15.69,4.8,.4,17.69])]
    return target+other


def verify(root,out,cpus,run,pair=False,geometry='straight'):
    assert cpus>=16
    base=out.parents[2];solver=base/'block-v1-20261027-069/tasks/fsv-partial-build'
    receipt=json.loads((solver/'receipt.json').read_text());assert receipt['passed']is True
    toolfile=solver/'fsv-qualified.json';assert sha(toolfile)==receipt['outputs'][toolfile.name]
    tool=json.loads(toolfile.read_text());binary=Path(tool['partial_binary']);assert sha(binary)==tool['partial_binary_sha256']
    runtime=base/'block-v1-20261027-033/tasks/fv-install'
    bound=json.loads((runtime/'receipt.json').read_text());assert bound['passed']is True
    runtime_file=runtime/'fv-runtime.json';assert sha(runtime_file)==bound['outputs'][runtime_file.name]
    installed=json.loads(runtime_file.read_text());prefix=Path(installed['prefix'])
    for name,digest in installed['files'].items():assert sha(prefix/name)==digest,name
    # Two touching boxes remain one physical conductor; the shared x=0 face
    # inserts the cut into FV grid lines without creating an artificial gap.
    # In this straight fixture no exposed x-normal target face lies at the
    # cut, so adjacent free-cell x selects the exact conductor-face half.
    boxes=fixture(geometry,pair)
    scene=out/'scene.txt';scene.write_text('background 3.9\nmaster target\n'+
        ''.join('box '+name+' '+' '.join(map(str,box))+'\n'for name,box in boxes))
    source=prefix/'source/fv3d_golden.py'
    (out/'research-fv-partial.py').write_text(fv_source(source.read_text()))
    gridspecs=[]
    for name,h,far in [('coarse',.4,80),('medium',.2,80),('fine',.1,80),('far',.4,160)]:
        path=out/(name+'-input.json');path.write_text(json.dumps(dict(prefix=str(prefix),
            source_sha256=sha(source),boxes=boxes,h=h,far=far,output=str(out/(name+'.json'))),indent=2)+'\n')
        gridspecs.append(path)
    def solve_grid(path):
        run(['env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1','python3',
             str(Path(__file__)),'grid',str(path)],path.stem+'.log')
    offsets=[.5,.25,.125]
    walks=33554432 if pair else 2097152
    def solve_field(offset):
        name='offset-'+str(offset)
        run([str(binary),str((cpus-4)//3),str(offset),str(walks),str(scene),'0','0'],name+'.json')
    with concurrent.futures.ThreadPoolExecutor(max_workers=7)as pool:
        futures=[pool.submit(solve_grid,path)for path in gridspecs]
        futures += [pool.submit(solve_field,offset)for offset in offsets]
        for future in futures:future.result()
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    import numpy as np
    from fv2d_golden import extrapolate
    grids=[json.loads((out/(name+'.json')).read_text())for name in ['coarse','medium','fine','far']]
    names=grids[0]['names'];assert names==list(dict.fromkeys(n for n,b in boxes))and all(g['names']==names for g in grids)
    partial=np.array([g['partial_ff'][0]for g in grids[:3]])
    reference=np.array([[extrapolate(partial[:,i,b])for b in range(2)]for i in range(len(names)+1)])
    total=float(reference[0].sum());assert total>0
    grid_step=float(np.max(np.abs(reference-partial[-1]))/total)
    refinement=float(np.max(np.abs(partial[-1]-partial[-2]))/total)
    far=float(np.max(np.abs(np.array(grids[3]['partial_ff'][0])-partial[0]))/total)
    rows=[json.loads((out/('offset-'+str(offset)+'.json')).read_text())for offset in offsets]
    def array(row,key):
        entries={e['net']:e for e in row['entries']};assert set(entries)==set(names+['ground'])
        return np.array([entries[name][key]for name in names+['ground']])
    last=array(rows[-1],'partial');sigma=array(rows[-1],'partial_sigma')
    before=array(rows[-2],'partial');before_sigma=array(rows[-2],'partial_sigma')
    allowances=.03*total+5*sigma
    if pair:allowances[1:-1]=.05*np.abs(reference[1:-1])+.005*total+5*sigma[1:-1]
    comparison=bool((np.abs(last-reference)<=allowances).all())
    swapped=last[:,::-1]
    swap_accepted=bool((np.abs(swapped-reference)<=allowances[:,::-1]).all())
    gates=dict(fv_extrapolation=grid_step<=.02,fv_refinement=refinement<=.02,
        fv_far_boundary=far<=.005,
        offset_convergence=bool((np.abs(last-before)<=.01*total+5*np.hypot(sigma,before_sigma)).all()),
        partial_statistical_precision=bool((sigma<=(.001 if pair else .003)*total).all()),
        independent_local_charge_comparison=comparison,swapped_halves_rejected=not swap_accepted,
        exact_global_row_conservation=all(abs(sum(e['partial'])-e['cap'])<=1e-10*max(1,abs(e['cap']))for row in rows for e in row['entries']))
    pair_control=None
    if pair:
        original=last[1:-1];assert original.shape==(2,2)
        delta=.8*min(-original[0,0],-original[1,1]);assert delta>0
        changed=original+delta*np.array([[1,-1],[-1,1]])
        pair_control=dict(delta_ff=float(delta),changed_ff=changed.tolist(),original_ff=original.tolist(),
            all_couplings_negative=bool((changed<0).all()),
            marginals_preserved=bool(np.allclose(original.sum(axis=0),changed.sum(axis=0),rtol=0,atol=1e-12)
                and np.allclose(original.sum(axis=1),changed.sum(axis=1),rtol=0,atol=1e-12)),
            rejected=not bool((np.abs(changed-reference[1:-1])<=allowances[1:-1]).all()))
        gates['node_pair_rewire_rejected']=pair_control['rejected']
        gates['rewire_control_preserves_physical_signs_and_marginals']=pair_control['all_couplings_negative']and pair_control['marginals_preserved']
        gates['physical_partial_signs']=bool((last[0]>0).all()and(last[1:]<0).all())
    result=dict(schema='block-v1-partial-field-fv/1',passed=all(gates.values()),gates=gates,
        boxes=boxes,fixture=geometry,cut_axis='x',cut_um=0,scene_sha256=sha(scene),partial_binary_sha256=sha(binary),
        fsv_build_receipt_sha256=sha(solver/'receipt.json'),fv_runtime_sha256=sha(runtime_file),
        fv_instrumentation_sha256=sha(out/'research-fv-partial.py'),grids=grids,field_rows=rows,
        reference_partial_ff=reference.tolist(),node_pair_control=pair_control,node_pair_pilot=pair,full_total_ff=total,extrapolation_over_total=grid_step,
        refinement_over_total=refinement,far_change_over_total=far,
        declared_gates=dict(fv_extrapolation=.02,fv_refinement=.02,fv_far=.005,offset_change=.01,
            local_comparison=.03,external_pair_relative=.05 if pair else None,external_pair_over_total=.005 if pair else None,
            partial_sigma=.001 if pair else .003,sigma_factor=5,walks_per_offset=walks,offsets=offsets),
        qualified_full_block=False,qualified_node_pair_coupling=False,
        scope='Single x-plane local/pair charge fixture only; finite-offset Gaussian flux must pass FV/convergence. General graph partitions, distributed extraction and native/new-layer stitching remain unqualified')
    (out/'partial-field-fv.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Locked local-charge pilot gate failed; preserve all outputs'


if __name__=='__main__':
    assert sys.argv[1]=='grid';grid(sys.argv[2])
