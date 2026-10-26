"""Independent finite-volume qualification of direct new-layer field solving.

Unmodified pinned FV scripts and hash-checked PyPI wheels live outside Git.
Each child has one BLAS thread; four FV children + four FSV threads fit 8 CPUs.
These are new short geometries, not the failed fitted-model holdouts.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time
import zipfile
from rc_pipeline import configuration

INSTALL_RUN='block-v1-20261027-033'
ARCHIVE_SHA='f4a11acad6f01b59170646c3f6f7fbe075cd076f10a3b18da0e62bf67097ab33'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def install(root,out,run):
    archive=root.parent/'fv-inputs.tar';assert sha(archive)==ARCHIVE_SHA
    prefix=Path('/public/home/yuzelu/opt/eda')/('llhd-fv-i121-'+root.parent.name)
    prefix.mkdir(exist_ok=False)
    with tarfile.open(archive)as tar:
        for entry in tar.getmembers():
            assert entry.isfile()and not Path(entry.name).is_absolute()and'..'not in Path(entry.name).parts
        tar.extractall(prefix)
    manifest=json.loads((prefix/'manifest.json').read_text())
    assert manifest['source_commit']=='6ea4ca224f3589dd91809933f50f39af66053634'
    for source in manifest['sources']:assert sha(prefix/'source'/source['filename'])==source['sha256']
    packages=prefix/'packages';packages.mkdir()
    for wheel in manifest['wheels']:
        path=prefix/'wheels'/wheel['filename'];assert sha(path)==wheel['sha256']
        with zipfile.ZipFile(path)as zipped:
            for name in zipped.namelist():
                assert not Path(name).is_absolute()and'..'not in Path(name).parts and not name.endswith('.pth')
            zipped.extractall(packages)
    env=os.environ.copy();env['PYTHONPATH']=str(packages)
    subprocess.run(['python3','-c','import numpy,scipy,pyamg; print(numpy.__version__,scipy.__version__,pyamg.__version__)'],
                   env=env,check=True)
    record=dict(schema='block-v1-fv-runtime/1',prefix=str(prefix),archive_sha256=sha(archive),manifest=manifest,
                files={str(p.relative_to(prefix)):sha(p)for p in prefix.rglob('*')if p.is_file()and'__pycache__'not in p.parts},
                qualification='Dependencies imported only; scientific geometry qualification remains separate')
    (out/'fv-runtime.json').write_text(json.dumps(record,indent=2)+'\n')


def grid(spec_path):
    spec=json.loads(Path(spec_path).read_text());prefix=Path(spec['prefix'])
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    import numpy as np
    import pyamg
    import fv3d_golden as fv
    original=pyamg.smoothed_aggregation_solver;residuals=[]
    def checked(matrix,**kwargs):
        solver=original(matrix,**kwargs)
        class Receiver:
            def solve(self,rhs,**options):
                answer=solver.solve(rhs,**options)
                relative=float(np.linalg.norm(matrix@answer-rhs)/np.linalg.norm(rhs))
                residuals.append(relative);assert relative<1e-8,relative
                return answer
        return Receiver()
    pyamg.smoothed_aggregation_solver=checked
    started=time.time()
    names,matrix,cells=fv.solve(3.9,[],spec['boxes'],[],spec['h'],spec['far'])
    output=dict(names=names,matrix_ff=matrix.tolist(),free_cells=cells,h_um=spec['h'],far_um=spec['far'],
                linear_relative_residuals=residuals,seconds=time.time()-started)
    Path(spec['output']).write_text(json.dumps(output,indent=2)+'\n')


def verify(root,out,cpus,run,index):
    assert cpus>=8 and 0<=index<6
    base=out.parents[2];runtime=base/INSTALL_RUN/'tasks/fv-install'
    receipt=json.loads((runtime/'receipt.json').read_text());assert receipt['passed']is True
    path=runtime/'fv-runtime.json';assert sha(path)==receipt['outputs'][path.name]
    installed=json.loads(path.read_text());prefix=Path(installed['prefix'])
    for name,digest in installed['files'].items():assert sha(prefix/name)==digest,name
    config=configuration(root)
    patterns=base/config['patterns_run']/'tasks/rcx-complete-patterns'
    before=json.loads((patterns/'receipt.json').read_text());assert before['passed']is True
    tech=patterns/'overlay/research12.tech.lef';assert sha(tech)==before['outputs']['overlay/research12.tech.lef']
    # Native M10 and research M11/M12 heights were already independently
    # read back from this exact overlay; use them unchanged in both solvers.
    text=tech.read_text();layers={}
    for number in [10,11,12]:
        body=re.search(r'(?m)^LAYER metal%d\s*\n(.*?)^END metal%d\s*$'%(number,number),text,re.S|re.M).group(1)
        layers[number]=tuple(float(re.search(r'\b'+name+r'\s+([0-9.]+)\s*;',body).group(1))for name in ['HEIGHT','THICKNESS'])
    assert layers=={10:(10.09,2.),11:(12.89,2.),12:(15.69,2.)},'Regenerate cases for a changed physical stack'
    boxes=[]
    if index<4:
        lower=10+index//2;upper=lower+1;cross=index%2
        for name,metal,vertical in [('a',lower,False),('b',upper,bool(cross))]:
            z,t=layers[metal]
            xy=[-.4,-3.2,.4,3.2]if vertical else[-3.2,-.4,3.2,.4]
            boxes.append((name,[xy[0],xy[1],z,xy[2],xy[3],z+t]))
        name=('cross'if cross else'parallel')+'-%d-%d'%(lower,upper)
    elif index==4:
        name='same-layer-12'
        for net,y in [('a',-1.84),('b',0),('c',1.84)]:boxes.append((net,[-3.2,y-.4,15.69,3.2,y+.4,17.69]))
    else:
        name='via-chain-10-11-12'
        for net,dx in [('a',0),('b',4.)]:
            for x0,y0,z0,x1,y1,z1 in [[-.4,-.4,10.09,.4,.4,12.09],[-.3,-.3,12.09,.3,.3,12.89],
                    [-.4,-.4,12.89,2.,.4,14.89],[1.3,-.3,14.89,1.9,.3,15.69],[1.2,-.4,15.69,2.,2.,17.69]]:
                boxes.append((net,[x0+dx,y0,z0,x1+dx,y1,z1]))
    scene=out/'scene.txt';scene.write_text('background 3.9\n'+''.join('box '+net+' '+' '.join(map(str,box))+'\n'for net,box in boxes))
    qualified=base/config['solver_run']/'tasks/fsv-build/fsv-qualified.json'
    tool=json.loads(qualified.read_text());binary=Path(tool['binary']);assert sha(binary)==tool['binary_sha256']
    specifications=[]
    for label,h,far in [('coarse',.4,80.),('medium',.2,80.),('fine',.1,80.),('far',.4,160.)]:
        p=out/(label+'-input.json')
        p.write_text(json.dumps(dict(prefix=str(prefix),boxes=boxes,h=h,far=far,output=str(out/(label+'.json'))),indent=2)+'\n')
        specifications.append(p)
    def solve(p):run(['env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1',
                     'python3',str(Path(__file__)),'grid',str(p)],p.stem+'.log')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:
        jobs=[pool.submit(solve,p)for p in specifications]
        jobs.append(pool.submit(run,[str(binary),'scene3d',str(cpus-4),str(scene)],'direct-field.jsonl'))
        for job in jobs:job.result()
    sys.path[:0]=[str(prefix/'packages'),str(prefix/'source')]
    import numpy as np
    from fv2d_golden import extrapolate
    grids=[json.loads((out/(label+'.json')).read_text())for label in ['coarse','medium','fine','far']]
    names=grids[0]['names'];assert all(g['names']==names for g in grids)
    matrices=np.array([g['matrix_ff']for g in grids[:3]])
    extrapolated=np.array([[extrapolate(matrices[:,i,j])for j in range(len(names)+1)]for i in range(len(names))])
    totals=np.diag(extrapolated[:,:-1])[:,None];assert (totals>0).all()
    step=float(np.max(np.abs(extrapolated-matrices[-1])/totals))
    refinement=float(np.max(np.abs(matrices[-1]-matrices[-2])/totals))
    far=float(np.max(np.abs(np.array(grids[3]['matrix_ff'])-matrices[0])/totals))
    raw=[json.loads(line)for line in(out/'direct-field.jsonl').read_text().splitlines()]
    assert raw[-1]=={'status':'PASS','mode':'scene3d'}and len(raw[:-1])==len(names)
    comparisons=[]
    for row in raw[:-1]:
        i=names.index(row['master']);total=extrapolated[i,i]
        for entry in row['entries']:
            j=len(names)if entry['net']=='ground'else names.index(entry['net'])
            expected=extrapolated[i,j];error=abs(entry['cap']-expected)
            allowance=(.03*total if j in(i,len(names))else .05*abs(expected)+.005*total)+5*entry['sigma']
            comparisons.append(dict(master=row['master'],net=entry['net'],finite_volume_ff=float(expected),
                field_ff=entry['cap'],sigma_ff=entry['sigma'],allowance_ff=float(allowance),passed=bool(error<=allowance)))
    gates=dict(grid_extrapolation=step<=.02,grid_refinement=refinement<=.02,far_boundary=far<=.005,
               independent_matrix_comparison=all(v['passed']for v in comparisons))
    record=dict(schema='block-v1-direct-field-fv/1',name=name,index=index,boxes=boxes,scene_sha256=sha(scene),
                binary_sha256=sha(binary),runtime_sha256=sha(path),grids=grids,extrapolated_ff=extrapolated.tolist(),
                extrapolation_over_total=step,refinement_over_total=refinement,far_change_over_total=far,
                comparisons=comparisons,gates=gates,passed=all(gates.values()),
                declared_gates=dict(extrapolation=.02,refinement=.02,far_boundary=.005,
                    total_or_ground_over_total=.03,coupling_relative=.05,coupling_over_total=.005,sigma=5),
                scope='Independent FV vs direct full-geometry field solver; not a pass for the failed fitted RCX model or full-block distributed RC')
    (out/'fv-case.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Independent finite-volume comparison failed'


if __name__=='__main__':
    assert sys.argv[1]=='grid';grid(sys.argv[2])
