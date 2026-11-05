import subprocess,shlex
q=r'''import subprocess,json
s=subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True);fields={}
for part in s.split():
 if '='in part:
  k,v=part.split('=',1)
  if k in ['JobId','JobName','UserId','JobState','Reason','NumCPUs','NumNodes','ReqNodeList','ExcNodeList','Partition','TimeLimit','Command','WorkDir','StdOut']:fields[k]=v
print(json.dumps(fields));print(subprocess.check_output(['sinfo','-N','-n','node13,node14,node15,node16,node17,node18,node19,node20,node21,node22,node23,node24,node25,node26','-o','%N %c %t %C'],universal_newlines=True))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
