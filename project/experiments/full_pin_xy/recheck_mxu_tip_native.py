"""Recheck only fresh DRC with the exact original MXU allowed layer range.

The new actual routed ODB/SPEF are reused. Preserve the r01 DRT-0155 failure;
do not repeat routing, change technology rules, or silently widen source layers.
"""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'mxu_actual_via_tip/r01';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['native_returncodes']=={'actual_edit_and_analysis':0,'fresh_DRC':1}
    assert q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_nets']==191438
    assert q['all_other_191437_multiterminal_route_box_multisets_identical'] and q['exactly_four_actual_M6_WIRE_rectangles_removed_all_vias_unchanged']
    assert q['complete_pin_contract']['only_changed_XY_pins']==['act_data[12]'] and q['complete_pin_contract']['all_signal_pins']==2172
    assert all(q['all_cells_signal_connections_PG_die_unchanged'].values()) and q['all_closed_sources_unchanged']
    assert q['setup_ns']>=0 and q['hold_ns']>=0 and q['literal_VIOLATED_markers_not_complete_failure_count']==0
    for name in ['routed.odb','extracted.spef','independent.log']:assert sha(source/name)==q['files'][name]['sha256']
    assert 'DRT-0155' in (source/'independent.log').read_text() and 'uses layer metal9' in (source/'independent.log').read_text()
    original=ROOT/'pin_escape_route/r02/mxu-C';op=original/'execution.json';p=json.loads(op.read_text())
    assert p['fresh_DRC_count']==0 and p['native_returncodes']['fresh_DRC']==0
    config=original/'fresh.tcl';assert sha(config)==p['files']['fresh.tcl']['sha256']
    ranges=re.findall(r'(?m)^set_routing_layers -signal (\S+) -clock (\S+)\s*$',config.read_text())
    assert ranges==[('metal2-metal10','metal4-metal10')]
    out=ROOT/'mxu_actual_tip_fresh'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(x):sha(x) for x in [rp,source/'routed.odb',source/'extracted.spef',source/'independent.log',op,config]}
    rec={'scope':'FRESH_ONLY_RECHECK_SAME_CLOSED_ECO_ODB_UNDER_EXACT_ORIGINAL_MXU_ALLOWED_LAYERS',
      'source_SHA':inputs,'full_qualification':False,'source_actual_ECO_ODB_SHA256':sha(source/'routed.odb'),
      'source_actual_ECO_SPEF_SHA256':sha(source/'extracted.spef'),
      'original_allowed_signal_clock_ranges':ranges[0],
      'prior_DRT_0155_failure_preserved':True,'routing_RCX_STA_reexecuted':False,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'inherited_exact_source_setup_hold_ns':[q['setup_ns'],q['hold_ns']],
      'complete_GDS_parent_RTL':'NOT_EXECUTED_NOT_QUALIFIED'}
    try:
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(source/'routed.odb')+'\nset_routing_layers -signal '+ranges[0][0]+' -clock '+ranges[0][1]+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_fresh_returncode']=execute(common,script,out/'native.log',threads=1)
        if rec['native_fresh_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(x))==h for x,h in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in out.iterdir() if x.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('native_fresh_returncode')==0 and rec.get('fresh_DRC_count')==0 and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
