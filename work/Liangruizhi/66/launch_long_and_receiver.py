from runner import *
entry='project/experiments/scale_state/receive_conv.py'
stage('phase7',[entry])
submit('receive-conv01','phase7',entry,['--capture',REMOTE+'/capture01','--root',REMOTE,'--out',REMOTE+'/receive-conv01'],minutes=20)
state='project/experiments/scale_state/state.py'
stage('phase8',[state],{'state_sha256':sha(REPO/state)})
for name in ('long-state01','long-state02'):
 submit(name,'phase8',state,['--root',REMOTE+'/legacy01','--binding',REMOTE+'/phase8/binding.json','--steps','256','--out',REMOTE+'/'+name],minutes=30)
