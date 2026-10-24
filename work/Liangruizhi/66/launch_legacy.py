from runner import *
entry='project/experiments/scale_state/export_legacy_state.py'
b=stage('phase1',[entry],{'source_sha256':sha(REPO/entry)})
submit('legacy01','phase1',entry,['--input',PREV+'/input/qwen35-states.pt.gz','--binding',REMOTE+'/phase1/binding.json','--out',REMOTE+'/legacy01'])
