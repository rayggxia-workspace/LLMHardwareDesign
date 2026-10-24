from runner import *
e='project/experiments/scale_state/receive_norm.py'
stage('phase14',[e],{'receive_norm_sha256':sha(REPO/e)})
submit('receive-norm01','phase14',e,['--capture',REMOTE+'/capture01','--consumer',REMOTE+'/consumer01','--integer',REMOTE+'/norm03','--repeat',REMOTE+'/norm04','--out',REMOTE+'/receive-norm01.json','--binding',REMOTE+'/phase14/binding.json'],minutes=30)
