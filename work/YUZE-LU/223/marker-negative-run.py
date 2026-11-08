import pathlib,shutil,subprocess,json,hashlib
r=pathlib.Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-223-mother-backend');base=r/'marker-negative01';audit=r/'eco04/acceptance23';script=r/'eco04/project/experiments/mother_control_v1/native_marker_gds.py';gds=r/'eco04/candidate0/flow/results/nangate45/mother_control_64/base/6_final.gds'
row=(audit/'marker-input.tsv').read_text().splitlines()[0].split('\t');index=row[0];shapes=[x.split('\t') for x in (audit/'marker-shapes.tsv').read_text().splitlines() if x.split('\t')[0]==index];assert shapes
results=[]
for name in ['missing_same_net_route','missing_actual_gds']:
 out=base/name;out.mkdir();shutil.copyfile(audit/'native-drc.rpt',out/'native-drc.rpt')
 inputrow=row[:];outs=[]
 if name=='missing_actual_gds':
  offset=10000000;inputrow[3:]=[str(int(x)+offset) for x in inputrow[3:]]
  outs=['\t'.join([s[0],*[str(int(x)+offset) for x in s[1:]]]) for s in shapes]
 (out/'marker-input.tsv').write_text('\t'.join(inputrow)+'\n');(out/'marker-shapes.tsv').write_text('\n'.join(outs)+'\n' if outs else '')
 with (out/'run.log').open('w') as log:
  code=subprocess.run(['klayout','-b','-r',str(script),'-rd','GDS='+str(gds),'-rd','DIRECTORY='+str(out)],stdout=log,stderr=subprocess.STDOUT).returncode
 proof=json.loads((out/'marker-proof.json').read_text());p=proof['results'][0];assert code!=0 and not proof['passed']
 if name=='missing_same_net_route':assert not p['same_net_odb_route_fills_entire_marker'] and p['actual_gds_fills_entire_marker']
 else:assert p['same_net_odb_route_fills_entire_marker'] and not p['actual_gds_fills_entire_marker']
 results.append(dict(case=name,expected_rejection=True,exit_code=code,proof_sha256=hashlib.sha256((out/'marker-proof.json').read_bytes()).hexdigest(),checks=p))
(base/'result.json').write_text(json.dumps(dict(schema='mother-filled-marker-negative-controls/1',passed=True,results=results,production_script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),scope='Deliberately invalid isolated proof inputs; no design/database modification'),indent=2)+'\n')
