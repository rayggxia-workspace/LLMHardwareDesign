from runner import *
e='project/experiments/scale_state/collect.py'
paths=[e,'project/experiments/scale_state/receive_state.py','project/experiments/scale_state/consumer_receive.py','project/experiments/scale_state/selected_review.py']
stage('phase15',paths,{'collect_sha256':sha(REPO/e)})
submit('collect01','phase15',e,['--root',REMOTE,'--out',REMOTE+'/delivery01','--binding',REMOTE+'/phase15/binding.json'],minutes=30,depends=[90081])
