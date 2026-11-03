import subprocess,shlex
q=r'''import subprocess,json
code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011;cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));\n  if any('r256-composition-453/function/obj/Vcontrol_system' in a for a in cmd):\n   status=dict(x.split(':',1)for x in open(p+'/status').read().splitlines()if ':'in x);stat=open(p+'/stat').read().split();rows.append(dict(pid=n,command=cmd[:4],threads=status.get('Threads'),rss=status.get('VmRSS'),utime_ticks=stat[13],state=stat[2]))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
print(subprocess.check_output(['srun','--jobid=95204','--overlap','-n1','-c1','python3','-c',code],universal_newlines=True))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
