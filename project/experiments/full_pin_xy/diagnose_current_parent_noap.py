"""Bind the actual parent NoAP to current leaf metal and exported OBS.

No inferred emptiness, no abstract-only repair, no unverified target layer.
"""
from pathlib import Path
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
DRIVER=Path(__file__).resolve().parent


def run(revision):
    fail=ROOT/'current_common_pin_access/r01';fp=fail/'execution.json';f=json.loads(fp.read_text())
    assert f.get('completed_utc') and f['native_returncode']==1 and f['all_immutable_phase_sources_unchanged']
    assert any('u_llaccel_aux/bit_1016' in s for s in f['exact_error_lines'])
    parent=ROOT/'common_checkpoint_def_import/corner-r01';pq=json.loads((parent/'execution.json').read_text());assert pq.get('completed_utc') and pq['native_returncodes']['fresh_import']==0
    odb=parent/'imported_current_NOT_ROUTED_NOT_FROZEN.odb';assert sha(odb)==f['source_SHA'][str(odb)]==pq['files'][odb.name]['sha256']
    source=ROOT/'llsys_corner_fill/r01';sq=json.loads((source/'execution.json').read_text());assert sq.get('completed_utc') and sq['fresh_DRC_count']==0 and sq['all_closed_sources_unchanged']
    view=ROOT/'llsys_corner_fill_views/r01/llaccel_aux-C';vq=json.loads((view/'execution.json').read_text());assert vq.get('completed_utc') and vq['source_geometry_sha256']==sq['files']['routed.odb']['sha256']
    alias=parent/'p126resume_llaccel_aux.lef';assert sha(alias)==pq['files'][alias.name]['sha256']
    paths=[source/'whole_access.tsv.gz',source/'after.pins.tsv',view/'pins.tsv']
    for p in paths:assert sha(p)==(sq if p.parent==source else vq)['files'][p.name]['sha256']
    pin=next(r for r in csv.DictReader((view/'pins.tsv').open(),delimiter='\t') if r['pin']=='bit_1016')
    assert pin['layer']=='metal5' and pin['net']=='bit_1016'
    box=tuple(int(pin[k]) for k in ['x0','y0','x1','y1']);cx=(box[0]+box[2])//2;cy=(box[1]+box[3])//2
    pose=next(r for r in csv.DictReader((parent/'after.instances.tsv').open(),delimiter='\t') if r['instance']=='u_llaccel_aux');assert pose['orientation']=='R0'
    out=ROOT/'current_parent_failed_pin_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in paths+[fp,parent/'execution.json',parent/'after.instances.tsv',source/'execution.json',view/'execution.json',alias]}
    rec={'scope':'ACTUAL_PARENT_BIT1016_OBS_VS_CURRENT_WIRE_DIAGNOSIS_NOT_REPAIR_OR_FULL_RULE_PASS','source_SHA':inputs,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
         'target':pin,'center_local_um':[cx/2000.,cy/2000.],'center_parent_um':[(cx+int(pose['x']))/2000.,(cy+int(pose['y']))/2000.],
         'physical_edit_RC_STA':'NOT_EXECUTED_READONLY','historical_parent_target_layer':'UNKNOWN_RETAINED; no new original target invented'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    try:
        inside=False;layer=None;origin=None;obs=[];radius=100000
        for line in alias.open():
            p=line.split()
            if not p:continue
            if p[0]=='ORIGIN':origin=[float(p[1]),float(p[2])]
            if p==['OBS']:inside=True
            elif inside and p[0]=='LAYER':layer=p[1]
            elif inside and p[0]=='RECT' and layer in ['metal4','metal5','metal6','metal7']:
                b=tuple(round(float(x)*2000) for x in p[1:5])
                if b[0]<=cx+radius and b[2]>=cx-radius and b[1]<=cy+radius and b[3]>=cy-radius:obs.append({'net':'UNOWNED_PARENT_ABSTRACT_OBS','layer':layer,'box_DBU':b,'kind':'ACTUAL_EXPORTED_MACRO_OBS'})
            elif inside and p==['END']:inside=False
        assert origin==[0.,0.]
        overlap=lambda a,b:a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
        rec['actual_adjacent_M6_OBS_intersections_at_same_size_first_cap']=[r for r in obs if r['layer']=='metal6' and overlap(box,r['box_DBU'])]
        rec['actual_parent_OBS_rows_in_100um_window']=len(obs);save()
        local=[];own=[];examined=0
        with gzip.open(str(paths[0]),'rt') as stream:
            assert stream.readline().strip().split('\t')==['net','layer','x0','y0','x1','y1','kind','link']
            for line in stream:
                p=line.rstrip('\n').split('\t');examined+=1
                if len(p)!=8 or p[1] not in ['metal4','metal5','metal6','metal7','via4','via5','via6']:continue
                b=tuple(map(int,p[2:6]));r={'net':p[0],'layer':p[1],'box_DBU':b,'kind':p[6],'link':p[7]}
                if p[0]=='bit_1016':own.append(r)
                if b[0]<=cx+radius and b[2]>=cx-radius and b[1]<=cy+radius and b[3]>=cy-radius:local.append(r)
        rec['current_signal_geometry_rows_examined']=examined
        rec['actual_M6_metal_intersections_at_first_cap']=[r for r in local if r['layer']=='metal6' and overlap(box,r['box_DBU'])]
        for filename,rows in [('actual_local_signal_and_parent_OBS.json.gz',local+obs),('actual_complete_target_high_geometry.json.gz',own)]:
            with gzip.open(str(out/filename),'wt') as stream:json.dump(rows,stream)
        rec['root_status']='OBS intersection and actual ownership evidence only; sole native root not proved until real leaf change and fresh parent AP'
        rec['root_hypothesis']='Exported upper-layer obstruction may contain own-net metal, or a retained unresolved foreign obstruction. Do not remove OBS to claim pass.'
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
