from runner import *
entry='project/experiments/scale_state/consumer_receive.py'
stage('phase10',[entry])
submit('receive-consumer01','phase10',entry,['--capture',REMOTE+'/capture01','--input',REMOTE,'--out',REMOTE+'/receive-consumer01.json','--negative-dir',REMOTE+'/receive-consumer-negative01'],minutes=30)
