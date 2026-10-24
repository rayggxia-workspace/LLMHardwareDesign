from runner import *
entry='project/experiments/scale_state/receive_state.py'
stage('phase9',[entry])
submit('receive-state01','phase9',entry,['--capture',REMOTE+'/capture01','--integer',REMOTE+'/state01','--repeat',REMOTE+'/state02','--out',REMOTE+'/receive-state01'],minutes=30)
