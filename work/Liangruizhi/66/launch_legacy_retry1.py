from runner import *
entry='project/experiments/scale_state/export_legacy_state.py'
b=stage('phase1b',[entry],{'source_sha256':sha(REPO/entry)})
submit('legacy01','phase1b',entry,['--input',PREV+'/input/qwen35-states.pt.gz','--binding',REMOTE+'/phase1b/binding.json','--out',REMOTE+'/legacy01'])
