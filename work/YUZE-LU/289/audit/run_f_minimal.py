"""Independent new-S minimal parent execution; does not overwrite prior attempts."""
import pathlib,subprocess,time,json,sys
root=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');gs=root/'gs';c=gs/'candidate-S-minimal-localv4'
# Dependency wait is bounded and only waits for the already-running qualified leaf.
for _ in range(120):
 if (c/'qualification-v2/physical-receipt.json').exists():break
 time.sleep(15)
else:raise RuntimeError('Leaf qualification not available after 30 minutes')
def run(script,*args):
 print('RUN',script,*args,flush=True);subprocess.run(['python3',str(gs/script),*map(str,args)],check=True)
run('state-preservation-v2.py','S',c)
run('join-leaf.py',c,'S')
run('parent-abstract.py','S',c)
subprocess.run(['python3',str(root/'audit/check_parent_abstract.py'),str(c),'local_s_base',str(root/'audit/S-minimal-localv4-conservatism.json')],check=True)
config=(gs/'candidate-S-hold08-v3/parent-F/config.mk').read_text().replace(str(gs/'candidate-S-hold08-v3'),str(c))
(c/'parent-F').mkdir();(c/'parent-F/config.mk').write_text(config)
run('f-eco-v4.py',c,'h20')
f=c/'parent-F-eco-h20-v4'
run('f-formal.py',f)
run('f-state-preservation.py','F',f)
run('f-qualify.py',f)
print('F_PIPELINE_STAGES_DONE_REQUIRES_INDEPENDENT_AGGREGATION',flush=True)
