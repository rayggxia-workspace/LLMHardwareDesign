"""Export the selected Gather plan and real two-sided candidate endpoints."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

from event_deploy import route_catalog
from handoff import verify_handoff
from image import pack_image
from publish_event_handoff import build
from resident_gather_contract import COMPLETION, GATHER, LINK_ABI, demand, local_image
from route_contract import digest, read_base, validate_base
from run import compile_event_ir
from adapter import bind_request

DEMAND = 'gather.U0.dma3'

def write_json(path, contents):
    path.write_text(json.dumps(contents, sort_keys=True, indent=2) + '\n')

def checksum(path):
    h = sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()

def stage_base(base, place, router):
    assembly = next(x for x in base['assemblies'] if x['id'] == 'U0')
    dx,dy = assembly['translation_dbu']
    table = list(csv.DictReader(router.read_text().splitlines(), delimiter='\t'))
    assert len(table)==650 and len({r['pin'] for r in table})==650 and len({r['net'] for r in table})==650
    # The placed netlist and ODB include the candidate logic. Existing U39
    # qualification does not apply to these bytes.
    files = {'U.Gather.odb':place/'staged-u.odb','U.Gather.netlist':place/'mapped.v',
             'U.Gather.endpoint_plan':router}
    base['views'].update({name:{'path':str(p.resolve()),'sha256':checksum(p)} for name,p in files.items()})
    assembly.update(state='staged',views={'odb':'U.Gather.odb','netlist':'U.Gather.netlist',
                                         'endpoint_plan':'U.Gather.endpoint_plan'})
    all_ports = {r[0]:list(map(int,r[1:])) for r in
                 (line.split('\t') for line in (place/'landings.tsv').read_text().splitlines())}
    for key, existing in base['endpoints'].items():
        if existing['assembly']!='U0':
            continue
        rect = [a+b for a,b in zip(all_ports[key.split('/',1)[1]],(dx,dy,dx,dy))]
        assert existing['m10_shapes'][0]['rect_dbu']==rect
    for row in table:
        name='U0/'+row['pin']
        cross = [int(row[k])+d for k,d in zip(('x0','y0','x1','y1'),(dx,dy,dx,dy))]
        base['endpoints'][name]={'assembly':'U0','odb_term':name,'native_net':'U0/'+row['net'],
            'role':{'INPUT':'sink','OUTPUT':'driver'}[row['role']],
            'm10_shapes':[{'layer':'M10','object':name+'/M10/0','rect_dbu':cross}]}
    base['base_id'] += '-u0-gather-staged'
    base['provenance']['gather_scope'] = 'candidate U0 M10 sites and physical DMA3 endpoints'
    signature={'schema':1,'abi':LINK_ABI,'opcode':GATHER}
    native=base['native_service_routes']
    assert all(t['group']!='U0' and t['id']!=3 for t in native['targets'])
    native['targets'].append({'group':'U0','id':3,'netlist_view':'U.Gather.netlist',
        'netlist_sha256':base['views']['U.Gather.netlist']['sha256'],
        'routes':[{**signature,'completions':[COMPLETION],'requires':[DEMAND]}]})
    validate_base(base)
    return signature

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base','place','audited_ports','compiled','reference_pm','rules','out'):
        parser.add_argument(name,type=Path)
    parser.add_argument('--prompt-address', type=lambda value:int(value,0))
    args=parser.parse_args()
    base=read_base(args.base)
    signature=stage_base(base,args.place,args.audited_ports)
    before=json.loads(args.compiled.read_bytes())
    ir, hardware=before['event_ir'],before['resolved_hardware']
    hardware['nets'][DEMAND] = {'cost':650,**demand('U0',3)}
    hardware['control_groups']['U0'] = hardware['control_groups'].pop('embedding')
    for service in hardware['event_model']['services'].values():
        providers = service['native_providers']
        providers['U0'] = providers.pop('embedding')
    hardware['native_provider_contracts']={'embedding-row':{'calls':[{**signature,'completion':COMPLETION}]}}
    result=compile_event_ir(ir,hardware,route_base=base,route_scope='interface',emit_outputs=True)
    assert result['status']=='planned', result
    program=result['outputs']['program']
    command,=program['locals']['U0']
    pm=local_image(command,topology=0x02500031,image_id=1,pack_image=pack_image,
                   prompt_address=args.prompt_address)
    assert pm==args.reference_pm.read_bytes()
    rules=json.loads(args.rules.read_bytes())
    resolved=result['resolved_hardware']
    bundle=build(ir,resolved,result['plan'],route_catalog(resolved),base,rules,bind_request,
                 source_outputs=result['outputs'])
    spec=bundle['algorithm2-input']
    assert len(spec['nets'])==650 and len(spec['pins'])==1300
    args.out.mkdir()
    for name,data in {**bundle,'compile':result,'base':base}.items():
        write_json(args.out/(name+'.json'),data)
    (args.out/'local.pm').write_bytes(pm)
    receipt=verify_handoff(spec,args.out)
    summary={'plan_sha256':digest(result['plan']),'base_sha256':digest(base),
             'local_pm_sha256':sha256(pm).hexdigest(),'bound_data_nets':len(spec['nets']),
             'admission':receipt,'scope':'Gather data interface only', 'product_qualified':False}
    write_json(args.out/'summary.json',summary)
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':
    main()

