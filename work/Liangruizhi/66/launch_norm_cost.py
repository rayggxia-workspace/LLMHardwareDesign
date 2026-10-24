from runner import *
entry='project/experiments/scale_state/norm.py';dep='project/experiments/scale_state/consumer.py'
stage('phase13',[entry,dep],{'norm_sha256':sha(REPO/entry),'consumer_sha256':sha(REPO/dep)})
for name in ('norm03','norm04'):
 submit(name,'phase13',entry,['--capture',REMOTE+'/capture01','--consumer',REMOTE+'/consumer01','--binding',REMOTE+'/phase13/binding.json','--out',REMOTE+'/'+name],minutes=30)
