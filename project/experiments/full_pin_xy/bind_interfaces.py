"""Bind actual logical peers to same-version physical pin layers; keep parent handoff unknown."""
from pathlib import Path
from collections import Counter
import argparse,json,gzip,pandas as pd

REPO=Path(__file__).resolve().parents[3]
def main(root):
    root=Path(root).resolve();maps=json.loads((root/'inventory/pin_logical_mapping.json').read_text(encoding='utf-8'))
    physical={};source={}
    for case in maps:
        if case in ['act','gemm']:
            t=pd.read_csv(REPO/f'docs/experiments/issue-119-pin-xy/data/{case}_pin_coordinates.csv.gz');t=t[t.plan=='A']
            pp={r.pin:{'layer':r.layer,'direction':r.direction,'x_um':r.x_um,'y_um':r.y_um} for _,r in t.iterrows()}
        else:
            t=pd.read_csv(root/'physical'/case/'bterms.tsv.gz',sep='\t');t=t[~t.pin.isin(['VDD','VSS'])]
            pp={str(r.pin).replace('\\',''):{'layer':r.layer,'direction':r.direction,'x_um':(r.x0+r.x1)/4000,'y_um':(r.y0+r.y1)/4000} for _,r in t.iterrows()}
        assert len(pp)==len(t) and set(pp)==set(maps[case]),(case,'port set differs')
        for pin,p in pp.items():assert p['direction'].lower()==maps[case][pin]['original_direction']
        physical[case]=pp
    rows=[];stats={}
    for case,mp in maps.items():
        count=Counter()
        for pin,m in mp.items():
            peers=[]
            # A literal is a value, never a single physical net connecting every same-valued pin.
            if isinstance(m['parent_bit'],str):
                peers=[{'block':'CONSTANT','pin':m['parent_bit'],'pin_layer':'NOT_APPLICABLE','connection_kind':'literal value; no shared physical net inferred'}]
            else:
                for q in m['logical_peers']:
                    layer=physical.get(q['block'],{}).get(q['pin'],{}).get('layer','EXTERNAL_UNKNOWN')
                    peers.append({'block':q['block'],'pin':q['pin'],'direction':q['direction'],'pin_layer':layer})
            known=any(p['pin_layer'] in ['metal5','metal6'] for p in peers);count['peer_endpoint_layer_known']+=known
            count['external_or_unbound_only']+=not known
            rows.append({'case':case,'pin':pin,'layer':physical[case][pin]['layer'],'direction':physical[case][pin]['direction'],
                         'semantic_bus':m['semantic_bus'],'semantic_bit':m['semantic_bit'],'parent_bit':str(m['parent_bit']),
                         'logical_peers_json':json.dumps(peers,ensure_ascii=False,separators=(',',':')),
                         'original_parent_handoff_layer':'UNKNOWN','actual_traversed_layer_sequence':'UNKNOWN',
                         'binding_scope':'logical peer + peer original pin layer verified; not a routed parent path or fixed M8 escape'} )
        stats[case]={'signal_pins':len(mp),'physical_port_name_width_direction_match':True,**dict(count),
                     'parent_handoff_layer_known':0,'changed_parent_connections':0,'changed_pin_layers':0}
    pd.DataFrame(rows).to_csv(root/'inventory/pin_bindings.csv',index=False,encoding='utf-8-sig')
    con=pd.read_csv(root/'inventory/connections.csv',keep_default_na=False)
    con['source_pin_layer']=[physical.get(r.source_block,{}).get(r.source_pin,{}).get('layer','EXTERNAL_OR_CONSTANT') for _,r in con.iterrows()]
    con['sink_pin_layer']=[physical.get(r.sink_block,{}).get(r.sink_pin,{}).get('layer','EXTERNAL_OR_CONSTANT') for _,r in con.iterrows()]
    con.to_csv(root/'inventory/connections_physical_endpoints.csv',index=False,encoding='utf-8-sig')
    (root/'inventory/binding_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert len(rows)==24767
    print('BOUND',len(rows),'physical signal pins across 6 blocks; peer endpoint layers checked, original parent handoffs explicitly unknown')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();main(a.root)
