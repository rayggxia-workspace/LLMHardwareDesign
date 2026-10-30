"""Execute actual OBS compaction and verify installed OpenDB import roundtrip."""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'llsys_parent_tip_views/r01/llaccel_aux-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    api=ROOT/'obs_union_api/r01/execution.json';aq=json.loads(api.read_text());assert aq['exact_integer_XOR_empty'] and aq['sample_has_hole']
    assert prior.get('completed_utc') and prior['source_native_DRC']==0 and prior['all_sources_and_pre_RCX_geometry_unchanged']
    lef=source/'detailed.lef';lib=source/'timing.lib'
    for p in [lef,lib]:assert sha(p)==prior['files'][p.name]['sha256']
    out=ROOT/'obs_union_compaction'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,lef,lib,api]}
    rec={'scope':'ACTUAL_SOURCE_OBS_GEOMETRY_COMPACTION_AND_NATIVE_IMPORT_NOT_PARENT_ACCESS_OR_DRC_QUALIFICATION',
         'full_qualification':False,'source_SHA':inputs,'source_physical_ODB_SHA256':prior['source_geometry_sha256'],
         'source_epoch':'Closed four-tip native0 source, NOT active10261-pin ECO; no automatic view promotion',
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'selected_layers':['metal1','metal2','metal3'],'native_returncodes':{},
         'not_checked':['Native router/DRC treatment of changed rectangle decomposition','Parent AP and actual reroute','Full rules, GDS/RC/STA/PG/system freeze']}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    (out/'input.json').write_text(json.dumps({'source_LEF':str(lef),'source_LEF_SHA256':sha(lef)},indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        cmd=common+['--env','PINXY_OBS_UNION_OUT='+str(out),IMAGE,'klayout','-b','-r',str(DRIVER/'compact_obs_union_klayout.py')]
        with (out/'union_native.log').open('x') as f:rec['native_returncodes']['exact_KLayout_union']=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
        assert rec['native_returncodes']['exact_KLayout_union']==0
        union=json.loads((out/'exact_union.json').read_text());assert not union.get('actual_failure') and union['source_LEF_unchanged']
        rec['actual_exact_union']=union;save()
        name=None
        with lef.open() as f:
            for line in f:
                if line.strip().startswith('MACRO '):name=line.split()[1];break
        assert name
        platform='/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/'
        for label,path in [('original',lef),('compacted',out/'compacted_GEOMETRY_ONLY.lef')]:
            body='''set m [[ord::get_db] findMaster NAME];if {$m eq "NULL"} {error "Source macro missing"}
set f [open PINS w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open SIZE w];puts $f [list [$m getWidth] [$m getHeight] [$m getOrigin]];close $f
'''.replace('NAME',tcl(name)).replace('PINS',tcl(out/(label+'.pins.tsv'))).replace('SIZE',tcl(out/(label+'.size.tsv')))
            if label=='compacted':body+='set f [open '+tcl(out/'native_compacted_OBS.tsv')+' w];foreach z [$m getObstructions] {set layer [[$z getTechLayer] getName];if {$layer in {metal1 metal2 metal3}} {puts $f [join [list $layer [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}};close $f\n'
            script=out/(label+'.tcl');script.write_text('read_lef '+tcl(platform+'NangateOpenCellLibrary.tech.lef')+'\nread_lef '+tcl(platform+'NangateOpenCellLibrary.macro.mod.lef')+'\nread_lef '+tcl(path)+'\nread_liberty '+tcl(lib)+'\n'+body)
            rec['native_returncodes'][label+'_OpenDB_import']=execute(common,script,out/(label+'.log'),threads=1);save()
            assert rec['native_returncodes'][label+'_OpenDB_import']==0
        assert (out/'original.pins.tsv').read_bytes()==(out/'compacted.pins.tsv').read_bytes()
        assert (out/'original.size.tsv').read_bytes()==(out/'compacted.size.tsv').read_bytes()
        rec['all_original_native_PIN_rectangles_directions_USE_layers_size_exact']=True
        expected={layer:Counter() for layer in rec['selected_layers']};actual={layer:Counter() for layer in rec['selected_layers']}
        for layer in expected:
            with (out/(layer+'.rects.dbu.tsv')).open() as f:
                for line in f:expected[layer][tuple(map(int,line.split()))]+=1
        with (out/'native_compacted_OBS.tsv').open() as f:
            for line in f:
                t=line.split();actual[t[0]][tuple(map(int,t[1:]))]+=1
        assert expected==actual
        rec['native_OpenDB_import_all_compacted_rectangle_multisets_exact']=True
        rec['all_13507_signal_interfaces_imported']=sum(r['use'] not in ['POWER','GROUND'] for r in csv.DictReader((out/'compacted.pins.tsv').open(),delimiter='\t'))==13507
        assert rec['all_13507_signal_interfaces_imported']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
