from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os,sys,subprocess,json,re
from run_exports import ROOT,CFG,IMAGE,BIN,sha
from check_access import check
DRIVER=Path(__file__).resolve().parent
def one(case,rev,plan):
    original=ROOT/'trials'/rev/(case+'-'+plan);trial=original/'execution.json'
    if not trial.exists():print('NOT_READY',original,flush=True);return
    j=json.loads(trial.read_text())
    if not j.get('finished_utc'):print('TRIAL_STILL_RUNNING',original,flush=True);return
    src=Path(CFG['physical_blocks'][case]['odb']) if plan=='A' else original/'routed.odb'
    if not src.exists():print('NO_COMPLETED_ROUTE',original,flush=True);return
    out=ROOT/'finalized'/rev/(case+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    env=dict(item.split('=',1) for item in j['command'][j['command'].index('--env')+1].split(','))
    relocations=env['PINXY_RELOCATIONS'];before=sha(src)
    en='PINXY_ODB={},PINXY_FINAL_OUT={},PINXY_RELOCATIONS={},PINXY_DRIVER={}'.format(src,out,relocations,DRIVER)
    common=['singularity','exec','--cleanenv','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro','--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    with (out/'export.log').open('x') as f:r=subprocess.run(common+['--env',en,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'finalize_clean.tcl')],stdout=f,stderr=subprocess.STDOUT)
    rec={'case':case,'revision':rev,'plan':plan,'source_pre_RCX_odb':str(src),'source_sha256':before,'source_unchanged':before==sha(src),'export_returncode':r.returncode,
        'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
        'rejected_post_RCX_geometry_odb':str(original/('analysis_after_RCX.odb' if (original/'analysis_after_RCX.odb').exists() else 'checked.odb')),'legacy_RC_STA_receipt':str(trial),'RC_STA_scope':'Existing SPEF/STA executed from this same pre-RCX source; post-RCX DB rejected as physical master. System boundary models incomplete.'}
    if (out/'clean.odb').exists():
        rec['clean_odb_sha256']=sha(out/'clean.odb');rec['clean_byte_identical_to_pre_RCX_source']=rec['clean_odb_sha256']==before
        expected=j.get('outputs',{}).get('routed.odb',{}).get('sha256') if plan!='A' else CFG['physical_blocks'][case]['expected_sha256']
        assert expected==before,'Routed source lineage mismatch'
        den='PINXY_DRC_ODB={},PINXY_TOP_LAYER={},PINXY_DRC_OUT={}'.format(out/'clean.odb',8 if case.endswith('_aux') else 10,out/'independent.drc')
        with (out/'drc.log').open('x') as f:d=subprocess.run(common+['--env',den,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'independent_drc.tcl')],stdout=f,stderr=subprocess.STDOUT)
        drc=out/'independent.drc';rec['independent_DRC_returncode']=d.returncode;rec['independent_DRC_count']=len(re.findall(r'^violation type:',drc.read_text(),re.M)) if drc.exists() else None
    for name,whole in [('selected_access',False),('whole_access',True)]:
        if r.returncode==0:
            result=check(out/(name+'.tsv.gz'),whole);(out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');rec[name]=result
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('CLEAN_FINALIZED',case,rev,plan,rec.get('independent_DRC_count'),rec.get('whole_access',{}).get('pass'),flush=True)
def safe(args):
    try:one(*args)
    except Exception:
        import traceback;traceback.print_exc()
if __name__=='__main__':
    case,rev=sys.argv[1:3];plans=sys.argv[3:] or ['A','A_replay','Aopt','B','C']
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(safe,[(case,rev,p) for p in plans]))
