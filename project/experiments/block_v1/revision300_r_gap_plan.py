"""Finite gap-derived one/two-endpoint moves on the actual five-marker source."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
from revision300_v_clearance_corners import intersect,outside_area
from revision300_v_via_batch import contains
from revision300_v_via_bridge import path_key
from revision300_v_corner_probe import candidates


def generate():
    base=Path('work/YUZE-LU/121/review-20261028');folder=base/'r-903-neighborhood-906';top=base/'r-903-topology-907'
    meta=json.loads((folder/'revision300-r-current-neighborhood.json').read_bytes());tr=json.loads((top/'revision300-r-current-topology.json').read_bytes());routes=json.loads((top/'observed-routes.json').read_bytes())
    assert meta['passed']and tr['passed']and meta['source_native_count']==tr['source_native_count']==5 and meta['source_receipt_sha256']==tr['source_receipt_sha256']
    aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(folder/'net-aliases.tsv').read_text().splitlines())}
    dims={l:(int(w),int(s))for l,w,s in(line.split('\t')for line in(folder/'layer-dimensions.tsv').read_text().splitlines())};foot=defaultdict(list);shapes=defaultdict(list)
    for line in(folder/'via-footprints.tsv').read_text().splitlines():v,l,*box=line.split('\t');foot[v].append((l,list(map(int,box))))
    for line in(folder/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,a,l,k,*box=line.split('\t');shapes[int(i)].append((a,l,k,list(map(int,box))))
    options=defaultdict(list);seen=defaultdict(set)

    def clear(i,name,added,removed,retained):
        alias=aliases[name];window=meta['windows'][i]['bbox_dbu']
        for l,box in added:
            s=dims[l][1];assert s>0
            if box[0]-s<window[0]or box[1]-s<window[1]or box[2]+s>window[2]or box[3]+s>window[3]:return False
            known=[q for a,layer,k,q in shapes[i]if a==alias and layer==l and not k.endswith('obstruction')and not(k=='wire-via'and[layer,q]in removed)]
            known.extend(q for layer,q in retained if layer==l)
            for a,layer,k,q in shapes[i]:
                if layer!=l or a==alias and k=='wire-via'and[layer,q]in removed:continue
                if l.startswith('metal')and a==alias:continue
                overlap=intersect(box,[q[0]-s,q[1]-s,q[2]+s,q[3]+s])
                if overlap:
                    if not l.startswith('metal'):
                        dx=max(q[0]-box[2],box[0]-q[2],0);dy=max(q[1]-box[3],box[1]-q[3],0)
                        # Euclidean bbox distance is candidate pruning only;
                        # the unmodified native checker remains authoritative.
                        if dx*dx+dy*dy<s*s:return False
                    elif outside_area(known,overlap)>0:return False
        # Same-net cut spacing between two newly moved vias is also real.
        for j,(l,box)in enumerate(added):
            if l.startswith('metal'):continue
            s=dims[l][1]
            for ll,q in added[:j]:
                if l==ll:
                    dx=max(q[0]-box[2],box[0]-q[2],0);dy=max(q[1]-box[3],box[1]-q[3],0)
                    if dx*dx+dy*dy<s*s:return False
        return True

    def add(edit):
        name=edit['net'];key=json.dumps([edit['remove_paths'],edit['add_paths'],edit['add_rectangles']],sort_keys=True)
        if key in seen[name]:return
        old=Counter(map(path_key,routes[name]['nonrect_paths']))
        if any(old[path_key(p)]!=1 for p in edit['remove_paths'])or any(old[path_key(p)]for p in edit['add_paths']):return
        if any(x%10 or y%10 for p in edit['add_paths']for x,y,_ in p['points']):return
        if any(x%10 for l,*box in edit['add_rectangles']for x in box):return
        retained=[[l,box]for l,*box in edit['add_rectangles']]
        if not clear(edit['index'],name,edit['new_shapes'],edit['removed_coverage'],retained):return
        seen[name].add(key);options[name].append(edit)

    def moved(i,name,moves,wire,method):
        layer=meta['markers'][i]['layer'];remove=[];paths=[];rects=[];new=[];removed=[]
        for move in moves:
            via,point=move[:2];replacement=move[2]if len(move)==3 else via['via']
            x,y,_=via['points'][0]
            if point==[x,y]:continue
            assert contains(wire,layer,[x,y],point)
            other=[l for l,q in foot[via['via']]if l.startswith('metal')and l!=layer];assert len(other)==1;other=other[0]
            h=dims[other][0]//2
            original=dict(foot[via['via']]);alternative=dict(foot[replacement]);assert set(original)==set(alternative) and alternative[layer]==original[layer]
            assert all(box==alternative[l]for l,box in original.items()if not l.startswith('metal'))
            remove.append(via);paths.extend([dict(layer=other,points=[[x,y,None],point+[None]],via=None),dict(via,points=[point+[None]],via=replacement)])
            new.append([other,[min(x,point[0])-h,min(y,point[1])-h,max(x,point[0])+h,max(y,point[1])+h]])
            for l,(a,b,c,d)in foot[via['via']]:
                old=[x+a,y+b,x+c,y+d];removed.append([l,old])
                if l==other and [l]+old not in routes[name]['rectangles']:
                    rects.append([l]+old);new.append([l,old])
            for l,(a,b,c,d)in foot[replacement]:new.append([l,[point[0]+a,point[1]+b,point[0]+c,point[1]+d]])
        if not remove:return
        add(dict(index=i,indices=[i],net=name,method=method,remove_paths=remove,add_paths=paths,add_rectangles=rects,preserved_source_wires=[p for p in routes[name]['nonrect_paths']if not p['via']],new_shapes=new,removed_coverage=removed))

    for i,m in enumerate(meta['markers']):
        name=m['net'];layer=m['layer'];x0,y0,x1,y1=m['bbox_dbu'];vias=[];paths=routes[name]['nonrect_paths']
        row=dict(marker=m,same_net_nearby_rectangles=[dict(shape='wire'if k=='wire-rect'else k,bbox_dbu=q)for a,l,k,q in shapes[i]if a==aliases[name]and l==layer])
        corners,_=candidates([row])
        for p in corners:
            if [layer]+p['bbox_dbu']in routes[name]['rectangles']:continue
            add(dict(index=i,indices=[i],net=name,method='fresh-corner-including-original-RECTs',remove_paths=[],add_paths=[],add_rectangles=[[layer]+p['bbox_dbu']],preserved_source_wires=[],new_shapes=[[layer,p['bbox_dbu']]],removed_coverage=[]))
        for v in paths:
            if not v['via']or len(v['points'])!=1:continue
            x,y,_=v['points'][0]
            for l,(a,b,c,d)in foot[v['via']]:
                if l!=layer:continue
                a+=x;b+=y;c+=x;d+=y;direction=None;gap=None
                if c==x0 and b<=y0 and d>=y1:direction=[1,0];gap=x1-x0
                elif a==x1 and b<=y0 and d>=y1:direction=[-1,0];gap=x1-x0
                elif d==y0 and a<=x0 and c>=x1:direction=[0,1];gap=y1-y0
                elif b==y1 and a<=x0 and c>=x1:direction=[0,-1];gap=y1-y0
                if direction is None:continue
                assert gap>0 and gap%10==0
                vias.append((v,direction,gap))
                original=dict(foot[v['via']]);alternatives=[v['via']]+[name for name,fp in foot.items()if name!=v['via']and set(dict(fp))==set(original)and dict(fp)[layer]==original[layer]and all(box==dict(fp)[l]for l,box in original.items()if not l.startswith('metal'))]
                for distance in (gap+10,gap,gap+20):
                    point=[x+direction[0]*distance,y+direction[1]*distance]
                    for wire in paths:
                        if contains(wire,layer,[x,y],point):
                            for alternative in alternatives:moved(i,name,[(v,point,alternative)],wire,'single-endpoint-actual-gap-close-with-existing-tech-adjacent-enclosure')
        for j,(v,direction,gap)in enumerate(vias):
            a=v['points'][0][:2]
            for w,reverse,othergap in vias[:j]:
                if direction!=[-reverse[0],-reverse[1]]or gap!=othergap:continue
                b=w['points'][0][:2]
                wires=[p for p in paths if contains(p,layer,a,b)]
                for overlap in (10,0,20):
                    total=gap+overlap
                    for first in range(10,total,10):
                        second=total-first;ap=[a[0]+direction[0]*first,a[1]+direction[1]*first];bp=[b[0]+reverse[0]*second,b[1]+reverse[1]*second]
                        for wire in wires:
                            if contains(wire,layer,a,ap)and contains(wire,layer,b,bp):moved(i,name,[(v,ap),(w,bp)],wire,'split-two-endpoint-actual-gap-close')
    variants=[];singletons=[v[0]for name,v in sorted(options.items())if len(v)==1]
    if singletons:variants.append(dict(variant=0,selected=singletons))
    # Independent parameter trials become real queue items, not a small batch
    # of synchronous multi-net alternatives. Six slots can refill immediately.
    for name,choices in sorted(options.items()):
        if len(choices)==1:continue
        for p in choices:variants.append(dict(variant=len(variants),selected=[p]))
    assert variants and len({json.dumps(v['selected'],sort_keys=True)for v in variants})==len(variants)
    inputs={}
    for f,names in [(folder,['receipt.json','revision300-r-current-neighborhood.json','neighborhood.tsv','net-aliases.tsv','layer-dimensions.tsv','via-footprints.tsv']),(top,['receipt.json','revision300-r-current-topology.json','observed-routes.json'])]:
        for name in names:inputs[(f/name).as_posix()]=hashlib.sha256((f/name).read_bytes()).hexdigest()
    plan=dict(source_native_count=5,source_receipt_sha256=meta['source_receipt_sha256'],inputs_sha256=inputs,variants=variants,option_counts={name:len(v)for name,v in options.items()},unmatched_nets=sorted(set(routes)-set(options)),physical_qualified=False,scope='Actual fresh9035-marker geometry and routes; finite10DBU-gap-derived moves close measured gap or add10/20DBU overlap, optionally split between both original via endpoints. All original wires/RECTs retained; old adjacent pads retained. All exported layers including cut and same-net cut spacing pruned; native rules and full final gates remain authoritative. Up to six genuinely different alternatives; no filler or source qualification transfer.')
    plan['scope']='Actual fresh9035-marker geometry/routes. Finite measured-gap or10/20DBU-overlap moves along preserved wires; existing tech alternatives preserve cut and target metal, old adjacent pads retained. Scalar metal/OBS and Euclidean cut-bbox candidate pruning including same-net cuts; these do not replace any native rule. Three singleton nets grouped, independent endpoint parameters are separate queue items for6x16 dynamic refill. No empty/duplicate filler. Whole native, exact DEF, fullsignal and every final gate mandatory.'
    target=Path('project/experiments/block_v1/r-gap-plan-912.json');assert not target.exists();target.write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('912',plan['option_counts'],'tasks',[len(v['selected'])for v in variants],'unmatched',plan['unmatched_nets'])


if __name__=='__main__':generate()
