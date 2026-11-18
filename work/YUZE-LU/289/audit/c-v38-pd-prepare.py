from pathlib import Path
import re
here=Path(__file__).parent
t=(here/'c-trace-size-v2.tcl').read_text()
t=t.replace('C-v28-actual-i8-h50','C-v38-close-y640-h50')
start=t.index('set pf [open $cu/c-v28-combined-size-plan.tsv]');end=t.index('set b [ord::get_db_block]',start);t=t[:start]+t[end:]
t=t.replace('$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/isolated.spef','$src/6_final.spef')
t=t.replace('[get_ports trace_retire_o]','[get_pins {memory_service.actor2.loader.pd[0][94]$_DFFE_PP_/D}]')
t=t.replace('$nh >= $bh-0.000001','$nh >= $bh-0.000000001 && $nh >= 0 && $nhn == 0 && $nc == 0 && $ns == 0')
t=t.replace(' || $trial-$round_start_trial>=64','')
start=t.index(' set main {};set other {}');end=t.index(' set round_start_trial',start)
t=t[:start]+''' set ranked {};set rest $todo
 foreach n $priority {
  if {$n in $todo} {lappend ranked $n;set idx [lsearch -exact $rest $n];set rest [lreplace $rest $idx $idx]}
 }
 set todo [concat $ranked $rest]
'''+t[end:]
t=t.replace('source choices.tcl','source choices.tcl\nsource priority.tcl')
t=t.replace('set baseline [metrics];','set baseline [metrics];lassign $baseline bw bt bc bs bn bh bht bhn btarget;if {$bc!=0 || $bs!=0 || $bhn!=0 || $bh<0} {error "Source no longer electrical/hold clean"};')
(here/'c-v38-pd-size.tcl').write_text(t)
m=(here/'c-trace-size-models-v2.py').read_text().replace('C-v27-joint-e20-h30','C-v38-close-y640-h50').replace("['C-v28-cell-preflight','C-v29-cell-preflight']","['C-v28-cell-preflight','C-v29-cell-preflight','C-trace-AOI221X4-fixture','C-trace-additional-fixture','C-v38-all-master-fixture']")
(here/'c-v38-pd-models.py').write_text(m)
v=(here/'c-trace-size-verify-v2.py').read_text().replace('target_trace_slack','target_pd94_slack').replace(' Source baseline already includes frozen 59-instance plan; exploratory AOI221_X4 requires original-library fixture acceptance.',' Source is exact C38 y640-h50 routed ODB/SPEF; no prior ECO plan replayed.')
v += '\nassert final[2]==0 and final[3]==0 and final[7]==0 and final[5]>=0 and final[5]>=base[5]-1e-9\n'
(here/'c-v38-pd-verify.py').write_text(v)
