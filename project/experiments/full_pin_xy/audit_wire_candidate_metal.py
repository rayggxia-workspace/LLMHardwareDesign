"""Check existing remaining WIRE candidates against current real metal.

Read-only, exact integer rectangle union. Excludes all BTerms from coverage,
so moving several interface rectangles cannot create circular justification.
This is a preflight for an actual edit, not parent AP or DRC qualification.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,datetime,gzip,json,os,sys,traceback
from run_exports import ROOT,sha

DRIVER=Path(__file__).resolve().parent

def covered_area(tile,rects):
    clips=[]
    for r in rects:
        z=(max(tile[0],r[0]),max(tile[1],r[1]),min(tile[2],r[2]),min(tile[3],r[3]))
        if z[0]<z[2] and z[1]<z[3]:clips.append(z)
    xs=sorted({z[i] for z in clips for i in (0,2)});area=0
    for a,b in zip(xs,xs[1:]):
        spans=sorted((z[1],z[3]) for z in clips if z[0]<=a and z[2]>=b)
        end=None;length=0
        for lo,hi in spans:
            if end is None or lo>end:length+=hi-lo;end=hi
            elif hi>end:length+=hi-end;end=hi
        area+=(b-a)*length
    return area

def run(revision):
    source=ROOT/'owned_cap_wire_restore/r01';views=ROOT/'llsys_owned_restored_views/r01/llaccel_aux-C'
    old=ROOT/'all_llsys_actual_access_caps/r02'
    inputs=[source/'execution.json',source/'routed.odb',source/'whole_access.tsv.gz',views/'execution.json',views/'pins.tsv',old/'execution.json',old/'all13507_actual_own_via_candidates.tsv']
    sq=json.loads(inputs[0].read_text());vq=json.loads((views/'execution.json').read_text());oq=json.loads((old/'execution.json').read_text())
    assert sq.get('completed_utc') and sq['fresh_DRC_count']==0 and sq['all_closed_sources_unchanged']
    assert vq.get('completed_utc') and vq['source_native_DRC']==0
    assert oq.get('completed_utc') and oq['all_closed_sources_unchanged']
    for p in inputs[1:3]:assert sha(p)==sq['files'][p.name]['sha256']
    assert sha(views/'pins.tsv')==vq['files']['pins.tsv']['sha256']
    assert sha(old/'all13507_actual_own_via_candidates.tsv')==oq['files']['all13507_actual_own_via_candidates.tsv']['sha256']
    hashes={str(p):sha(p) for p in inputs}
    out=ROOT/'wire_candidate_metal_preflight'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'CURRENT_SOURCE_REMAINING_WIRE_CANDIDATE_METAL_UNION_PREFLIGHT_NOT_PHYSICAL_ACCESS_PASS','source_SHA':hashes,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'actual_edit_DRC_RC_STA':'NOT_EXECUTED_READ_ONLY_PREFLIGHT','excluded_from_metal_coverage':['all BTerm rectangles'],'not_checked':['Foreign signal/PG/OBS spacing','Parent access/via enclosure and full applicable DRC','Functional and timing qualification']}
    try:
        pins={r['pin']:r for r in csv.DictReader((views/'pins.tsv').open(),delimiter='\t') if r['use'] not in ['POWER','GROUND']};assert len(pins)==13507
        rows=[r for r in csv.DictReader((old/'all13507_actual_own_via_candidates.tsv').open(),delimiter='\t') if r['candidate_kind']=='WIRE'];assert len(rows)==2832
        wanted=defaultdict(set)
        for r in rows:
            p=pins[r['pin']];assert all(r[k]==p[k] for k in ['pin','net','layer','x0','y0','x1','y1'])
            wanted[r['net']].add(r['layer'])
        geom=defaultdict(list);terms=defaultdict(list);nrows=0
        with gzip.open(str(source/'whole_access.tsv.gz'),'rt') as f:
            for r in csv.DictReader(f,delimiter='\t'):
                nrows+=1
                if r['net'] not in wanted or r['layer'] not in wanted[r['net']]:continue
                box=tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
                if r['kind'] in ['WIRE','VIA','ITERM']:geom[r['net'],r['layer']].append((r['kind'],box))
                if r['kind']=='BTERM':terms[r['net'],r['layer']].append((r['link'],box))
        output=[]
        for r in rows:
            oldbox=tuple(int(r[k]) for k in ['x0','y0','x1','y1']);x,y=int(r['candidate_x']),int(r['candidate_y']);newbox=(x-140,y-140,x+140,y+140)
            shapes=geom[r['net'],r['layer']];rects=[box for kind,box in shapes]
            assert ('B:'+r['pin'],oldbox) in terms[r['net'],r['layer']]
            actual_candidate=any(kind=='WIRE' and box[0]<=newbox[0] and box[1]<=newbox[1] and box[2]>=newbox[2] and box[3]>=newbox[3] for kind,box in shapes)
            assert actual_candidate,'Historical WIRE candidate no longer contained in current actual WIRE: '+r['pin']
            area=covered_area(oldbox,rects);assert covered_area(newbox,rects)==78400
            item=dict(r);item.update(old_pin_area_DBU2=78400,old_pin_covered_by_non_BTerm_metal_DBU2=area,old_pin_metal_that_would_be_removed_DBU2=78400-area,new_pin_fully_inside_current_own_WIRE=True,preflight_status='METAL_UNION_UNCHANGED_READY_FOR_NATIVE_EDIT' if area==78400 else 'KEEP_PENDING_EXACT_METAL_RETENTION_IMPLEMENTATION')
            output.append(item)
        with (out/'all2832_current_wire_metal_preflight.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
        rec.update(all_2832_original_pin_contracts_and_current_candidate_WIRE_verified=True,current_source_geometry_rows_scanned=nrows,status_counts=dict(Counter(r['preflight_status'] for r in output)),total_old_pin_metal_removed_if_blindly_moved_DBU2=sum(r['old_pin_metal_that_would_be_removed_DBU2'] for r in output),no_pin_wire_via_cell_changed=True)
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in hashes.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])

if __name__=='__main__':sys.exit(run(sys.argv[1]))
