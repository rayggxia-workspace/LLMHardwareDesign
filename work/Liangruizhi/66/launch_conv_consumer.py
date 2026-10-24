from runner import *
conv='project/experiments/scale_state/conv.py'
stage('phase3',[conv],{'conv_sha256':sha(REPO/conv)})
submit('conv01','phase3',conv,['--capture',REMOTE+'/capture01','--binding',REMOTE+'/phase3/binding.json','--out',REMOTE+'/conv01'])
submit('conv02','phase3',conv,['--capture',REMOTE+'/capture01','--binding',REMOTE+'/phase3/binding.json','--out',REMOTE+'/conv02'])
consumer='project/experiments/scale_state/consumer.py'
stage('phase4',[consumer],{'consumer_sha256':sha(REPO/consumer)})
submit('consumer01','phase4',consumer,['--input',REMOTE+'/capture01','--binding',REMOTE+'/phase4/binding.json','--out',REMOTE+'/consumer01'],minutes=30)
submit('consumer02','phase4',consumer,['--input',REMOTE+'/capture01','--binding',REMOTE+'/phase4/binding.json','--out',REMOTE+'/consumer02'],minutes=30)
