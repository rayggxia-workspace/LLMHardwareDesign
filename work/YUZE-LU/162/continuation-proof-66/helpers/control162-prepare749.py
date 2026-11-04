from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-phase727.py').read_text(encoding='utf-8').replace('import subprocess,shlex,json,time','import subprocess,shlex,json,time,sys')
s=s.replace("reg=b/'r256-phase-trace-regression-718'","reg=b/'r256-pair-window-regression-736'")
s=s.replace("upper-candidates/7200/route","upper-candidates/SEED/route")
s=s.replace("raw=subprocess.check_output", "q=q.replace('/SEED/','/'+str(int(sys.argv[1]))+'/')\nraw=subprocess.check_output",1)
s=s.replace("'control162-phase727'","'control162-phase749'").replace("selected=d['phases'][:2]","selected=d['phases'][:1],seed=int(sys.argv[1])")
s=s.replace("d=json.loads(raw);out=", "d=json.loads(raw);d['candidate']=int(sys.argv[1]);d['route_root']='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates/'+sys.argv[1]+'/route';raw=(json.dumps(d)+'\\n').encode();out=")
s=s.replace("out.mkdir(exist_ok=True);", "out=out/sys.argv[1];out.mkdir(parents=True,exist_ok=True);")
compile(s,'phase749','exec');(p/'control162-phase749.py').write_bytes(s.encode())
