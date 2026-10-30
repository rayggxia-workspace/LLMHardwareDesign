"""Publish only completed model exports or explicit failures, with raw SHA evidence."""
from pathlib import Path
import datetime,gzip,json,shutil,sys,tarfile
from run_exports import ROOT,sha

name=sys.argv[1];assert name.replace('-','').isalnum()
out=ROOT/'timing_model_snapshots'/name;out.mkdir(parents=True,exist_ok=False)
records=[]
for directory in sorted((ROOT/'leaf_timing_models').glob('*/*')):
    execution=directory/'execution.json';failure=directory/'driver_failure.json'
    j=json.loads(execution.read_text()) if execution.exists() else {}
    if not j.get('finished_utc') and not failure.exists():continue
    destination=out/directory.relative_to(ROOT/'leaf_timing_models');destination.mkdir(parents=True)
    for p in directory.iterdir():
        if not p.is_file():continue
        if p.suffix in ['.lib','.tsv','.txt','.log']:
            with (destination/(p.name+'.gz')).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(p.read_bytes())
        elif p.suffix in ['.json','.tcl']:shutil.copyfile(p,destination/p.name)
    libtext=(directory/'timing.lib').read_text() if (directory/'timing.lib').exists() else ''
    records.append({'model':directory.relative_to(ROOT/'leaf_timing_models').as_posix(),'source_directory':str(directory),
      'source_execution_sha256':sha(execution) if execution.exists() else None,'actual_receipt':j,
      'driver_failure':json.loads(failure.read_text()) if failure.exists() else None,
      'native_model_features_textual_presence_only':{key:key in libtext for key in ['minimum_period','max_capacitance','max_transition','setup_rising','hold_rising']},
      'qualified_for_full_system_STA':False,'reason':'Native extracted research model; boundary drive/load/slew and SRAM device/model qualifications incomplete. Leaf internal failures/minimum-period coverage remain separate.'})
(out/'summary.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Completed model exports or explicit driver failures only. Not characterized signoff libraries; active exports omitted, never passed.',
 'records':records},indent=2)+'\n')
with tarfile.open(str(out)+'.tar.gz','x:gz') as tar:tar.add(str(out),arcname=name)
print('TIMING_MODEL_SNAPSHOT',str(out)+'.tar.gz',len(records),'completed/failure records')
