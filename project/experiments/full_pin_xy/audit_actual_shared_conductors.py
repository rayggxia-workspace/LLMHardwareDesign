"""Read the real pre-GRT checkpoint: geometry AND native DEF FIXED attributes."""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_escape_fixture import execute
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'common_integration/r01/C';odb=source/'fixed_prewires_NOT_FROZEN.odb'
    assert odb.exists() and 'STAGE_START lower_global_route' in (source/'lower_route.log').read_text()
    expected=json.loads((source/'actual_shared_conductors.json').read_text());assert len(expected)==256
    with (source/'before.shared.tsv').open() as f:geometry=list(csv.DictReader(f,delimiter='\t'))
    bypad={r['pad']:r for r in geometry};assert len(geometry)==len(bypad)==256
    for row in expected:
        q=bypad[row['construction_pad']];assert q['layer']=='metal10'
        assert all(int(q[k])==round(row[k+'_um']*2000) for k in ['x0','y0','x1','y1'])
    out=ROOT/'shared_conductor_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [odb,source/'actual_shared_conductors.json',source/'before.shared.tsv',source/'lower_route.tcl']}
    rec={'scope':'ACTUAL_256_FIXED_M10_NATIVE_CHECKPOINT_NOT_FROZEN_BASE_OR_TWO_MODE_REUSE',
      'source_SHA':inputs,'qualified':False,'frozen':False,'complete_two_mode_physical_reuse':'NOT_VERIFIED',
      'full_lower_route_DRC_connectivity_RC_STA':'NOT_YET_QUALIFIED',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    script=out/'audit.tcl';script.write_text('read_db '+tcl(odb)+'\nwrite_def '+tcl(out/'native_checkpoint.def')+'\n')
    rec['native_export_returncode']=execute(common,script,out/'native.log',threads=1)
    try:
        assert rec['native_export_returncode']==0
        nets={q['net']:q for q in geometry};found={};active=None;parts=[];in_nets=False
        with (out/'native_checkpoint.def').open() as f:
            for line in f:
                if re.match(r'^NETS\s+\d+\s*;',line):in_nets=True;continue
                if line.strip()=='END NETS':in_nets=False
                if not in_nets:continue
                start=re.match(r'^-\s+(\S+)',line)
                if start:active=start.group(1);parts=[]
                if active in nets:parts.append(line)
                if ';' in line and active:
                    if active in nets:
                        text=''.join(parts);assert active not in found
                        assert re.search(r'\+\s+FIXED\s+metal10\b',text),('Shared wire not actually FIXED',active)
                        assert not re.search(r'\+\s+(?:ROUTED|COVER)\b',text),('Unexpected non-FIXED route',active)
                        assert re.findall(r'\+\s+FIXED\s+(\S+)',text)==['metal10']
                        q=nets[active];assert re.findall(r'\(\s*PIN\s+(\S+)\s*\)',text)==[q['pad']]
                        found[active]={'net':active,'pad':q['pad'],'native_DEF_path_status':'FIXED','native_layer':'metal10',
                          'native_metal_bbox_dbu':[int(q[k]) for k in ['x0','y0','x1','y1']],
                          'native_DEF_net_statement':text.strip()}
                    active=None;parts=[]
        assert set(found)==set(nets) and len(found)==256
        (out/'native_fixedness.json').write_text(json.dumps(sorted(found.values(),key=lambda x:x['pad']),indent=2)+'\n')
        rec['all_256_native_FIXEDS_and_original_net_bindings_verified']=True
        rec['native_shared_conductor_count']=len(found)
        rec['actual_shared_centerline_length_um']=sum(q['length_um'] for q in expected)
        rec['width_um']=.8;rec['centerline_length_each_um']=32.
        rec['geometry_bbox_includes_half_width_endcaps']=True
    except Exception:
        rec['all_256_native_FIXEDS_and_original_net_bindings_verified']=False;rec['actual_failure']=traceback.format_exc()
    rec['all_closed_source_files_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec['all_256_native_FIXEDS_and_original_net_bindings_verified'] and rec['all_closed_source_files_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
