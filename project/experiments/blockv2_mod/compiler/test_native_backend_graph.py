"""Validate fresh encoder coverage on full-model RMS/Add shapes, not a plan."""
import json,sys
from pathlib import Path
from collections import Counter
from native_backend import NativeBackend
from native_add_descriptor import add_provider
from native_rms_descriptor import rms_provider,q16_rms_profile
from image import pack_image

graph=json.loads(Path(sys.argv[1]).read_text())
profile=json.loads(Path('algo1/blockv2-mod.json').read_text())
backend=NativeBackend(profile)
out=Path(sys.argv[2]);out.mkdir()
counts=Counter()
for task in graph['tasks']:
    if task['kind'] not in ('RMSNorm','Add'):continue
    for group in ('U0','U1'):
        site=group+'.S'
        if task['kind']=='RMSNorm':
            operation=task['details']['operation']
            epsilon=graph['values'][operation['inputs'][2]]['constant']
            while isinstance(epsilon,list):epsilon=epsilon[0]
            parameters=q16_rms_profile(float(epsilon))
            provider=rms_provider(schema=3,provider_abi=7,operation=3,topology=25001,
                    site=site,x_word=0,output_word=512,**parameters)
            reads=[{'site':site,'address':0,'bytes':8192},
                   {'site':site,'address':8192,'bytes':8192}]
            writes=[{'site':site,'address':8192,'bytes':8192}]
        else:
            width=max(s[-1] for s in task['input_shapes'].values() if s)
            if width%4 or width>2048:raise ValueError('shape needs additional ADD tiling')
            size=width*4
            provider=add_provider(schema=3,provider_abi=7,operation=2,topology=25001,site=site)
            reads=[{'site':site,'address':0,'bytes':size},
                   {'site':site,'address':8192,'bytes':size}]
            writes=[{'site':site,'address':0,'bytes':size}]
        command={'op':'EXEC','read':reads,'write':writes,'required_completion':'service_done'}
        encoded=backend.encode_deployment_call(group,provider,command)
        assert encoded.target==backend.targets[group]['id']
        page=encoded.descriptor
        if not page:raise ValueError('empty native descriptor')
        counts[task['kind']+'/'+group]+=1
        # One representative of each actual target/type, not hundreds of redundant payloads.
        name=task['kind']+'-'+group+'.descriptor'
        if not (out/name).exists():(out/name).write_bytes(page)
# Rejection must occur before a candidate can enter scheduling.
broken=dict(command,required_completion='uncommitted')
try:backend.encode('U1',provider,broken)
except ValueError:pass
else:raise AssertionError('completion mismatch accepted')
report={'passed':True,'freshly_encoded_candidates':dict(counts),
        'scope':'all full-model RMS/Add shapes encoded to raw descriptors for fixed U0/U1 kernels; scratch test allocation, not a selected whole-graph plan',
        'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
