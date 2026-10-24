from runner import *
entry='project/experiments/scale_state/state.py'
stage('phase5',[entry],{'state_sha256':sha(REPO/entry)})
for name,source in [('state01','capture01'),('state02','capture01'),('legacy-state01','legacy01'),('legacy-state02','legacy01')]:
 submit(name,'phase5',entry,['--root',REMOTE+'/'+source,'--binding',REMOTE+'/phase5/binding.json','--out',REMOTE+'/'+name],minutes=30)
