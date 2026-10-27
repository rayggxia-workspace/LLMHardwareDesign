"""Independent Dirichlet boundary-patch FV reference for joint node charge.

Reuse the pinned Laplace matrix and uniform-net reference solves. Only the
right-hand side changes for auxiliary boundary basis functions: exciting one
surface patch is not a claim that the physical wire is several electrodes.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import types


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fv_source(text):
    from graph_field_verify import fv_source as origin_source
    text = origin_source(text)
    before = '    return names, matrix, n, partial'
    after = '''    # Actual conductor faces, with stable nearest-node tie breaking.
    face_bins = {}
    for net,name in enumerate(names):
        points = np.array(CAPTURE_REFERENCE_NODES[name],dtype=float)
        assert points.ndim == 2 and points.shape[1] == 3 and len(points) >= 2
        p = wire_pos[wire_net == net]
        delta = p[:,None,:] - points[None,:,:]
        face_bins[net] = np.argmin(np.sum(delta*delta,axis=2),axis=1)
    joint = {}
    for drive,name in enumerate(names):
        on_net = wire_net == drive
        on_indices = np.flatnonzero(on_net)
        count = len(CAPTURE_REFERENCE_NODES[name])
        for receiver in range(len(names)):
            if receiver != drive:
                joint[names[receiver]+'|'+name] = np.zeros((len(CAPTURE_REFERENCE_NODES[names[receiver]]),count))
        for j in range(count):
            on = on_indices[face_bins[drive] == j]
            assert len(on) > 0, 'FV capture patch has no exposed boundary faces'
            rhs = np.zeros(n)
            np.add.at(rhs,wire_cell[on],wire_g[on])
            phi = ml.solve(rhs,tol=1e-11,accel='cg',maxiter=500)
            for receiver in range(len(names)):
                if receiver == drive:
                    continue
                target_faces = wire_net == receiver
                charge = -EPS0 * wire_g[target_faces] * phi[wire_cell[target_faces]]
                key = names[receiver]+'|'+name
                joint[key][:,j] = np.bincount(face_bins[receiver],weights=charge,minlength=joint[key].shape[0])
    for receiver in range(len(names)):
        for drive in range(len(names)):
            if receiver == drive:
                continue
            key = names[receiver]+'|'+names[drive]
            assert np.isclose(joint[key].sum(),matrix[drive,receiver],rtol=1e-8,atol=1e-10)
            reverse = names[drive]+'|'+names[receiver]
            assert np.allclose(joint[key],joint[reverse].T,rtol=1e-8,atol=1e-10)
            if receiver == 0:
                assert np.allclose(joint[key].sum(axis=1),partial[drive],rtol=1e-8,atol=1e-10)
    return names, matrix, n, partial, joint'''
    assert text.count(before) == 1
    return text.replace(before, after)


def fixture(geometry):
    from partial_field_verify import fixture as origin_fixture
    from graph_field_verify import fixture_nodes
    target = [(name,box) for name,box in origin_fixture(geometry,True) if name=='target']
    boxes = target+[('near',[-1.6,-.4,15.69,4.8,.4,17.69])]
    nodes,_ = fixture_nodes(geometry)
    return boxes,dict(target=nodes,near=[('left',[-.8,0,16.69]),('right',[3.2,0,16.69])])


def grid(path):
    spec=json.loads(Path(path).read_text());prefix=Path(spec['prefix'])
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    import numpy as np
    import pyamg
    source=prefix/'source/fv3d_golden.py';assert sha(source)==spec['source_sha256']
    text=fv_source(source.read_text());module=types.ModuleType('joint_fv_reference')
    module.__dict__.update(__file__=str(source),GRAPH_NODES=spec['nodes']['target'],
                           CAPTURE_REFERENCE_NODES=spec['nodes'])
    exec(compile(text,'joint-fv-reference','exec'),module.__dict__)
    original=pyamg.smoothed_aggregation_solver;residuals=[]
    def checked(matrix,**kwargs):
        solver=original(matrix,**kwargs)
        class Receiver:
            def solve(self,rhs,**options):
                phi=solver.solve(rhs,**options)
                residual=float(np.linalg.norm(matrix@phi-rhs)/np.linalg.norm(rhs))
                residuals.append(residual);assert residual<1e-8
                return phi
        return Receiver()
    pyamg.smoothed_aggregation_solver=checked
    names,matrix,cells,partial,joint=module.solve(3.9,[],spec['boxes'],[],spec['h'],spec['far'])
    result=dict(names=names,matrix_ff=matrix.tolist(),partial_ff=partial.tolist(),
                joint_ff={key:value.tolist()for key,value in joint.items()},free_cells=cells,
                linear_relative_residuals=residuals,h_um=spec['h'],far_um=spec['far'],
                upstream_source_sha256=sha(source),instrumented_source_sha256=hashlib.sha256(text.encode()).hexdigest())
    Path(spec['output']).write_text(json.dumps(result,indent=2)+'\n')


def assess(grids,rows,nodes):
    """Locked scientific gates. Totals/marginals cannot replace local agreement."""
    import numpy as np
    from fv2d_golden import extrapolate
    names=list(nodes);assert names==['target','near']
    assert all(g['names']==names for g in grids)
    references={};results={};gates={}
    for origin,other in [('target','near'),('near','target')]:
        key=origin+'|'+other;shape=(len(nodes[origin]),len(nodes[other]))
        samples=np.array([g['joint_ff'][key]for g in grids[:3]])
        assert samples.shape==(3,*shape) and np.isfinite(samples).all()
        reference=np.array([[extrapolate(samples[:,i,j])for j in range(shape[1])]for i in range(shape[0])])
        index=names.index(origin)
        self_samples=np.array([g['matrix_ff'][index][index]for g in grids[:3]])
        total=float(extrapolate(self_samples));assert total>0 and np.isfinite(reference).all()
        references[key]=reference
        def joint(row,field):
            assert row['master']==origin and row['nodes']==[name for name,p in nodes[origin]]
            entries=[e for e in row['captures']if e['net']==other]
            assert [e['node']for e in entries]==[name for name,p in nodes[other]]
            array=np.array([e[field]for e in entries]).T
            assert array.shape==shape and np.isfinite(array).all()
            return array
        series=rows[origin];last=joint(series[-1],'partial');sigma=joint(series[-1],'partial_sigma')
        before=joint(series[-2],'partial');prior_sigma=joint(series[-2],'partial_sigma')
        assert (sigma>=0).all() and (prior_sigma>=0).all()
        allowance=.05*np.abs(reference)+.005*total+5*sigma
        raw=next(e for e in series[-1]['entries']if e['net']==origin)
        local=dict(fv_extrapolation=bool((np.abs(reference-samples[-1])<=.02*total).all()and abs(total-self_samples[-1])<=.02*total),
                   fv_refinement=bool((np.abs(samples[-1]-samples[-2])<=.02*total).all()and abs(self_samples[-1]-self_samples[-2])<=.02*total),
                   fv_far_boundary=bool((np.abs(np.array(grids[3]['joint_ff'][key])-samples[0])<=.005*total).all()
                       and abs(grids[3]['matrix_ff'][index][index]-self_samples[0])<=.005*total),
                   offset_convergence=bool((np.abs(last-before)<=.01*total+5*np.hypot(sigma,prior_sigma)).all()),
                   statistical_precision=bool((sigma<=.001*total).all()),
                   physical_negative_couplings=bool((last<0).all()and(reference<0).all()),
                   independent_local_coupling=bool((np.abs(last-reference)<=allowance).all()),
                   uniform_master_capacitance=abs(raw['cap']-total)<=.03*total+5*raw['sigma'])
        # Preserve both marginals and every physical sign while corrupting
        # a labelled 2x2 submatrix. A totals-only receiver must fail this.
        candidates=[(i,k,j,l)for i in range(shape[0])for k in range(shape[0])if i!=k
                    for j in range(shape[1])for l in range(shape[1])if j!=l]
        i,k,j,l=max(candidates,key=lambda q:min(-last[q[0],q[2]],-last[q[1],q[3]]))
        delta=.8*min(-last[i,j],-last[k,l]);assert delta>0
        changed=last.copy();changed[i,j]+=delta;changed[k,l]+=delta;changed[i,l]-=delta;changed[k,j]-=delta
        control=dict(delta_ff=float(delta),changed_ff=changed.tolist(),
                     physical_signs=bool((changed<0).all()),
                     marginals_preserved=bool(np.allclose(last.sum(axis=0),changed.sum(axis=0),rtol=0,atol=1e-12)
                         and np.allclose(last.sum(axis=1),changed.sum(axis=1),rtol=0,atol=1e-12)),
                     rejected=not bool((np.abs(changed-reference)<=allowance).all()))
        local['rewire_rejected']=control['rejected']
        local['rewire_preserves_signs_and_marginals']=control['physical_signs']and control['marginals_preserved']
        gates[origin]=local
        results[origin]=dict(reference_joint_ff=reference.tolist(),measured_joint_ff=last.tolist(),
            sigma_ff=sigma.tolist(),self_total_ff=total,rewire_control=control)
    a=np.array(results['target']['measured_joint_ff']);b=np.array(results['near']['measured_joint_ff']).T
    sigma=np.hypot(np.array(results['target']['sigma_ff']),np.array(results['near']['sigma_ff']).T)
    total=max(r['self_total_ff']for r in results.values())
    reciprocal=bool((np.abs(a-b)<=.05*np.abs(references['target|near'])+.005*total+5*sigma).all())
    passed=reciprocal and all(all(row.values())for row in gates.values())
    return dict(passed=passed,directional_gates=gates,reciprocal_joint_coupling=reciprocal,directions=results,
                declared_gates=dict(fv_extrapolation=.02,fv_refinement=.02,fv_far=.005,offset_change=.01,
                    sigma_over_total=.001,external_relative=.05,external_over_total=.005,sigma_factor=5,
                    self_total_relative=.03))


def verify(root,out,cpus,run,geometry):
    assert geometry in ('branch','via') and cpus>=16
    base=out.parents[2];build=base/'block-v1-20261027-099/tasks/fsv-capture-build'
    bound=json.loads((build/'receipt.json').read_text());assert bound['passed']is True
    tool_path=build/'fsv-qualified.json';assert sha(tool_path)==bound['outputs'][tool_path.name]
    tool=json.loads(tool_path.read_text());binary=Path(tool['capture_binary'])
    assert sha(binary)==tool['capture_binary_sha256']
    runtime=base/'block-v1-20261027-033/tasks/fv-install'
    receipt=json.loads((runtime/'receipt.json').read_text());assert receipt['passed']is True
    path=runtime/'fv-runtime.json';assert sha(path)==receipt['outputs'][path.name]
    installed=json.loads(path.read_text());prefix=Path(installed['prefix'])
    for name,digest in installed['files'].items():assert sha(prefix/name)==digest,name
    boxes,nodes=fixture(geometry);source=prefix/'source/fv3d_golden.py'
    (out/'research-joint-fv.py').write_text(fv_source(source.read_text()))
    gridspecs=[]
    for name,h,far in [('coarse',.4,80),('medium',.2,80),('fine',.1,80),('far',.4,160)]:
        path=out/(name+'-input.json')
        path.write_text(json.dumps(dict(prefix=str(prefix),source_sha256=sha(source),boxes=boxes,
            nodes={net:[p for name,p in group]for net,group in nodes.items()},h=h,far=far,
            output=str(out/(name+'.json'))),indent=2)+'\n');gridspecs.append(path)
    for origin in nodes:
        (out/(origin+'-scene.txt')).write_text('background 3.9\nmaster '+origin+'\n'+
            ''.join('box '+name+' '+' '.join(map(str,box))+'\n'for name,box in boxes))
        (out/(origin+'-nodes.txt')).write_text(''.join(name+' '+' '.join(map(str,p))+'\n'for name,p in nodes[origin]))
        (out/(origin+'-captures.txt')).write_text(''.join(net+' '+name+' '+' '.join(map(str,p))+'\n'
            for net,group in nodes.items()if net!=origin for name,p in group))
    def solve_grid(path):
        run(['env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1','python3',
             str(Path(__file__)),'grid',str(path)],path.stem+'.log')
    offsets=[.5,.25,.125];walks=33554432
    def solve_field(pair):
        origin,offset=pair;name=origin+'-offset-'+str(offset)
        run([str(binary),str((cpus-4)//6),str(offset),str(walks),str(out/(origin+'-scene.txt')),
             str(out/(origin+'-nodes.txt')),str(out/(origin+'-captures.txt'))],name+'.json')
    with concurrent.futures.ThreadPoolExecutor(max_workers=10)as pool:
        futures=[pool.submit(solve_grid,path)for path in gridspecs]
        futures += [pool.submit(solve_field,(origin,offset))for origin in nodes for offset in offsets]
        for future in futures:future.result()
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    grids=[json.loads((out/(name+'.json')).read_text())for name in ['coarse','medium','fine','far']]
    rows={origin:[json.loads((out/(origin+'-offset-'+str(offset)+'.json')).read_text())for offset in offsets]for origin in nodes}
    result=assess(grids,rows,nodes)
    result.update(schema='block-v1-capture-field-fv/1',fixture=geometry,boxes=boxes,nodes=nodes,
        build_receipt_sha256=sha(build/'receipt.json'),capture_binary_sha256=sha(binary),fv_runtime_sha256=sha(runtime/'fv-runtime.json'),
        fv_instrumentation_sha256=sha(out/'research-joint-fv.py'),grids=grids,field_rows=rows,
        offsets=offsets,walks_per_offset=walks,qualified_full_block=False,
        scope='Two-conductor branch/via joint-node fixture only; arbitrary routed multi-net distributed RC, window ownership and native/new-layer stitching remain unqualified')
    (out/'capture-field-fv.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Locked joint-node scientific gate failed; preserve every output'


if __name__=='__main__':
    assert sys.argv[1]=='grid'
    grid(sys.argv[2])
