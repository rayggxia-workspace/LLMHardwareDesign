from pathlib import Path
p=Path(__file__).parent;s=(p/'synth-original.tcl').read_text(encoding='utf-8')
a='  log_cmd abc {*}$abc_args';b='  set cec_saved_pwd [pwd]\n  cd $::env(CEC_REPLAY_DIR)\n  log_cmd abc -nocleanup -showtmp {*}$abc_args\n  cd $cec_saved_pwd'
assert s.count(a)==1
(p/'synth-cec-byte-fixed.tcl').write_text(s.replace(a,b),encoding='utf-8')
assert s.replace(a,b).replace(b,a)==s
