"""Choose actual per-net useful copies; a real combined native check is mandatory."""
from pathlib import Path
from collections import defaultdict
import json,re,hashlib


def generate(gap=False):
    b=Path('work/YUZE-LU/121/review-20261028');prior=json.loads(Path('project/experiments/block_v1/'+('r-gap-plan-912.json'if gap else'r-remaining-plan-893.json')).read_bytes());options=defaultdict(list);inputs=prior['inputs_sha256'].copy()
    families=[('r-914-gap-917',914,'revision300-r-gap-')]if gap else[('r-894-alternatives-899',894,'revision300-r-remaining-'),('r-897-orientation-901',897,'revision300-r-orientation-')]
    for folder,run,prefix in families:
        index=json.loads((b/folder/'index.json').read_bytes());assert index['all_inputs_and_stable_outputs_verified']
        for i in range(7 if gap else 6):
            task=b/folder/'tasks'/(prefix+str(i));receipt=json.loads((task/'receipt.json').read_bytes());report=json.loads((task/'revision300-r-remaining.json').read_bytes());selected=json.loads((task/'selected-edits.json').read_bytes())
            assert report['passed']==receipt['passed'] and report['source_receipt_sha256']==prior['source_receipt_sha256'] and report['exact_normal_net_header_path_rect_and_nonnet_delta']and report['original_inputs_unchanged']
            for name in ('receipt.json','revision300-r-remaining.json','remaining-native-drc.rpt','selected-edits.json'):
                h=hashlib.sha256((task/name).read_bytes()).hexdigest();assert h==index['files'][(task/name).relative_to(b/folder).as_posix()]['sha256']
                if name!='receipt.json':assert h==receipt['outputs'][name]
                inputs[(task/name).as_posix()]=h
            changed={p['net']for p in selected};bad={n.replace('\\','')for marker in report['added']for n in re.findall(r'net:(\S+)',marker)}&changed
            removed=defaultdict(int)
            for marker in report['removed']:
                for n in re.findall(r'net:(\S+)',marker):removed[n.replace('\\','')]+=1
            for p in selected:
                if p['net']in bad or not removed[p['net']]:continue
                score=(-removed[p['net']],run!=897,len(p['add_paths'])+len(p['add_rectangles']),i)
                options[p['net']].append((score,p,dict(task='block-v1-20261101-'+str(run)+'/tasks/'+prefix+str(i),variant=i,actual_local_removed_markers=removed[p['net']],actual_added_marker_participant=False)))
    selected=[];provenance={}
    for name,choices in sorted(options.items()):
        score,p,evidence=min(choices,key=lambda v:v[0]);selected.append(p);provenance[name]=evidence
    assert selected and len({p['net']for p in selected})==len(selected)
    routes=json.loads((b/('r-903-topology-907'if gap else'r-889-topology-891')/'observed-routes.json').read_bytes())
    untested=[];untested_evidence={}
    if gap:
        # The actual failed half-fill creates a second, adjacent same-net
        # notch. Union both explicit boxes; this new candidate is untested.
        from decimal import Decimal
        from revision300_v_clearance_corners import intersect,outside_area
        assert set(routes)-set(options)=={'net113322'}
        failed=b/'r-914-gap-917/tasks/revision300-r-gap-0';d=json.loads((failed/'revision300-r-remaining.json').read_bytes())
        assert not d['passed']and d['added_markers']==1 and len(d['added'])==1
        marker=d['added'][0];match=re.fullmatch(r'violation type: Metal Spacing srcs: net:net113322 bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer metal2',marker);assert match
        coords=[Decimal(v)*2000 for v in match.groups()];assert all(v==int(v)for v in coords);box=list(map(int,coords))
        previous=next(p for p in json.loads((failed/'selected-edits.json').read_bytes())if p['net']=='net113322');assert len(previous['add_rectangles'])==1
        l,*oldbox=previous['add_rectangles'][0];assert l=='metal2'and oldbox[1]==box[3]
        union=[min(oldbox[0],box[0]),min(oldbox[1],box[1]),max(oldbox[2],box[2]),max(oldbox[3],box[3])]
        geometry=b/'r-903-neighborhood-906';meta=json.loads((geometry/'revision300-r-current-neighborhood.json').read_bytes());i=previous['index'];assert meta['markers'][i]['net']=='net113322'
        aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(geometry/'net-aliases.tsv').read_text().splitlines())};shapes=[]
        for line in(geometry/'neighborhood.tsv').read_text().splitlines():
            if not line or line.startswith('#'):continue
            j,a,ll,k,*q=line.split('\t')
            if int(j)==i and ll==l:shapes.append((a,k,list(map(int,q))))
        own=[q for a,k,q in shapes if a==aliases['net113322']and not k.endswith('obstruction')];spacing={layer:int(s)for layer,w,s in(line.split('\t')for line in(geometry/'layer-dimensions.tsv').read_text().splitlines())}[l];window=meta['windows'][i]['bbox_dbu']
        assert union[0]-spacing>=window[0]and union[1]-spacing>=window[1]and union[2]+spacing<=window[2]and union[3]+spacing<=window[3]
        for a,k,q in shapes:
            if a==aliases['net113322']:continue
            overlap=intersect(union,[q[0]-spacing,q[1]-spacing,q[2]+spacing,q[3]+spacing]);assert not overlap or outside_area(own,overlap)==0
        extra=outside_area(own,union);assert extra>0
        p=dict(index=i,indices=[i],net='net113322',method='untested-union-of-actual-original-and-added-notch-halves',remove_paths=[],add_paths=[],add_rectangles=[[l]+union],preserved_source_wires=[v for v in routes['net113322']['nonrect_paths']if not v['via']],new_shapes=[[l,union]],removed_coverage=[])
        selected.append(p);untested=[p];untested_evidence['net113322']=dict(task='block-v1-20261101-914/tasks/revision300-r-gap-0',actual_failed_added_marker=marker,original_half_rectangle=oldbox,union_rectangle=union,estimated_added_area_dbu2=extra,scalar_foreign_clearance_pass=True,passed=False,scope='New union geometry derived from actual failed half-fill; whole combined native check is the first EDA test, no prior qualification.')
    plan=dict(source_native_count=5 if gap else 55,source_receipt_sha256=prior['source_receipt_sha256'],inputs_sha256=inputs,variants=[dict(variant=0,selected=selected)],selection_provenance=provenance,unmatched_nets=sorted(set(routes)-set(options)),physical_qualified=False,scope='Only actual useful per-net copies, excluding every selected net implicated in an added native marker. One edit per net on its actual source. Individual removal counts are selection evidence only, never a predicted combined result. Fresh whole native and exact entire DEF comparison mandatory, followed by fullsignal and all final gates.')
    if gap:
        plan.update(untested_candidates=untested,untested_candidate_evidence=untested_evidence,unmatched_nets=[],scope='Four actual useful per-net edits plus one explicitly UNTESTED union of actual old/new net113322 notch halves. No actual failed half-fill is reused as passed. Exact source5 routes/geometry and actual failed native report bound. The combined whole-native check tests the new union for the first time; every final gate still pending.')
    out=Path('project/experiments/block_v1/'+('r-gap-compose-plan-918.json'if gap else'r-current-plan-900.json'));assert not out.exists();out.write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('selected',len(selected),'unmatched',plan['unmatched_nets'])


if __name__=='__main__':
    import sys
    generate(gap='--gap'in sys.argv)
