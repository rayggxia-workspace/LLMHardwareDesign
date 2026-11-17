from pathlib import Path
for p in Path('/proc').glob('[0-9]*'):
 try:
  env=dict(x.split(b'=',1) for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x)
  if env.get(b'SLURM_JOB_ID')==b'119628' and env.get(b'RECOVERY_KIND')==b'U':
   print(p.name,env.get(b'SLURM_STEP_ID'),(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()[:400])
 except (OSError,ValueError):pass
