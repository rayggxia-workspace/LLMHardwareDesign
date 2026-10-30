"""Local actual-metal diagnosis after the full-interface parent AP failure."""
from pathlib import Path
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'all_llsys_parent_owned_realization/r01';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['all_closed_sources_unchanged'] and q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['all_original_WIRE_VIA_exact']
    assert not q['actual_full_parent_AP']['pass'] and any('u_llaccel_aux/bit_1166' in x for x in q['actual_full_parent_AP']['errors'])
    pin='bit_1166';geo=source/'whole_access.tsv.gz';alias=source/'p126resume_llaccel_aux.lef';ps=source/'full_current_parent_AP.tcl';coordinates=source/'all_13507_actual_pin_correspondence.csv'
    paths=[geo,alias,ps,coordinates]
    for p in paths:assert sha(p)==q['files'][p.name]['sha256']
    row=next(x for x in csv.DictReader(coordinates.open()) if x['pin']==pin);box=tuple(round(float(row['actual_'+k+'_um'])*2000) for k in ['x0','y0','x1','y1']);cx=(box[0]+box[2])//2;cy=(box[1]+box[3])//2
    out=ROOT/'current_full_pin_local_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in paths+[rp]};rec={'scope':'LOCAL_NATIVE_PARENT_PIN_AND_ACTUAL_METAL_OBS_DIAGNOSIS_NOT_PHYSICAL_REPAIR',
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'target':row,'target_box_DBU':box,'full_qualification':False,'native_returncodes':{},'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    try:
        reads=[x for x in ps.read_text().splitlines() if x.startswith(('read_lef ','read_def '))];assert len(reads)==9
        script=out/'read_actual_parent_pin.tcl';script.write_text('\n'.join(reads)+r'''
set i [[ord::get_db_block] findInst u_llaccel_aux];set mt [[$i getMaster] findMTerm bit_1166]
set f [open '''+tcl(out/'actual_parent_pin.tsv')+r''' w]
puts $f [join [concat origin [[$i getMaster] getOrigin]] "\t"]
puts $f [join [concat pose [$i getLocation] [$i getOrient]] "\t"]
foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list pin [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}};close $f
''')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_returncodes']['fresh_parent_native_pin']=execute(common,script,out/'read_actual_parent_pin.log',threads=1);save();assert rec['native_returncodes']['fresh_parent_native_pin']==0
        native=[x.split() for x in (out/'actual_parent_pin.tsv').read_text().splitlines()]
        assert native[0]==['origin','0','0'] and native[1][-1]=='R0' and native[2]==['pin','metal5']+list(map(str,box))
        rec['actual_parent_center_um']=[(cx+int(native[1][1]))/2000.,(cy+int(native[1][2]))/2000.]
        obs=[];inside=False;ly=None;radius=100000
        near=lambda b:b[0]<=cx+radius and b[2]>=cx-radius and b[1]<=cy+radius and b[3]>=cy-radius
        overlap=lambda a,b:a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
        for line in alias.open():
            p=line.split()
            if p==['OBS']:inside=True
            elif inside and p and p[0]=='LAYER':ly=p[1]
            elif inside and p and p[0]=='RECT' and ly in ['metal4','metal5','metal6','metal7']:
                b=tuple(round(float(v)*2000) for v in p[1:5])
                if near(b):obs.append({'net':'PARENT_ABSTRACT_OBS_NO_OWNERSHIP','layer':ly,'box_DBU':b,'kind':'OBS'})
            elif inside and p==['END']:inside=False
        local=[];own=[];examined=0
        with gzip.open(str(geo),'rt') as f:
            for p in csv.DictReader(f,delimiter='\t'):
                examined+=1
                if p['layer'] not in ['metal4','metal5','metal6','metal7','via4','via5','via6']:continue
                b=tuple(int(p[k]) for k in ['x0','y0','x1','y1']);r={'net':p['net'],'layer':p['layer'],'box_DBU':b,'kind':p['kind'],'link':p['link']}
                if p['net']==pin:own.append(r)
                if near(b):local.append(r)
        rec['current_geometry_rows_examined']=examined;rec['own_high_geometry_count']=len(own)
        rec['own_actual_M5_support']=[r for r in own if r['layer']=='metal5' and r['kind'] in ['WIRE','VIA']]
        rec['actual_M6_OBS_touching_current_first_cap']=[r for r in obs if r['layer']=='metal6' and overlap(box,r['box_DBU'])]
        rec['actual_M6_signal_touching_current_first_cap']=[r for r in local if r['layer']=='metal6' and overlap(box,r['box_DBU'])]
        for name,rows in [('local_actual_signal_and_OBS.json.gz',local+obs),('all_target_high_geometry.json.gz',own)]:
            with gzip.open(str(out/name),'wt') as f:json.dump(rows,f)
        rec['root_status']='Actual intersection evidence only; need native physical repair and parent AP before claiming causal closure'
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])


if __name__=='__main__':sys.exit(run(sys.argv[1]))
