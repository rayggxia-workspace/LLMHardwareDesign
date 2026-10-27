"""Read-only connectivity explanation of rejected native input cut points."""
import collections
import json
from pathlib import Path
from io_slots import file_sha


def verify(root,out,cpus,policy):
    assert cpus==1 and policy in 'AC';base=out.parents[2]
    source=base/'block-v1-20261027-134/tasks'/('native-receive-shared109-'+policy.lower())
    r=json.loads((source/'receipt.json').read_text());assert r['passed']is False
    reports={};hashes={}
    for label in ['before','after']:
        path=source/('formal-'+label+'-logic.json');hashes[str(path)]=file_sha(path)
        assert hashes[str(path)]==r['outputs'][path.name]
        m=json.loads(path.read_text())['modules']['shared109'];drivers=set();used=collections.defaultdict(list)
        outputs=[];top_outputs=set()
        for name,p in m['ports'].items():
            if p['direction']in ('input','inout'):drivers.update(b for b in p['bits']if isinstance(b,int))
            if p['direction']in ('output','inout'):top_outputs.update(b for b in p['bits']if isinstance(b,int))
        for name,c in m['cells'].items():
            for pin,bits in c['connections'].items():
                direction=c['port_directions'][pin]
                if direction in ('output','inout'):
                    drivers.update(b for b in bits if isinstance(b,int))
                    for bit in bits:outputs.append((name,c['type'],pin,bit))
                if direction in ('input','inout'):
                    for bit in bits:
                        if isinstance(bit,int):used[bit].append((name,c['type'],pin))
        undriven={bit:uses for bit,uses in used.items()if bit not in drivers}
        missing_top=top_outputs-drivers
        aliases=collections.defaultdict(list)
        for name,n in m['netnames'].items():
            for bit in n['bits']:
                if bit in undriven or bit in missing_top:aliases[bit].append(name)
        unused=collections.Counter();samples=collections.defaultdict(list)
        for name,master,pin,bit in outputs:
            if bit not in used and bit not in top_outputs:
                key=master+'/'+pin;unused[key]+=1
                if len(samples[key])<12:samples[key].append(dict(instance=name,bit=bit))
        reports[label]=dict(cells=len(m['cells']),undriven_used_bits=[dict(bit=b,uses=undriven[b],aliases=aliases[b])for b in sorted(undriven)],
            undriven_top_outputs=[dict(bit=b,aliases=aliases[b])for b in sorted(missing_top)],
            unused_cell_output_counts=dict(unused),unused_output_samples=dict(samples),
            literal_constant_inputs=dict(collections.Counter(str(b)for c in m['cells'].values()for p,bits in c['connections'].items()if c['port_directions'][p]=='input'for b in bits if isinstance(b,str))))
        del m,drivers,used,outputs,aliases
    assert all(file_sha(Path(p))==h for p,h in hashes.items())
    (out/'native-c8-graph-inputs.json').write_text(json.dumps(dict(schema='block-v1-c8-graph-inputs/1',passed=True,policy=policy,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),inputs=hashes,graphs=reports,
        native_lec_qualified=False,qualified_hard_macro=False,
        scope='Read-only complete parsed graph driver/use and unused output diagnostic; no assumption that an unmatched native input is harmless, no graph edit or LEC waiver'),indent=2)+'\n')
