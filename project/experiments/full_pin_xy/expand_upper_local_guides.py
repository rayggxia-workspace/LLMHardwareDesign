"""Actual endpoint-neighbor selection and guide-only search-space expansion.

No pin, lower landing, via, metal, technology or spacing rule is edited here.
Native detailed route and independent full adapter checks remain mandatory.
"""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,re


def endpoint_blockers(branches):
    with gzip.open(branches,'rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
    box=lambda r:tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
    contains=lambda a,b:a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]
    observations=[];ids=set()
    for net,marker in [('src[248]',(4876190,5285740,4877790,5287340)),('src[206]',(4930590,5276140,4932190,5277740))]:
        hit=[r for r in rows if r['net']==net and r['layer']=='metal11' and r['kind']=='WIRE' and contains(box(r),marker)]
        assert len(hit)==1;z=box(hit[0]);assert min(z[2]-z[0],z[3]-z[1])==1600
        for x,y in [(z[0]+800,z[1]+800),(z[2]-800,z[3]-800)]:
            point=(x-800,y-800,x+800,y+800)
            for r in rows:
                if r['net']==net or r['layer']!='metal12' or r['kind']!='WIRE':continue
                b=box(r);dx=max(point[0]-b[2],b[0]-point[2],0);dy=max(point[1]-b[3],b[1]-point[3],0)
                if max(dx,dy)>=1600:continue
                match=re.fullmatch(r'src\[(\d+)\]',r['net']);assert match
                ids.add(int(match[1]));observations.append({'crossing_branch':net,'actual_M11_segment_box_dbu':list(z),
                  'actual_segment_endpoint_dbu':[x,y],'M12_blocking_branch':r['net'],'M12_blocking_box_dbu':list(b),'actual_link':r['link']})
    assert ids=={128,129,201},('Unexpected actual blockers, review source',ids)
    return sorted(ids),observations


def expand(source,dest,selected,native_log,die,gcell_steps=4):
    original=Path(source).read_text();log=Path(native_log).read_text()
    matches=re.findall(r'GCELLGRID [XY] [-\d]+ DO \d+ STEP (\d+)',log)
    assert len(matches)>=2 and set(matches)=={'5700'},'Actual source native GCell lattice changed'
    delta=int(matches[0])*gcell_steps;selected={'src['+str(i)+']' for i in selected}
    lines=original.splitlines();output=[];current=None;changed=0;old_m10=[];new_m10=[];unselected=[]
    for line in lines:
        if line.startswith('src['):
            assert re.fullmatch(r'src\[\d+\]',line);current=line
        p=line.split()
        if len(p)==5 and p[-1].startswith('metal'):
            assert current;z=list(map(int,p[:4]));layer=p[4]
            if layer=='metal10':old_m10.append((current,line))
            if current in selected and layer in ['metal11','metal12']:
                z=[max(die[0],z[0]-delta),max(die[1],z[1]-delta),min(die[2],z[2]+delta),min(die[3],z[3]+delta)]
                assert z[2]>z[0] and z[3]>z[1]
                line=' '.join(map(str,z))+' '+layer;changed+=1
            elif current not in selected:unselected.append((current,line))
            if layer=='metal10':new_m10.append((current,line))
        output.append(line)
    assert Counter(old_m10)==Counter(new_m10) and changed>0
    assert len({x for x in lines if x.startswith('src[')})==770
    Path(dest).write_text('\n'.join(output)+'\n')
    return {'source_guide_SHA256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
      'expanded_guide_SHA256':hashlib.sha256(Path(dest).read_bytes()).hexdigest(),
      'actual_GCell_step_dbu':5700,'expanded_GCell_steps_each_side':gcell_steps,'expansion_um':delta/2000.,
      'expanded_M11_M12_guide_rectangles':changed,'all_original_M10_guide_rectangles_exact':True,
      'other_branches_guides_exact':True,'guide_hints_only_not_new_metal_or_rule_change':True,'full_qualification':False}
