"""Check extracted terminal identities against declared signal and PG roles.

Power roles come from the supplied ODB inventory, never from net-name guesses.
The extraction itself remains an independent KLayout geometry operation.
"""
import argparse
import json
from pathlib import Path
from native_inventory import sha


def audit(inventory,topology):
    assert topology['passed']
    terms=inventory['terms'];probes=topology['boundary_probes']
    expected={name for name,t in terms.items() if t['signal_type']=='SIGNAL' and
              any(s['layer']=='metal10' for s in t['shapes'])}
    assert set(probes)==expected,'extracted signal terminal coverage mismatch'
    token=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'))
    components={};signals={}
    for name,row in probes.items():
        assert row['native_net']==terms[name]['native_net'],'terminal native identity mismatch'
        observed={token(p['token']) for p in row['probes']}
        assert len(observed)==1,'disconnected terminal shapes'
        physical=next(iter(observed));native=row['native_net']
        assert components.setdefault(native,physical)==physical,'disconnected native signal'
        assert signals.setdefault(physical,native)==native,'native signal short'
    pg_terms={name:t for name,t in terms.items() if t['signal_type'] in ('POWER','GROUND')}
    assert {t['signal_type'] for t in pg_terms.values()}=={'POWER','GROUND'},'missing declared PG roles'
    seen=set();pg={}
    for row in topology['power_probes']:
        name=row['label']
        if name not in pg_terms:continue # Additional GDS text probes are not role declarations.
        seen.add(name);role=pg_terms[name]['signal_type'];physical=token(row['token'])
        assert pg.setdefault(physical,role)==role,'power physically shorted to ground'
        assert physical not in signals,'signal physically shorted to PG'
    assert seen==set(pg_terms),'declared PG terminal coverage mismatch'
    return {'passed':True,'signal_terminals':len(probes),'signal_components':len(signals),
            'pg_terminals':len(seen),'pg_components':len(pg),
            'scope':'exact extracted M1--M10 terminal/component identities, with ODB-declared PG roles'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','topology','output'):p.add_argument(name,type=Path)
    a=p.parse_args();topology=json.loads(a.topology.read_text())
    assert topology['inventory_sha256']==sha(a.inventory),'changed extraction inventory'
    result=audit(json.loads(a.inventory.read_text()),topology)
    result.update(inventory_sha256=sha(a.inventory),topology_sha256=sha(a.topology))
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
