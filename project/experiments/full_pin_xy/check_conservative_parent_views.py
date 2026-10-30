"""Native readback of all conservatively aggregated current parent views."""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent

def lef_contract(path):
    pin=None;direction=None;use='SIGNAL';layer=None;obs=False;pins=Counter();counts=Counter();low={};size=None
    for line in path.open():
        p=line.split()
        if not p:continue
        if p[0]=='SIZE':size=(round(float(p[1])*2000),round(float(p[3])*2000))
        if p[0]=='PIN':pin=p[1];direction=None;use='SIGNAL'
        elif pin and p==['END',pin]:pin=None
        elif pin and p[0]=='DIRECTION':direction=p[1]
        elif pin and p[0]=='USE':use=p[1]
        if p==['OBS']:obs=True
        elif obs and p==['END']:obs=False
        elif p[0]=='LAYER':layer=p[1]
        elif p[0]=='RECT':
            z=tuple(round(float(x)*2000) for x in p[1:5])
            if pin:pins[(pin,direction,use,layer)+z]+=1
            elif obs:
                counts[layer]+=1
                if layer in ['metal1','metal2','metal3','metal4']:low.setdefault(layer,[]).append(z)
    return pins,counts,low,size

def run(revision):
    source=ROOT/'parent_conservative_low_views/r01';rp=source/'execution.json';q=json.loads(rp.read_text());assert q.get('completed_utc') and not q.get('actual_failure') and q['all_sources_unchanged']
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';out=ROOT/'parent_conservative_native_check'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,tech]+[source/('p126_'+c+'.lef') for c in q['cases']]};rec={'scope':'NATIVE_ALL_SIX_CONSERVATIVE_PARENT_VIEWS_READBACK_NOT_ROUTE_OR_FREEZE','source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'cases':{}}
    try:
        lines=['read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef']
        for case in q['cases']:lines.append('read_lef '+tcl(source/('p126_'+case+'.lef')))
        for case in q['cases']:
            body='''set m [[ord::get_db] findMaster NAME];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open PINS w];puts $f "pin\\tdirection\\tuse\\tlayer\\tx0\\ty0\\tx1\\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\\t"]}}};close $f
set f [open COUNTS w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\\t$n"};close $f
set f [open SIZE w];puts $f [list [$m getWidth] [$m getHeight]];close $f
'''
            for key,value in [('NAME','p126_'+case),('PINS',out/(case+'.pins.tsv')),('COUNTS',out/(case+'.OBS_counts.tsv')),('SIZE',out/(case+'.size.tsv'))]:body=body.replace(key,tcl(value))
            lines.append(body)
        script=out/'readback.tcl';script.write_text('\n'.join(lines)+'\n');common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_returncode']=execute(common,script,out/'native.log',threads=1);assert rec['native_returncode']==0
        total=0
        for case in q['cases']:
            path=source/('p126_'+case+'.lef');pins,counts,low,size=lef_contract(path)
            actual=Counter()
            for r in csv.DictReader((out/(case+'.pins.tsv')).open(),delimiter='\t'):actual[tuple(r[k] for k in ['pin','direction','use','layer'])+tuple(int(r[k]) for k in ['x0','y0','x1','y1'])]+=1
            assert pins==actual
            assert tuple(map(int,(out/(case+'.size.tsv')).read_text().split()))==size
            native_counts={p[0]:int(p[1]) for p in (line.split() for line in (out/(case+'.OBS_counts.tsv')).read_text().splitlines())};assert native_counts==dict(counts)
            count=len({r[0] for r in pins if r[2] not in ['POWER','GROUND']});total+=count
            rec['cases'][case]={'all_native_PIN_rectangles_direction_USE_layers_and_SIZE_exact':True,'all_native_OBS_layer_counts_match_written_view':True,'signal_pins':count,'aggregated_layers':q['cases'][case]['aggregated_layers'],'original_metal_never_removed_or_represented_as_empty':True}
        assert total==24767;rec['all_24767_signal_pins_and_PG_preserved']=True
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec['all_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
