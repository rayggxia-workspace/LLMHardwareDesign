"""Choose actual per-net useful copies; a real combined native check is mandatory."""
from pathlib import Path
from collections import defaultdict
import json,re,hashlib


def generate():
    b=Path('work/YUZE-LU/121/review-20261028');prior=json.loads(Path('project/experiments/block_v1/r-remaining-plan-893.json').read_bytes());options=defaultdict(list);inputs=prior['inputs_sha256'].copy()
    for folder,run,prefix in [('r-894-alternatives-899',894,'revision300-r-remaining-'),('r-897-orientation-901',897,'revision300-r-orientation-')]:
        index=json.loads((b/folder/'index.json').read_bytes());assert index['all_inputs_and_stable_outputs_verified']
        for i in range(6):
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
    routes=json.loads((b/'r-889-topology-891/observed-routes.json').read_bytes())
    plan=dict(source_native_count=55,source_receipt_sha256=prior['source_receipt_sha256'],inputs_sha256=inputs,variants=[dict(variant=0,selected=selected)],selection_provenance=provenance,unmatched_nets=sorted(set(routes)-set(options)),physical_qualified=False,scope='Only actual useful per-net copies, excluding every selected net implicated in an added native marker. Prefer same-cut/other-metal-identical orientation where equally effective. Source55 unchanged, one edit per net. Individual removal counts are selection evidence only, never a predicted combined result. Fresh whole native and exact entire DEF comparison are mandatory, followed by fullsignal and all final gates.')
    out=Path('project/experiments/block_v1/r-current-plan-900.json');assert not out.exists();out.write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('900 selected',len(selected),'unmatched',plan['unmatched_nets'])


if __name__=='__main__':generate()
