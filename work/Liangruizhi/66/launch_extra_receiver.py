from runner import *
extra='project/experiments/scale_state/receive_state_extra.py';main='project/experiments/scale_state/receive_state.py'
stage('phase11',[extra,main],{'receive_state_extra_sha256':sha(REPO/extra),'receive_state_sha256':sha(REPO/main)})
submit('receive-extra01','phase11',extra,['--capture',REMOTE+'/capture01','--conv',REMOTE+'/conv01','--conv-repeat',REMOTE+'/conv02','--coupled',REMOTE+'/coupled01','--coupled-repeat',REMOTE+'/coupled02','--legacy',REMOTE+'/legacy01','--long',REMOTE+'/long-state01','--long-repeat',REMOTE+'/long-state02','--out',REMOTE+'/receive-extra01','--binding',REMOTE+'/phase11/binding.json'],minutes=30)
