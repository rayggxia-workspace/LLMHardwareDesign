from pathlib import Path
p=Path(__file__).parent;s=(p/'synth-original.tcl').read_text(encoding='utf-8')
marker='# Technology mapping of flip-flops';assert s.count(marker)==1;s=s.replace(marker,'write_json $::env(CEC_REPLAY_DIR)/before-dff.json\n'+marker)
marker='}\nopt\n\n# Replace undef values with defined constants';assert s.count(marker)==1;s=s.replace(marker,'}\nwrite_json $::env(CEC_REPLAY_DIR)/after-dff.json\nopt\n\n# Replace undef values with defined constants')
marker='  log_cmd abc {*}$abc_args';assert s.count(marker)==1
s=s.replace(marker,'  write_json $::env(CEC_REPLAY_DIR)/pre-abc.json\n  set cec_saved_pwd [pwd]\n  cd $::env(CEC_REPLAY_DIR)\n  log_cmd abc -nocleanup -showtmp {*}$abc_args\n  cd $cec_saved_pwd\n  write_json $::env(CEC_REPLAY_DIR)/post-abc.json')
(p/'synth-cec.tcl').write_text(s,encoding='utf-8')
