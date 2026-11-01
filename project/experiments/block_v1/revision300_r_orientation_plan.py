"""Finite existing-tech via enclosure alternatives on actual current55 source."""
from pathlib import Path
from collections import defaultdict
import json,hashlib
from revision300_v_clearance_corners import intersect,outside_area


def generate():
    base=Path('work/YUZE-LU/121/review-20261028');folder=base/'r-880-neighborhood-892'
    meta=json.loads((folder/'revision300-r-current-neighborhood.json').read_bytes())
    routes=json.loads((base/'r-889-topology-891/observed-routes.json').read_bytes())
    prior=json.loads(Path('project/experiments/block_v1/r-remaining-plan-893.json').read_bytes())
    assert meta['passed'] and meta['source_receipt_sha256']==prior['source_receipt_sha256'] and meta['source_native_count']==55
    aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(folder/'net-aliases.tsv').read_text().splitlines())}
    foot=defaultdict(dict);shapes=defaultdict(list)
    spacing={l:int(s) for l,w,s in(line.split('\t')for line in(folder/'layer-dimensions.tsv').read_text().splitlines())}
    for line in(folder/'via-footprints.tsv').read_text().splitlines():
        v,l,*box=line.split('\t');assert l not in foot[v];foot[v][l]=list(map(int,box))
    for line in(folder/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,a,l,k,*box=line.split('\t');shapes[int(i)].append((a,l,k,list(map(int,box))))
    options=defaultdict(list)
    for i,m in enumerate(meta['markers']):
        name=m['net'];layer=m['layer'];marker=m['bbox_dbu'];own=aliases[name]
        for path in routes[name]['nonrect_paths']:
            if not path['via'] or len(path['points'])!=1:continue
            original=foot[path['via']]
            if layer not in original:continue
            x,y,_=path['points'][0];a,b,c,d=original[layer];box=[x+a,y+b,x+c,y+d]
            if not ((box[2]==marker[0]or box[0]==marker[2])and box[1]<=marker[1]and box[3]>=marker[3]or(box[3]==marker[1]or box[1]==marker[3])and box[0]<=marker[0]and box[2]>=marker[2]):continue
            for replacement,fp in foot.items():
                if set(fp)!=set(original) or any(fp[l]!=v for l,v in original.items() if l!=layer) or fp[layer]==original[layer]:continue
                a,b,c,d=fp[layer];new=[x+a,y+b,x+c,y+d]
                # Require a strict reduction toward the actual notch, not a random via variant.
                reduces=(box[3]==marker[1]and new[3]<box[3]or box[1]==marker[3]and new[1]>box[1]or box[2]==marker[0]and new[2]<box[2]or box[0]==marker[2]and new[0]>box[0])
                if not reduces:continue
                s=spacing[layer];window=meta['windows'][i]['bbox_dbu']
                if new[0]-s<window[0]or new[1]-s<window[1]or new[2]+s>window[2]or new[3]+s>window[3]:continue
                coverage=[q for a,l,k,q in shapes[i]if a==own and l==layer and not k.endswith('obstruction')and not(k=='wire-via'and q==box)]
                bad=False
                for a,l,k,q in shapes[i]:
                    if a==own or l!=layer:continue
                    overlap=intersect(new,[q[0]-s,q[1]-s,q[2]+s,q[3]+s])
                    if overlap and outside_area(coverage,overlap)>0:bad=True;break
                if bad:continue
                moved=dict(path,via=replacement)
                options[name].append(dict(index=i,indices=[i],net=name,method='same-cut-identical-other-layer-existing-tech-via-orientation',remove_paths=[path],add_paths=[moved],add_rectangles=[],preserved_source_wires=[v for v in routes[name]['nonrect_paths']if not v['via']],new_shapes=[[layer,new]],removed_coverage=[[layer,box]],same_cut_and_other_layer_exact=True))
    # One minimal deterministic option per net, six independent disjoint net shards.
    selected=[min(v,key=lambda p:json.dumps(p,sort_keys=True))for name,v in sorted(options.items())]
    variants=[dict(variant=i,selected=[p for p in selected if int(hashlib.sha256(p['net'].encode()).hexdigest(),16)%6==i],conflicting_nets_skipped=[])for i in range(6)]
    assert all(v['selected']for v in variants),'Never pad with empty/duplicate tasks'
    result=dict(source_native_count=55,source_receipt_sha256=prior['source_receipt_sha256'],inputs_sha256=prior['inputs_sha256'],variants=variants,physical_qualified=False,scope='Existing native tech vias only, exactly same cut and other-metal enclosure; target enclosure retracts from actual notch and complete fresh foreign/OBS scalar pruning passes. No custom via or rule changes; all original paths and RECTs retained except exact specified via swap. Whole native and later fullsignal/all final gates mandatory. Six disjoint net shards, not six repeats; combined result must be checked.')
    target=Path('project/experiments/block_v1/r-orientation-plan-896.json');assert not target.exists();target.write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print('896',len(selected),'nets', [len(v['selected'])for v in variants])


if __name__=='__main__':generate()
