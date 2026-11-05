import subprocess,shlex
q="import subprocess;print(subprocess.check_output(['sinfo','-N','-n','node1,node2,node3,node4,node5,node6,node7,node8,node9,node10,node11,node12','-o','%N %c %t %C'],universal_newlines=True))"
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
