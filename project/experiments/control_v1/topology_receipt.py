"""Independently replay the frozen graph generator; never invent its receipt."""
import hashlib,json,os,subprocess,sys
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def structural(value):
    """Ignore only source-location attributes, preserving every logic field."""
    if isinstance(value,list):return [structural(v)for v in value]
    if not isinstance(value,dict):return value
    return {k:({kk:structural(vv)for kk,vv in v.items()if kk!='src'}
               if k=='attributes' and isinstance(v,dict)else structural(v))
            for k,v in value.items()}


def audit(a):
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
    old=a.audit_existing.resolve();spec_path=a.audit_spec.resolve();out=a.out.resolve()
    assert old==base/'s-escape-composition-03/1350/topology'
    assert spec_path==base/'dynamic-02/node26/pending/00-h-s1350-fast137-topology.json'
    assert out==base/'s-escape-composition-03/1350/topology-audit'
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,operation='topology-replay-audit',job=os.environ['SLURM_JOB_ID'],
        inputs={},whole_system_qualified=False,native_leaf_qualified=False,
        scope='Actual independent replay of the unchanged frozen source137 graph generator; no physical or system qualification inferred.')
    def bind(path,digest=None):
        path=Path(path);value=sha(path)
        if digest is not None:assert value==digest,str(path)
        receipt['inputs'][str(path)]=value
        return value
    try:
        bind(Path(__file__));bind(Path(__file__).with_name('topology.py'))
        bind(spec_path);spec=json.loads(spec_path.read_text())
        source=Path(spec['source_root']);script=source/'project/experiments/control_v1/topology.py'
        assert source==base/'source-137'and spec['script']=='topology.py'
        manifest=source/'source-manifest.json';bind(manifest);frozen=json.loads(manifest.read_text())
        for name in ['project/experiments/control_v1/topology.py','project/experiments/control_v1/boundary_links.py','project/rtl/control_v1/control_system.sv']:
            bind(source/name,frozen['files'][name])
        command=spec_path.parent.parent/'commands'/spec_path.name
        result=spec_path.parent.parent/'results'/spec_path.name
        bind(command);bind(result);cmd=json.loads(command.read_text());done=json.loads(result.read_text())
        assert done['returncode']==0 and done['spec_sha256']==cmd['spec_sha256']==sha(spec_path)
        assert cmd['source_manifest_sha256']==sha(manifest)and cmd['script_sha256']==sha(script)
        args=spec['args'];assert cmd['command'][-len(args):]==args and str(script)in cmd['command']
        assert args[args.index('--out')+1]==str(old)
        assert Path(args[args.index('--manifest')+1]).resolve()==a.manifest.resolve()
        selected=a.manifest.parent/'receipt.json';bind(selected);selection=json.loads(selected.read_text())
        bind(a.manifest,selection['outputs']['physical.json']);assert selection['passed']
        graph=old/'boundary-graph.json';bind(graph);g=json.loads(graph.read_text())
        assert g['passed']and g['no_unassigned_active_logic']and g['source_sha256']==sha(script)
        assert g['S_external_link_instances']==0 and g['S_internal_drive']['all_four_gates_fresh']
        for name,digest in g['inputs'].items():bind(Path(name),digest)
        replay=out/'replay';replay_args=list(args);replay_args[args.index('--out')+1]=str(replay)
        with(out/'replay.log').open('w')as log:
            run=subprocess.run([sys.executable,str(script),*replay_args],stdout=log,stderr=subprocess.STDOUT)
        assert run.returncode==0
        checks={}
        for name in ['boundary-graph.json','combined.v','leaves.v']:
            bind(old/name);checks[name]=sha(old/name)==sha(replay/name);assert checks[name],name
        bind(old/'topology.json')
        model=structural(json.loads((old/'topology.json').read_text()))
        checks['all_logic_fields']=model==structural(json.loads((replay/'topology.json').read_text()))
        assert checks['all_logic_fields']
        report=dict(passed=True,checks=checks,original_graph=str(graph),original_graph_sha256=sha(graph),
            original_topology=str(old/'topology.json'),original_topology_sha256=sha(old/'topology.json'),
            physical_manifest=str(a.manifest),physical_manifest_sha256=sha(a.manifest),
            original_execution_result=str(result),original_execution_result_sha256=sha(result),
            original_frozen_source=str(source),original_frozen_commit=frozen['commit'],
            replay_command=[sys.executable,str(script),*replay_args],
            instance_count=len(g['instances']),native_types=len(json.loads(a.manifest.read_text())['leaves']),
            ignored_fields=['Yosys attributes.src only; replay stub file paths differ'],
            whole_system_qualified=False,scope=receipt['scope'])
        (out/'topology-audit.json').write_text(json.dumps(report,indent=2)+'\n')
        receipt.update(passed=True,all_logic_fields_replayed=True,original_graph_sha256=sha(graph))
    finally:
        receipt['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

