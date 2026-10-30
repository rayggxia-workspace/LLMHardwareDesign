"""Source-bound whole-interface track audit and actual NoAP-net extraction.

Track alignment is a geometric diagnostic, never an access/DRC verdict. Read
completed native exports; do not alter any routed source or invent endpoints.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,os,re,sys,traceback
from decimal import Decimal
from run_exports import ROOT,sha

DRIVER=Path(__file__).resolve().parent
COUNTS={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}


def pins(path):
    name=None;rows=[];layer=None
    with path.open() as f:
        for line in f:
            t=line.strip().split()
            if not t:continue
            if t[0]=='OBS' and name is None:break
            if t[0]=='PIN':name=t[1];kind='SIGNAL';direction=None;boxes=[]
            elif name is not None:
                if t[0]=='USE':kind=t[1]
                elif t[0]=='DIRECTION':direction=t[1]
                elif t[0]=='LAYER':layer=t[1]
                elif t[0]=='RECT':boxes.append((layer,[int(Decimal(x)*2000) for x in t[1:5]]))
                elif t==['END',name]:
                    if kind not in ['POWER','GROUND']:rows.append((name,direction,kind,boxes))
                    name=None
    return rows


def run(revision):
    parent=ROOT/'common_lower_resume/r02';pq=json.loads((parent/'execution.json').read_text())
    assert pq.get('completed_utc') and 'DRT-0073' in (parent/'native.log').read_text() and 'u_llaccel_aux/bit_1025' in (parent/'native.log').read_text()
    leaf=ROOT/'llsys_actual_via_tips/r02';lq=json.loads((leaf/'execution.json').read_text())
    assert lq.get('completed_utc') and lq['fresh_DRC_count']==0 and lq['all_closed_sources_unchanged']
    geometry=leaf/'whole_access.tsv.gz';assert sha(geometry)==lq['files'][geometry.name]['sha256']
    out=ROOT/'parent_noap_grid_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    files=[parent/'execution.json',parent/'native.log',parent/'before_route.instances.tsv',parent/'regrouped_BPin.def',leaf/'execution.json',geometry]
    aliases={case:ROOT/'common_integration/r01/C'/('p126_'+case+'.lef') for case in COUNTS}
    inputs={str(p):sha(p) for p in files+list(aliases.values())}
    rec={'scope':'ALL24767_PARENT_INTERFACE_TRACK_GEOMETRY_AND_REAL_NoAP_NET_DIAGNOSIS_NOT_REPAIR_OR_ACCESS_PASS',
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
      'parent_leaf_selection':'Original R02 aliases; current native0 LL source differs at three other XY pins only',
      'not_checked':['Fresh native repair/access','Local PG/OBS via clearance','Full DRC/LVS','RC/STA/electrical or functional qualification'],
      'alignment_flags_are_geometric_risks_not_access_verdicts':True}
    try:
        positions={}
        for line in (parent/'before_route.instances.tsv').read_text().splitlines():
            t=line.split('\t')
            if len(t)==5 and t[0].startswith('u_') and t[1].startswith('p126_'):
                assert t[4]=='R0';positions[t[0][2:]]=(int(t[2]),int(t[3]))
        assert set(positions)==set(COUNTS)
        tracks={}
        with (parent/'regrouped_BPin.def').open() as f:
            for line in f:
                m=re.match(r'TRACKS ([XY]) (\d+) DO (\d+) STEP (\d+) LAYER (metal[56]) ;',line)
                if m:tracks[m.group(5),m.group(1)]=(int(m.group(2)),int(m.group(4)))
                if line.startswith('COMPONENTS'):break
        assert len(tracks)==4
        rows=[];summary={}
        for case,path in aliases.items():
            data=pins(path);assert len(data)==COUNTS[case]
            dx,dy=positions[case];bad=0
            for name,direction,kind,boxes in data:
                assert len(boxes)==1;layer,b=boxes[0];assert layer in ['metal5','metal6']
                axis='Y' if layer=='metal5' else 'X';a,z=(b[1]+dy,b[3]+dy) if axis=='Y' else (b[0]+dx,b[2]+dx)
                start,pitch=tracks[layer,axis];res=((a+z)-2*start)%(2*pitch);delta=min(res,2*pitch-res)
                bad+=int(delta!=0)
                rows.append({'case':case,'pin':name,'direction':direction,'use':kind,'layer':layer,
                    'local_x0_um':b[0]/2000.,'local_y0_um':b[1]/2000.,'local_x1_um':b[2]/2000.,'local_y1_um':b[3]/2000.,
                    'macro_origin_x_um':dx/2000.,'macro_origin_y_um':dy/2000.,'preferred_axis':axis,
                    'preferred_track_center_aligned':delta==0,'nearest_preferred_track_center_offset_um':delta/4000.})
            summary[case]={'signal_pins':len(data),'preferred_axis_center_not_aligned':bad,
                           'macro_origin_aligned_to_both_actual_M5_M6_pitches':all(v%tracks['metal5','X'][1]==0 for v in [dx,dy])}
        assert len(rows)==24767 and len({(r['case'],r['pin']) for r in rows})==24767
        with (out/'all24767_actual_parent_pin_track_geometry.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        target=next(r for r in rows if r['case']=='llaccel_aux' and r['pin']=='bit_1025')
        rec['actual_error_pin_parent_geometry']=target;rec['per_block_track_geometry']=summary
        selected={'bit_1025','bit_1382013','bit_6907','bit_1389626'};counts=Counter()
        with gzip.open(geometry,'rt') as f,(out/'actual_error_and_three_repaired_complete_nets.tsv').open('w',newline='') as g:
            reader=csv.DictReader(f,delimiter='\t');w=csv.DictWriter(g,fieldnames=reader.fieldnames,delimiter='\t');w.writeheader()
            for r in reader:
                if r['net'] in selected:w.writerow(r);counts[r['net']]+=1
        assert sum(counts[n] for n in selected if n!='bit_1025')==854
        rec['actual_complete_selected_net_row_counts']=dict(counts)
        rec['missing_error_net_rows_policy']='If bit_1025 absent, whole export excludes one-terminal/unused nets; endpoint remains UNKNOWN and requires native DB lookup, never invented.'
        rec['old_3_pin_native4_to_native0_source_unchanged_here']=True
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
