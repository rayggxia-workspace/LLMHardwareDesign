from runner import *
entry='project/experiments/scale_state/norm.py';dep='project/experiments/scale_state/consumer.py'
stage('phase12',[entry,dep],{'norm_sha256':sha(REPO/entry),'consumer_sha256':sha(REPO/dep)})
for name in ('norm01','norm02'):
 submit(name,'phase12',entry,['--capture',REMOTE+'/capture01','--consumer',REMOTE+'/consumer01','--binding',REMOTE+'/phase12/binding.json','--out',REMOTE+'/'+name],minutes=30)
