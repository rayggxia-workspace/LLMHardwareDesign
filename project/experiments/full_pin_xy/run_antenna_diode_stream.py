"""Strict real-diode stream-out and unchanged full available deck, after routing."""
from pathlib import Path
from collections import Counter
import datetime,json,os,subprocess,sys,xml.etree.ElementTree as ET
from run_exports import ROOT,IMAGE,sha

DRIVER=Path(__file__).resolve().parent


def run(revision,physical_revision,source_kind='diode'):
    assert source_kind in ['diode','cap','incremental']
    physical_root={'diode':'antenna_diode_eco','cap':'diode_cap_eco','incremental':'antenna_incremental_eco'}[source_kind]
    source=ROOT/physical_root/physical_revision/'gemm-C'
    out=ROOT/'antenna_diode_stream'/revision/'gemm-C';out.mkdir(parents=True,exist_ok=False)
    p=source/'execution.json';receipt=json.loads(p.read_text())
    record={'scope':'REAL_DIODE_ECO_STRICT_GDS_AND_UNCHANGED_AVAILABLE_RULES_NOT_COMPLETE_SIGNOFF',
      'source_receipt':str(p),'source_receipt_SHA':sha(p),'full_qualification':False,'source_kind':source_kind,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'available_deck_findings':None,
      'original_available_deck_findings':1460,'missing_SRAM_geometry_fabricated':False}
    if not receipt.get('completed_utc') or not (source/'routed.def').exists():
        record['status']='NOT_EXECUTED_NO_COMPLETED_REAL_DIODE_ROUTE'
        (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');return 1
    deffile=source/'routed.def';assert sha(deffile)==receipt['files'][deffile.name]['sha256']
    if source_kind=='diode':
        source_contract=(receipt.get('original_functional_instances_pose_and_terminal_contract_unchanged')
          and all(receipt.get('unchanged_geometry',{}).get(k) for k in ['pins','pdn','die'])
          and receipt.get('separate_diode_cost',{}).get('inserted_real_ANTENNA_X1')==636)
    elif source_kind=='cap':
        source_contract=(receipt.get('all_original_signal_terminal_and_port_graph_equal_with_exact_two_proven_sizes')
          and all(receipt.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
          and receipt.get('retained_real_diode_count')==636)
    else:
        source_contract=(receipt.get('all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads')
          and receipt.get('all_prior_functional_and_636_diode_poses_and_terminals_unchanged')
          and all(receipt.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
          and receipt.get('actual_total_real_diodes')==658)
    if not source_contract:
        record['status']='NOT_EXECUTED_SOURCE_CONTRACT_FAILED_OR_UNVERIFIED'
        (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');return 1
    previous=ROOT/'streamout/costed-r02/gemm-C_ECO/input.json';old=json.loads(previous.read_text())
    spec={'def':str(deffile),'top':old['top'],'lefs':old['lefs'],'source_clean_execution':str(p)}
    (out/'input.json').write_text(json.dumps(spec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    merge=common+['--env','PINXY_STREAM_OUT='+str(out),IMAGE,'klayout','-b','-r',str(DRIVER/'streamout_probe.py')]
    record.update({'merge_command':merge,'source_DEF_SHA':sha(deffile),'original_stream_inputs_SHA':sha(previous),
      'strict_allow_empty':'DISABLED','same_explicit_LEF_dependencies':True,
      'source_native_DRC_count':receipt.get('fresh_DRC_count'),'source_whole_geometry':receipt.get('whole_signal_geometry')})
    with (out/'merge.log').open('x') as f:record['merge_returncode']=subprocess.run(merge,stdout=f,stderr=subprocess.STDOUT).returncode
    if (out/'diagnostic.gds').exists():
        deck='/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'
        drc=common+[IMAGE,'klayout','-b','-rd','in_gds='+str(out/'diagnostic.gds'),'-rd','report_file='+str(out/'diagnostic.lyrdb'),'-r',deck]
        record['DRC_command']=drc
        with (out/'drc.log').open('x') as f:record['DRC_returncode']=subprocess.run(drc,stdout=f,stderr=subprocess.STDOUT).returncode
        if record['DRC_returncode']==0 and (out/'diagnostic.lyrdb').exists():
            categories=Counter()
            for event,element in ET.iterparse(str(out/'diagnostic.lyrdb'),events=['end']):
                if element.tag=='item':categories[element.findtext('category','UNKNOWN')]+=1;element.clear()
            record['available_deck_findings']=sum(categories.values());record['available_deck_findings_by_category']=dict(categories)
    record['source_receipt_and_DEF_unchanged']=sha(p)==record['source_receipt_SHA'] and sha(deffile)==record['source_DEF_SHA']
    record['status']='STRICT_GDS_AND_AVAILABLE_DECK_COMPLETED_NOT_FULL_QUALIFICATION'
    record['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file()}
    (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if record.get('merge_returncode')==record.get('DRC_returncode')==0 and record['available_deck_findings']==0 else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:4]))
