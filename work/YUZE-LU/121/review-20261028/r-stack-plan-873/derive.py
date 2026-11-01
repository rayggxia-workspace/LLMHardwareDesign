from pathlib import Path
import json,hashlib
s=Path('work/YUZE-LU/121/review-20261028/r-alternate-plan-869/derive.py').read_text(encoding='utf-8');prefix=s[:s.index('for i,m in enumerate(meta[\'markers\']):')]
exec(compile(prefix,'869-setup-only','exec'))
earlier=Path('project/experiments/block_v1/r-alternate-plan-869.json');alt=json.loads(earlier.read_bytes())
for p in alt['selected']:seen.add(p['net']);extras.extend((p['net'],l,q)for l,q in p['new_shapes'])
for i,m in enumerate(meta['markers']):
 name=m['net'];layer=m['layer'];own=aliases[name];paths=routes[name]['nonrect_paths'];options=[]
 if layer!='metal3'or name in seen:continue
 row=dict(marker=m,same_net_nearby_rectangles=[dict(bbox_dbu=q,shape=k)for a,l,k,q in shapes[i]if a==own and l==layer])
 for aa,bb in pairs(row):
  aa=list(aa);bb=list(bb);wires=[p for p in paths if contains(p,'metal3',aa,bb)]
  if not wires:continue
  for a,bp in [(aa,bb),(bb,aa)]:
   av=[p for p in paths if p['layer']=='metal2'and p['via']and len(p['points'])==1 and p['points'][0][:2]==a]
   bv=[p for p in paths if p['layer']=='metal2'and p['via']and len(p['points'])==1 and p['points'][0][:2]==bp]
   if len(av)!=1 or len(bv)!=1 or av[0]['via']!=bv[0]['via']or any(v%10 for v in a+bp):continue
   half=dimensions['metal2'][0]//2;spacing=dimensions['metal2'][1]
   box=[min(a[0],bp[0])-half,min(a[1],bp[1])-half,max(a[0],bp[0])+half,max(a[1],bp[1])+half];wx0,wy0,wx1,wy1=meta['windows'][i]['bbox_dbu']
   if box[0]-spacing<wx0 or box[1]-spacing<wy0 or box[2]+spacing>wx1 or box[3]+spacing>wy1:continue
   context=shapes[i]+[(aliases[net],l,'active-candidate-addition',q)for net,l,q in extras]
   ownboxes=[q for alias,l,k,q in context if alias==own and l=='metal2'and not k.endswith('obstruction')];collision=False
   for alias,l,k,q in context:
    if alias==own or l!='metal2':continue
    overlap=intersect(box,[q[0]-spacing,q[1]-spacing,q[2]+spacing,q[3]+spacing])
    if overlap and outside_area(ownboxes,overlap)>0:collision=True;break
   if collision:continue
   options.append(dict(index=i,net=name,a=a,b=bp,removed_via=av[0],retained_via=bv[0],moved_via=None,preserved_source_wires=wires,retain_pad_layer='metal2',added_bridge=dict(layer='metal2',points=[a+[None],bp+[None]],via=None),new_shapes=[('metal2',box)],method='same-via2-pair-retain-original-M2-pad'))
 if options:
  p=options[0];selected.append(p);seen.add(name);extras.extend((name,l,q)for l,q in p['new_shapes'])
 else:skipped.append(i)
assert selected
d=dict(selected=selected,selected_count=len(selected),skipped=skipped,physical_qualified=False,source_native_count=584,source_receipt_sha256=alt['source_receipt_sha256'],observed_sha256=alt['observed_sha256'],geometry_sha256=alt['geometry_sha256'],inputs_sha256=alt['inputs_sha256'],other_plan_sha256=hashlib.sha256(earlier.read_bytes()).hexdigest(),scope='Derived only, independent remaining same-via2 pairs including direct via1/via2 stacks. Original M3 wires and other via retained, removed via M2 pad retained explicitly plus alternate M2 bridge. No assumption that a stacked M2 endpoint has a wire record. R851 complete geometry plus314/53/64 proposed additions conservatively included; all those nets excluded, remaining candidates sequentially pruned. Full native/correct DEF/fullsignal/final gates mandatory.')
out=Path('project/experiments/block_v1/r-stack-plan-873.json');assert not out.exists();out.write_bytes((json.dumps(d,indent=2)+'\n').encode());print('873',len(selected),'shards',Counter(int(hashlib.sha256(p['net'].encode()).hexdigest(),16)%6 for p in selected),'skipped',len(skipped))
