"""Minimal two-WIRE bypass using independently proven native cut behavior.

All original other-net routes, original via10 and existing via11 stay. Only
the two actual offending M11 WIRE records may be replaced. Native execution
and complete composed-net DRC remain mandatory after geometric preparation.
"""
from pathlib import Path
import csv,gzip,json
from plan_upper_whole_nets import astar
from plan_upper_local_bypass import rect,contains,HALF,box_wire
from check_access import check_rows

def plan(branches,obstructions,diefile,out):
    with gzip.open(branches,'rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
    obs=[]
    for line in Path(obstructions).read_text().splitlines():
        p=line.split()
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    die=list(map(int,Path(diefile).read_text().split()));edits=[];fail=None
    specs=[('src[248]',(4876190,5285740,4877790,5287340)),('src[206]',(4930590,5276140,4932190,5277740))]
    for net,marker in specs:
        hits=[r for r in rows if r['net']==net and r['kind']=='WIRE' and r['layer']=='metal11' and contains(rect(r),marker)];assert len(hits)==1
        old=hits[0];z=rect(old);a=(z[0]+HALF,z[1]+HALF);b=(z[2]-HALF,z[3]-HALF);margin=48000
        region=(min(a[0],b[0])-margin,min(a[1],b[1])-margin,max(a[0],b[0])+margin,max(a[1],b[1])+margin)
        q=astar(rows,obs,net,a,b,die,region_override=region,include_own_cuts=True)
        if not q['path_dbu']:fail=dict(net=net,old_wire=old,**q);break
        rows=[r for r in rows if r is not old];existing={rect(r) for r in rows if r['net']==net and r['kind']=='VIA' and r['layer']=='via11'};reuse=[];serial=len(rows)
        for i,(p,t) in enumerate(zip(q['path_dbu'],q['path_dbu'][1:])):
            box=box_wire(p,t)
            if p[2]!=t[2] and box in existing:reuse.append([p[0],p[1]]);continue
            layers=['metal'+str(p[2])] if p[2]==t[2] else ['metal11','metal12','via11'];kind='WIRE' if p[2]==t[2] else 'VIA'
            for layer in layers:rows.append(dict(zip(['x0','y0','x1','y1'],map(str,box)),net=net,layer=layer,kind=kind,link='native_rule_proposed_'+str(serial)+'_'+str(i)))
        edits.append(dict(net=net,removed_wire_box_DBU=z,removed_layer='metal11',native_short_box_DBU=marker,reused_existing_via11_centers_DBU=reuse,**q))
    result={'scope':'TWO_WIRE_NATIVE_RULE_BYPASS_PREPARATION_NOT_PHYSICAL_IMPLEMENTATION','status':'PROPOSED_TWO_WIRE_BYPASSES_NATIVE_REQUIRED' if not fail else 'FAILED_BOUNDED_NATIVE_RULE_BYPASS','failure':fail,'edits':edits,'all_original_via10_via11_and_other_WIRE_material_retained':True,'fixed_M1_M10_and_pin_geometry_unchanged':True,'cut_rule_source':'Actual native orthogonal FAIL1 / diagonal PASS0 in upper_cut_corner_probe/r03, technology unchanged','full_qualification':False}
    if not fail:
        result['proposed_per_net_geometry']=check_rows(sorted([dict(r) for r in rows],key=lambda r:r['net']),True);assert result['proposed_per_net_geometry']['pass']
        with gzip.open(str(Path(out).with_name('proposed_branch_geometry_NOT_IMPLEMENTED.tsv.gz')),'wt') as f:
            w=csv.DictWriter(f,fieldnames=['net','layer','x0','y0','x1','y1','kind','link'],delimiter='\t');w.writeheader();w.writerows(rows)
    Path(out).write_text(json.dumps(result,indent=2)+'\n');return result
