from runner import *
entry='project/experiments/scale_state/capture_qwen35.py'
stage('phase2b',[entry])
submit('capture01','phase2b',entry,['--root',PREV,'--binding',REMOTE+'/phase2b/binding.json','--threads','24','--out',REMOTE+'/capture01'],cpus=24,minutes=30)
