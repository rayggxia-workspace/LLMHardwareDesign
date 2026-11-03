from pathlib import Path
import os,json
binary='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-359/upper-candidates/4010/route/router'
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=10011:continue
  cmd=(p/'cmdline').read_bytes().decode().split(chr(0))
  if not cmd or cmd[0]!=binary:continue
  memory={k:v.strip()for k,v in(line.split(':',1)for line in(p/'status').read_text().splitlines()if ':'in line)}
  rows.append(dict(pid=int(p.name),input=cmd[1],vmrss_kib=int(memory['VmRSS'].split()[0]),vmhwm_kib=int(memory['VmHWM'].split()[0]),threads=int(memory['Threads'])))
 except(OSError,UnicodeError):pass
mem={k:v.strip()for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
print(json.dumps(dict(rows=rows,node_available_kib=int(mem['MemAvailable'].split()[0]))))
