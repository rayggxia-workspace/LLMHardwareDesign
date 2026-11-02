"""Verify committed A8 provenance and complete real-server CASE evidence; no RTL run."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path

def fingerprint(p):
 raw=p.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root.resolve();w=r/'work/Melodydt/151';e=w/'a8-rtl-evidence';checks=0
 def ck(value,message):
  nonlocal checks
  checks+=1
  if not value:raise AssertionError(message)
 index=json.loads((w/'a8-execution-index.json').read_text(encoding='utf8'))
 for row in index['final_files']+index['raw_evidence_files']:
  ck(fingerprint(r/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path'])
 for row in json.loads((w/'a8-inherited-source-lock.json').read_text())['unchanged_files']:
  ck(fingerprint(r/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},'inherited '+row['path'])
 lock=json.loads((w/'phase2-source-lock.json').read_text());ck(len(lock['core_files'])==14,'native14')
 for row in lock['core_files']:
  ck(fingerprint(r/row['path'])['sha256']==row['sha256'],'native lock '+row['path'])
 receipt=json.loads((e/'runs/r04/results/run-receipt.json').read_text())
 ck(receipt['status']=='PASS_REAL_VERILATOR_RTL_DECLARED_CASES','actual success')
 ck(receipt['slurm']['SLURM_JOB_ID']=='95116' and receipt['slurm']['SLURM_CPUS_PER_TASK']=='8','actualSlurm')
 baseline=json.loads((w/'a8-verilator-baseline-contract.json').read_text());profiles=baseline['profiles'];profiles['a8']=json.loads((w/'a8-verilator-profile-contract.json').read_text())
 spec=importlib.util.spec_from_file_location('a8_runner',str(w/'run_a8_verilator.py'));runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 for item in receipt['profiles']:
  key=item['profile'];contract=profiles[key];log=(e/'runs/r04/logs'/('simulate-'+key+'.log')).read_text()
  parsed=runner.parse_output(log,contract['expected_case_ids'],contract['pass_marker'],0)
  ck(parsed['passed'] and parsed['summary_case_count']=={'n':29,'f8':25,'a8':26}[key],'completeCASE '+key)
  ck(parsed==item['output_check'],'independentparse '+key)
 for command in receipt['commands']:
  ck(command['exit_code']==0,'command exit '+command['label'])
  ck(fingerprint(e/'runs/r04'/command['log'])['sha256']==command['log_fingerprint']['sha256'],'logSHA '+command['label'])
 for source in receipt['inputs']:
  if source.get('snapshot'):
   relative=source['path']
  elif '/input-r04/' in source['path']:relative=source['path'].split('/input-r04/',1)[1]
  else:continue
  ck(fingerprint(r/relative)['sha256']==source['sha256'],'executed source '+relative)
 for tool in ['verilator','verilator_bin']:
  ck(receipt['tools'][tool]['sha256']==receipt['tools'][tool]['after_fingerprint']['sha256'],'toolstable '+tool)
 ck(sum(x['count'] for x in receipt['compiler_warnings'])==98,'warning98 retained')
 ck(receipt['warning_policy']=={'nonfatal':True,'suppressed_warning_categories':[],'lint_clean_claim':False},'warning policy')
 ck(all('-Wno-fatal' in x['argv'] and '--assert' in x['argv'] and '--timing' in x['argv'] for x in receipt['commands'] if x['label'].startswith('build-')),'no assert/timing removal')
 account=(e/'exports/c02/accounting-95116.txt').read_text().splitlines()[0].split('|')
 ck(account[0]=='95116' and account[2]=='COMPLETED' and account[3]=='0:0' and account[5]=='8','terminalaccounting')
 result={'status':'PASS_PROVENANCE_AND_SERVER_EVIDENCE_NOT_NEW_RTL_EXECUTION','checks':checks,'server_job':95116,'case_counts':{'N':29,'F8':25,'A8':26},'new_RTL_simulation_in_this_checker':False,'lint_clean':False,'complete_A_L4_physical':False}
 (w/'a8-verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf8'))
 print('PASS {} source/log/tool/completeCASE evidence checks; no simulator invoked'.format(checks))
if __name__=='__main__':main()
