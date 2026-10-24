from runner import *
entry='project/experiments/scale_state/capture_qwen35.py'
stage('phase2',[entry])
submit('capture01','phase2',entry,['--root',PREV,'--binding',REMOTE+'/phase2/binding.json','--threads','24','--out',REMOTE+'/capture01'],cpus=24,minutes=30)
