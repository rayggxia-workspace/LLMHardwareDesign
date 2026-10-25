import argparse,json,subprocess,sys
from pathlib import Path
from inputs import put,sha
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--stall',type=int,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);cases=json.loads((a.fixtures/'fixtures.json').read_text());results=[]
for c in cases:
 inp=Path(c['input_path']);assert sha(inp/'manifest.json')==c['manifest_sha256'];run=a.out/(c['name']+'-run');recv=a.out/(c['name']+'-recv')
 for argv in [[sys.executable,str(P/'run.py'),'sim','--out',str(run),'--input',str(inp),'--build',str(a.build),'--steps','1','--stall',str(a.stall),'--mode','fixture'],[sys.executable,str(P/'verify.py'),'--run',str(run),'--input',str(inp),'--out',str(recv)]]:
  x=subprocess.run(argv,text=True,capture_output=True);(a.out/(c['name']+('-sim.log'if'run.py'in argv[1]else'-recv.log'))).write_text(x.stdout+x.stderr,encoding='utf8',newline='\n');assert x.returncode==0,(c['name'],x.stderr)
 r=json.loads((recv/'receipt.json').read_text());results.append({'name':c['name'],'expected_status':c['expected_status'],'receipt_sha256':sha(recv/'receipt.json'),'status':r['status'],'final':r['final'],'stage_pairs_checked':r['stage_pairs_checked']})
put(a.out/'receipt.json',{'schema':'gdn104-boundaries-v1','status':'PASS_ALL_FULL_GROUP_BOUNDARIES','stall':a.stall,'fixtures_sha256':sha(a.fixtures/'fixtures.json'),'cases':results});print('PASS_ALL_FULL_GROUP_BOUNDARIES',len(results))
