import pathlib,tarfile,hashlib,json,subprocess
root=pathlib.Path(__file__).resolve().parent
files=[]
for pattern in ('*.py','*.sbatch','*.json','*.log','C-v2/*.rpt','C-v2/*.log','U-v2/*.rpt','U-v2/*.log','v4/*/*.rpt','v4/*/*.tsv','v4/*/*.log','v4/*/*.tcl','v4/run-status.json'):
 files.extend(root.glob(pattern))
files=sorted(set(files))
(root/'jobs.psv').write_text(subprocess.check_output(['sacct','-j','119508,119509,119510,119511,119512,119513,119514,119515','--format=JobID,JobName,Partition,AllocCPUS,Elapsed,State,ExitCode','-P'],universal_newlines=True))
files.append(root/'jobs.psv')
manifest={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
(root/'evidence-index.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(root/'evidence.tar.gz','w:gz') as tar:
 for p in files+[root/'evidence-index.json']:tar.add(p,arcname=str(p.relative_to(root)))
(root/'evidence.tar.gz.sha256').write_text(hashlib.sha256((root/'evidence.tar.gz').read_bytes()).hexdigest()+'  evidence.tar.gz\n')
