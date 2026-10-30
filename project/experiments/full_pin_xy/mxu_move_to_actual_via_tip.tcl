# Current native0 M6 source: 24 actual target-net rows, exactly one original
# hold19330/A peer. Existing via5 landing is selected, never a new target layer.
set specs {{act_data[12] metal6 {656370 2137600 656650 2137880} {656930 2177280 657210 2177560} hold19330 A 7}}
set removed [dict create {act_data[12]} {{metal6 656510 2137600 657770 2137880} {metal6 657490 2137600 657770 2139480} {metal6 656930 2139200 657770 2139480} {metal6 656930 2139200 657210 2177560}}]
source [file join [file dirname [info script]] llsys_move_to_actual_via_tips.tcl]
