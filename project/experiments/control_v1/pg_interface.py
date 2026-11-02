"""Read fixed M10 supply interfaces from the actual completed native wrappers."""
import hashlib,json,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify_source(row,folder,wrapper,inputs):
    """Bind either original input or its fully qualified fixed-PG delivery."""
    original=row['final_files']['6_final.odb']
    assert sha(original['path'])==original['sha256'];inputs[original['path']]=original['sha256']
    selected=row.get('fixed_pg_delivery')
    if selected:
        path=Path(selected['path']);receipt=Path(selected['receipt'])
        for p,key in [(path,'sha256'),(receipt,'receipt_sha256')]:
            assert sha(p)==selected[key];inputs[str(p)]=selected[key]
        proof=json.loads(receipt.read_text());delivery=json.loads(path.read_text())
        assert proof['passed']and proof['native_leaf_qualified']and proof['outputs'][path.name]==sha(path)
        assert delivery['passed']and delivery['native_leaf_accepted']and delivery['final_files']==row['final_files']
        assert Path(delivery['fixed_pg_receipt']).resolve()==(folder/'receipt.json').resolve()
        assert delivery['fixed_pg_receipt_sha256']==sha(folder/'receipt.json')
        assert original['sha256']==wrapper['outputs']['wrapper.odb']==sha(folder/'wrapper.odb')
        assert row['final_files']['6_final.gds']['sha256']==wrapper['outputs']['wrapper.gds']==sha(folder/'wrapper.gds')
        old=Path(delivery['original_delivery']);assert sha(old)==delivery['original_delivery_sha256'];inputs[str(old)]=sha(old)
        prior=json.loads(old.read_text());assert prior['passed']and prior['native_leaf_accepted']
        original=prior['final_files']['6_final.odb']
        assert sha(original['path'])==original['sha256'];inputs[original['path']]=original['sha256']
    assert wrapper['inputs'][original['path']]==original['sha256']


def inventory(manifest,folder,out,candidate=False):
    inputs={str(Path(__file__)):sha(Path(__file__))};wrappers={}
    (out/'pg-access.tsv').write_text('')
    for top,row in manifest['leaves'].items():
        root=folder/top;receipt=root/'receipt.json'
        try:w=json.loads(receipt.read_text())
        except (OSError,ValueError):w={}
        completed=w.get('passed') is True
        original=row['final_files']['6_final.odb'];assert sha(original['path'])==original['sha256']
        inputs[original['path']]=original['sha256']
        if completed:
            inputs[str(receipt)]=sha(receipt)
            assert w['native_drc_zero'] and w['full_deck']['total_items']==0
            verify_source(row,root,w,inputs)
        else:
            assert candidate,'Completed native wrapper gates are required'
            request=json.loads((root/'gds-input.json').read_text())
            assert request['native_sha256']==row['final_files']['6_final.gds']['sha256']
            assert not (root/'native-whole-drc.rpt').read_text().strip()
            assert sha(root/'original.v')==sha(root/'wrapper.v')
            for name in ('gds-input.json','fixed-access.tcl','native-whole-drc.rpt','original.v','wrapper.v'):
                inputs[str(root/name)]=sha(root/name)
        for name in ('wrapper.odb','wrapper.def'):
            p=root/name;digest=sha(p)
            if completed:assert digest==w['outputs'][name]
            inputs[str(p)]=digest
        wrappers[top]=dict(folder=str(root),receipt_sha256=sha(receipt) if completed else None,
                           odb=str(root/'wrapper.odb'),odb_sha256=sha(root/'wrapper.odb'),gds=str(root/'wrapper.gds'),
                           gds_sha256=w.get('outputs',{}).get('wrapper.gds'),native_leaf_qualified=False,
                           complete_wrapper_drc=completed)
        script='set_thread_count 16\nset f [open {'+str(out/'pg-access.tsv')+'} a]\n'
        script+='read_db {'+str(root/'wrapper.odb')+'}\nset b [ord::get_db_block]\n'
        script+='foreach supply {VDD VSS} {set n [$b findNet $supply];set port [$b findBTerm $supply];if {$port eq "NULL" || [$port getNet] ne $n} {error "Actual supply port mismatch"};set count 0\n'
        script+='foreach pin [$port getBPins] {foreach box [$pin getBoxes] {if {[[$box getTechLayer] getName] ne "metal10"} {continue};incr count;puts $f "'+top+'\\t$supply\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"}}\nif {$count!=1} {error "Expected exactly one actual M10 supply interface"}}\n'
        script+='close $f\n';path=out/('pg-access-'+top+'.tcl');path.write_text(script)
        with (out/('pg-access-'+top+'.log')).open('w') as log:q=subprocess.run(['openroad','-no_init','-exit',path],stdout=log,stderr=subprocess.STDOUT,cwd=out)
        assert q.returncode==0,('Actual PG interface readback failed',top)
    for path,digest in inputs.items():assert sha(path)==digest,'PG input changed during actual readback'
    contacts={top:{} for top in manifest['leaves']}
    for line in (out/'pg-access.tsv').read_text().splitlines():
        top,supply,*values=line.split('\t');box=list(map(int,values));assert supply not in contacts[top]
        x=(box[0]+box[2])/4000;y=(box[1]+box[3])/4000
        assert box[2]-box[0]==box[3]-box[1]==4000
        assert abs((x-.095)/4-round((x-.095)/4))<1e-8 and abs((y-.07)/4-round((y-.07)/4))<1e-8
        contacts[top][supply]=dict(pin=supply,xy_um=[x,y],box_dbu=box,direction='input')
    assert all(set(v)=={'VDD','VSS'} for v in contacts.values())
    result=dict(passed=True,contacts=contacts,wrappers=wrappers,inputs=inputs,candidate_access=candidate,
                scope='Actual M10 interface readback only. In candidate mode full native GDS gates may still run; final geometry must require completed same-ODB wrapper gates. Fresh RC/STA and whole upper supply continuity remain separate.')
    (out/'pg-access.json').write_text(json.dumps(result,indent=2)+'\n');return result

def augment(graph,access,access_path):
    g=json.loads(json.dumps(graph));assert not g.get('pg_access')
    for supply in ('VDD','VSS'):
        g['connections']['PG_'+supply]=dict(driver=dict(instance='TOP',pin=supply,direction='output'),
            sinks=[dict(instance=name,pin=supply,direction='input') for name in g['instances']])
    g.update(connected_nets=len(g['connections']),pg_access=str(access_path),pg_access_sha256=sha(access_path),
             scope='Original logical boundary plus two actual native M10 supply networks. Route candidate, not whole qualification.')
    return g
