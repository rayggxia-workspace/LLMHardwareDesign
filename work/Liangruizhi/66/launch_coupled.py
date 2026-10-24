from runner import *
entry='project/experiments/scale_state/state.py'
stage('phase6',[entry],{'state_sha256':sha(REPO/entry)})
for name in ('coupled01','coupled02'):
 submit(name,'phase6',entry,['--root',REMOTE+'/capture01','--binding',REMOTE+'/phase6/binding.json','--conv',REMOTE+'/conv01','--only-coupled','--out',REMOTE+'/'+name],minutes=30)
