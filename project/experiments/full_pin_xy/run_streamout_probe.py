"""Strict baseline/full ACT stream-out and unmodified available DRC deck.

Missing memory GDS remains a failed merge; any DRC is diagnostic only then.
Never suppress missing cells or turn off FEOL/BEOL/antenna/off-grid checks.
"""
import datetime,json,os,re,subprocess,sys
from pathlib import Path
from run_exports import ROOT,CFG,IMAGE,sha
from run_trials import config_values
DRIVER=Path(__file__).resolve().parent
rev=sys.argv[1];case=sys.argv[2] if len(sys.argv)>2 else 'act'
baseline_rev={'act':'r02','gemm':'r01','mxu':'r03','vector':'r04','opentpu_aux':'r03','llaccel_aux':'r03'}[case]
c_rev='fullC-r02' if case=='act' else 'r01' if case=='gemm' else 'grid-r05'
for plan,source in [('A',ROOT/'finalized'/baseline_rev/(case+'-A')),('C',ROOT/'finalized'/c_rev/(case+'-C'))]:
    out=ROOT/'streamout'/rev/(case+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    source_config=Path(CFG['physical_blocks'][case]['odb']).parents[5]/('vec-config.mk' if case=='vector' else 'config.mk')
    values=config_values(source_config)
    platform='/OpenROAD-flow-scripts/flow/platforms/nangate45'
    lefs=[platform+'/lef/NangateOpenCellLibrary.tech.lef',platform+'/lef/NangateOpenCellLibrary.macro.mod.lef']+values.get('ADDITIONAL_LEFS','').split()
    deffile=source/'clean.def';top=re.search(r'^DESIGN\s+(\S+)\s*;',deffile.read_text(),re.M).group(1)
    (out/'input.json').write_text(json.dumps({'def':str(deffile),'top':top,'lefs':lefs,'source_clean_execution':str(source/'execution.json')},indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro','--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    cmd=common+['--env','PINXY_STREAM_OUT='+str(out),IMAGE,'klayout','-b','-r',str(DRIVER/'streamout_probe.py')]
    rec={'plan':plan,'case':case,'source_clean_execution':str(source/'execution.json'),'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'merge_command':cmd,'source_clean_execution_sha256':sha(source/'execution.json')}
    with (out/'merge.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    rec['merge_returncode']=r.returncode
    rec['missing_GDS_cells']=re.findall(r"LEF Cell '([^']+)' has no matching GDS",(out/'merge.log').read_text())
    if (out/'diagnostic.gds').exists():
        drc=common+[IMAGE,'klayout','-b','-rd','in_gds='+str(out/'diagnostic.gds'),'-rd','report_file='+str(out/'diagnostic.lyrdb'),'-r',platform+'/drc/FreePDK45.lydrc']
        rec['DRC_command']=drc
        with (out/'drc.log').open('x') as f:d=subprocess.run(drc,stdout=f,stderr=subprocess.STDOUT)
        rec['DRC_returncode']=d.returncode
    rec['status']='DIAGNOSTIC_ONLY; missing views or full-rule/parent/system qualification still separate'
    rec['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('STRICT_STREAM_PROBE',plan,rec['merge_returncode'],rec['missing_GDS_cells'],flush=True)
