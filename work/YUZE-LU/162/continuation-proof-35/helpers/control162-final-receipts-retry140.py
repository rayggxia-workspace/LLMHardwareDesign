"""Append an unchanged final acceptance only after a proven receipt-I/O race.

Never edit original queued work, bypass a gate, retry a physical failure, or
grant qualification here. All acceptance checks run again in the Slurm task.
"""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');appended=[]
for record_name in ['s-ready-upper-source140.json','s-ready-capacity-upper-source140.json','s-ready-capacity-refill-source140.json','s-ready-cap-proof141-refill-source140.json','s-ready-congestion-source142.json','s-ready-congestion-followup-source142.json','s-ready-halo-routes-source142.json','s-ready-cache-source143.json','s-ready-cache-refill-source143.json','s-ready-history-product-source144.json','s-ready-history-product-refill-source144.json','s-ready-segment-source145.json','s-ready-openroad-source156.json','s-ready-openroad-halo-source156.json','s-ready-openroad-source157.json','s-ready-internal-channel-openroad-source157.json']:
 record=b/'route-selection-102'/record_name
 if not record.exists():continue
 selection=json.loads(record.read_text());assert selection['source']in ['source-140','source-142','source-143','source-144','source-145','source-156','source-157']and selection['selected_adapter_candidate']==1391
 for row in selection['tasks']:
  spec=row['spec'];args=spec['args']
  if spec['script']!='system_geometry.py'or'--acceptance'not in args:continue
  old=Path(row['path']);assert hashlib.sha256(old.read_bytes()).hexdigest()==row['sha256']
  folder=Path(args[args.index('--out')+1]);receipt=folder/'receipt.json'
  if not receipt.exists():continue
  if json.loads(receipt.read_text()).get('passed'):continue
  name=old.stem;queue=old.parent.parent;result=queue/'results'/(name+'.json');log=queue/(name+'.log')
  if not result.exists()or json.loads(result.read_text()).get('returncode')!=1 or not log.exists():continue
  text=log.read_text();config=Path(args[args.index('--acceptance')+1]);cfg=json.loads(config.read_text())
  missing=[Path(p)/'receipt.json'for p in cfg['timing'].values()if "FileNotFoundError"in text and str(Path(p)/'receipt.json')in text]
  if len(missing)!=1:continue
  # Only retry a missing-final-receipt race whose real final receipt was
  # completed after that failed acceptance. Numerical/geometry failures stay.
  if not missing[0].exists()or missing[0].stat().st_mtime<receipt.stat().st_mtime:continue
  ready=True;proofs={}
  for corner,path in cfg['timing'].items():
   p=Path(path)/'receipt.json'
   if not p.exists():ready=False;break
   r=json.loads(p.read_text())
   if not all(r.get(k)for k in ['execution_passed','actual_upper_distributed_research_rc','research_composed_timing_passed','native_coverage_audit_passed','typed_native_timing_passed']):ready=False;break
   if r.get('rc_variant')!=corner:ready=False;break
   audit=Path(path)/'native-system-audit.json'
   if not audit.exists()or not json.loads(audit.read_text()).get('passed'):ready=False;break
   if r['outputs']['native-system-audit.json']!=hashlib.sha256(audit.read_bytes()).hexdigest():ready=False;break
   proofs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  if not ready:continue
  out=folder.with_name('delivery-after-final-receipts');new=old.with_name(name+'-after-final-receipts.json');record_out=out.parent/'final-receipt-race-retry.json'
  if record_out.exists():continue
  assert not new.exists()and not out.exists()
  args=list(args);args[args.index('--out')+1]=str(out);new_spec=dict(spec,args=args)
  temp=new.with_suffix('.tmp');temp.write_text(json.dumps(new_spec));temp.rename(new)
  record_out.write_text(json.dumps(dict(time=time.time(),passed=True,orchestration_only=True,whole_system_qualified=False,original_spec=str(old),original_spec_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),original_failed_receipt=str(receipt),original_failed_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),original_failed_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),new_spec=str(new),new_spec_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),completed_actual_timing_receipts=proofs,all_acceptance_math_and_gates_unchanged=True),indent=2));appended.append(str(new))
print(json.dumps(dict(appended=appended,scope='Exact missing-final-timing-receipt I/O race only; no physical or numerical failure bypassed; no qualification granted.')))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
