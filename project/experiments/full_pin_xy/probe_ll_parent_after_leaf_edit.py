"""Native fresh parent AP using a real edited leaf; no timing model reuse claim."""
import json,re
from run_exports import ROOT,sha
from run_parent_trial import tcl
from coarsen_parent_low_obs import coarsen
from run_common_integration import alias_stream


def probe(out,run_native):
    parent=ROOT/'common_checkpoint_def_import/corner-r01';receipt=parent/'execution.json';q=json.loads(receipt.read_text())
    assert q.get('completed_utc') and q['all_closed_sources_unchanged']
    assert run_native('native_geometry_export','read_db '+tcl(out/'routed.odb')+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(out/'parent_probe_detailed.lef')+'\nclose $stages',threads=1)==0
    proof=coarsen(out/'parent_probe_detailed.lef',out/'parent_probe_low.lef',requested=('metal1','metal2','metal3'))
    oldview=ROOT/'llsys_corner_fill_views/r01/llaccel_aux-C/execution.json';v=json.loads(oldview.read_text())
    assert proof['original_OBS_envelope_DBU']==v['conservative_parent_low_OBS_preparation']['original_OBS_envelope_DBU']
    master=next(line.split()[1] for line in (out/'parent_probe_detailed.lef').open() if line.startswith('MACRO '))
    alias_stream(out/'parent_probe_low.lef',out/'p126resume_llaccel_aux.lef',master,'p126resume_llaccel_aux')
    script=parent/'fresh_import.tcl';deffile=parent/'current_fixed.def'
    for p in [script,deffile]:assert sha(p)==q['files'][p.name]['sha256']
    reads=[line for line in script.read_text().splitlines() if line.startswith('read_lef ')];assert len(reads)==8
    old='read_lef '+tcl(parent/'p126resume_llaccel_aux.lef');assert reads.count(old)==1
    reads=[('read_lef '+tcl(out/'p126resume_llaccel_aux.lef')) if line==old else line for line in reads]
    body='\n'.join(reads+['read_def '+tcl(deffile),'set_routing_layers -signal metal2-metal10 -clock metal4-metal10','stage full_current_parent_AP {pin_access}','close $stages'])
    rc=run_native('full_current_parent_AP',body,threads=4);log=(out/'full_current_parent_AP.log').read_text()
    counters={k:int(v) for k,v in re.findall(r'^#(\w*NoAp)\s*=\s*(\d+)',log,re.M)}
    errors=[line for line in log.splitlines() if '[ERROR ' in line or 'STAGE_FAIL full_current_parent_AP' in line]
    return {'scope':'ACTUAL_ALL_COMMON_PARENT_MACRO_PIN_ACCESS_ONLY_NOT_ROUTED_OR_TIMING_MODEL',
            'native_returncode':rc,'native_no_access_counters':counters,'errors':errors,
            'pass':rc==0 and 'STAGE_EXECUTED full_current_parent_AP' in log and bool(counters) and not any(counters.values()) and not errors,
            'source_parent_receipt_SHA256':sha(receipt),'source_current_fixed_DEF_SHA256':sha(deffile),
            'actual_low_OBS_envelope_matches_previous_PG_screened_source':True,'geometry_view_RC_STA_model':'NOT_EXPORTED_BY_THIS_PROBE'}
