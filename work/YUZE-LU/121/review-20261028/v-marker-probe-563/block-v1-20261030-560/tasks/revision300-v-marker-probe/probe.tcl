set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-523/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343239383233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2276320 586880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343330303731}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 800020 905520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343333393338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 969070
odb::dbWireEncoder_addRect $enc 0 0 140 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431333538333732}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 969070
odb::dbWireEncoder_addRect $enc 0 0 140 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431333539393730}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 1165640
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431343033383232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1797520 2205770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431343034333338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1474810 1992830
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313035323635}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 361120 1337840
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313037373135}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1176050 959630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313134343533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 403130 959630
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313139363036}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201520 620130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313230373632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 129910 480830
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313235393536}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1502470 1115030
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313332323737}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1335650 955430
odb::dbWireEncoder_addRect $enc 0 0 70 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313335333530}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1318720 822360
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313339313333}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1398520 532770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313432313233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1833240 550760
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313433313535}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 729470
odb::dbWireEncoder_addRect $enc 0 0 200 60
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313538323234}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 334880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313539383733}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1009610 401030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313635303039}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 720220 855680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313639343239}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464690 716030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313731383435}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 321220 694610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313734353837}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 388310 556430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313737343734}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 480820 477400
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313737373837}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 530880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313738313534}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 556440 675360
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313738343337}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 586530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313739333736}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 476640 595560
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313830353533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 577930 560630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313831353439}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 530050 396830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313832353835}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 663860 401030
odb::dbWireEncoder_addRect $enc 0 0 50 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2417510 401030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 423920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834323834}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435920 414960
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834353935}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2475820 396130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313837303637}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 247800
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313838343137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 148960
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313839363231}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2356120 291690
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313932353435}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2232240 597730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313933353236}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2260190 800030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313938323535}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2236420 855120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313939343334}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2471640 658770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313939353231}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2471640 675640
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323033303338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2276320 497560
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323036333437}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2396020 847000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323039303732}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2316220 987000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323131393930}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2156620 863170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323133383232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 161050 401030
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323134363133}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 302050 321230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323135323738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 416010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323136303135}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 911570 237230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323139333232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 379120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323231303635}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1917220 113680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323232303834}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1358620 440930
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323237343535}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1764670 321230
odb::dbWireEncoder_addRect $enc 0 0 10 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323238363237}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673640 171070
odb::dbWireEncoder_addRect $enc 0 0 140 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323333333130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1598020 115290
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323334383832}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1139570 321230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323433333839}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 121720 389130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323434353435}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1478320 399770
odb::dbWireEncoder_addRect $enc 0 0 60 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1478320 399770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323436393431}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1737690 560630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323438323937}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 518330 1997030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323532313938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1669690 2072630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323535373434}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879820 2277730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323535393636}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 1471120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323630313833}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1020650 1518230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323634363439}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2152440 2170560
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323637363838}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196520 1380120
odb::dbWireEncoder_addRect $enc 0 0 80 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196520 1380120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323731323138}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 919720 2450490
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323733363736}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 1402450
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323738373230}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 873930 636230
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739303135}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 466200
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739303735}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1039420 670530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739363735}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 720220 686770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739383534}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 720220 572040
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323830393132}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 1241520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323838393334}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 396840 131810
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323930363732}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 171070
odb::dbWireEncoder_addRect $enc 0 0 140 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323937303931}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072640 1155840
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323938343434}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2085390 1039430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939383038}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2123780 955430
odb::dbWireEncoder_addRect $enc 0 0 90 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939383334}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2116720 939120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939393830}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1994190 636230
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333031343437}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999520 990290
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333033313637}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 121720 855120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333033343938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440920 1077650
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333035343731}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1075140 2274370
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333130303239}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2031450 2072630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333136343233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1633740 2420040
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333137373030}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 1917720
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333137373930}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1752890 1917230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333337383838}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 413390 1194830
odb::dbWireEncoder_addRect $enc 0 0 10 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333435343032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676140 1302210
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333436323132}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1119220 1188320
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333436383333}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401020 1290240
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333531343934}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 647850 1837430
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333533373232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1035240 1063720
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333536333133}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 157440 1366610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333633353833}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 646710 2156630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333633373737}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317040 2348360
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333635363930}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 368250 2232230
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333735363238}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1904510 1997030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333736323731}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1115040 2165170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333736373638}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 556440 2401210
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333738383539}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401020 2029440
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333833353030}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2010530 1278830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333837393334}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2118450 2316230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333930343239}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1553940 1957480
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333932393034}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 716040 2337160
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343032363634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1957120 2418360
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343034323237}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1558120 2470090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343034383936}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673640 2092090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343131333137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1648410 959630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343131333933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1957120 933730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343135393631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2316220 833000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3535343336}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1833240 2336880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3536343736}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637920 1751960
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3538313333}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 361120 1226610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3538323634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 709850 1115030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3539363530}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 915040
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3631313133}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600520 912170
odb::dbWireEncoder_addRect $enc 0 0 100 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600520 912170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3631323134}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 598070 955430
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3634373036}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1199020 2198490
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3636313038}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1434240 2360610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3636333738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 902420 2391830
odb::dbWireEncoder_addRect $enc 0 0 130 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3732393130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 907770 1115030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3733363139}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 476640 2457840
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3738343032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2211930 1598030
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3739343438}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1285460 2232230
odb::dbWireEncoder_addRect $enc 0 0 130 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3739343836}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 2224320
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3832373331}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1796590 1753430
odb::dbWireEncoder_addRect $enc 0 0 10 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3932323136}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 1565410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3935313932}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1717720 1403570
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3935313936}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1717720 1368920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3937383031}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 640420 2451680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133353935}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2241940 1833230
odb::dbWireEncoder_addRect $enc 0 0 110 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133373830}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2285690 1753430
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3134313737}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2359050 1753430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3134373934}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2396020 1924440
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3135313938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312040 1755880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312090 1755880
odb::dbWireEncoder_addRect $enc 0 0 90 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3135373734}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2403850 1917230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136343337}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2387110 1917230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435920 1795570
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373931}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441070 2152430
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3138323139}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2325550 1598030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3138353632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 2128560
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e32363230}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312040 2462880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e32393534}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2356120 2407720
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34323233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 2191000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34343031}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2475820 2243010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34353238}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2475820 2289560
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e35323631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 2305520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 2305730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e36333735}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342250 1194830
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {24666c617474656e5c5c66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e39303633}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2298570 1119230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {63686f73656e5f69645c5b315c5d5b325d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 321220 872130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f3132395f305f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1301450 161630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f3137305f305f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2320610 157430
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f385f305f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 326810 157430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f323133305f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435920 1288270
odb::dbWireEncoder_addRect $enc 0 0 140 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3237315f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317040 802410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f323733375f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196520 418530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3533305f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 651650 1194830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3733325f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 763370 1119230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f37395f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201520 360010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f38345f636c6b}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 449680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e64656c7461315c5b315c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2396020 2443210
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e66726163315c5b305c5d5b375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2330110 1514030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3130345c5d5b31325d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 455770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3131305c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879820 74410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3133375c5d5b31315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2206990 476630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3134315c5d5b32335d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 223390 161630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3135345c5d5b335d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1329190 77630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3136365c5d5b32385d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 596340 153160
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3138325c5d5b32305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 476640 68600
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3139375c5d5b325d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1496770 157430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3231325c5d5b32315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 823790 81830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3232355c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955440 147490
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3233375c5d5b32355d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 84690 317030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b3234395c5d5b31345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072640 409640
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b32365c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1079320 237090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b34305c5d5b355d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1637370 237230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b34385c5d5b31345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1764290 476630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b35365c5d5b31365d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238920 208600
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b36335c5d5b31315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1717720 367640
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b36385c5d5b32325d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 143210 317030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5c5b39325c5d5b355d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673640 59920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313031313031}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 1410080
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313031373532}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 2159920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313032373038}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 241420 2070530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313032383538}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999520 1741810
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313032383632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1159120 1354080
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313033373835}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1968730 1278830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313034333430}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 490530 2391830
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313034373831}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1072730 1278830
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313034383639}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1395290 2471630
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313034393830}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1159120 2269960
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313035373933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1951630 560630
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313036323632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 243530 2312030
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313036323836}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 918410 1837430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313037303335}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 798330 1677830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313037303638}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 2255120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313037313439}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 371610 1913030
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313037383032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1462190 716030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313038353639}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1282070 401030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313038363337}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1952940 978320
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313038363630}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 438470 241430
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313038373135}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1753440 1718010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313039303034}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1194840 1143450
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313039303933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1038570 2316230
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313039313137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 396840 1363320
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313039373738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1857850 1997030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313130313031}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1459910 1434230
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313130323631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1434240 2336250
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313130333037}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1434240 1126650
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313130383130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 117540 309050
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313131313033}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1173770 1194830
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313131343432}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 709520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313131343835}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1518220 648480
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313131383639}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2136690 1514030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313131383935}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1363010 237230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313132333136}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 596340 80010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313132373938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 2126880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313132393432}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 2065770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133313234}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1125930 157430
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133313839}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 157440 2031680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133323933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2266650 1119230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133333332}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 203000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 203000
odb::dbWireEncoder_addRect $enc 0 0 180 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133353436}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1271810 1035230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133393332}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1606970 556430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313133393538}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2471640 217280
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313134323236}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 682050 716030
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313134353333}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 674830 716030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313134353433}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1438420 617400
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313134353735}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 888930
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313134373036}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1695130 476630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313537323233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 680320 1167810
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313639393633}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1438420 726530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313731383737}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 217310 1913030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313732323633}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 836410 1917230
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313732363630}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 502310 1677830
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313732393033}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1213290 1438430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e6574313734323933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 197340 826210
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743638353938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677820 2421090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743638373030}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1159120 1373960
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743638383432}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 636240 1154650
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743638393031}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999520 2440690
odb::dbWireEncoder_addRect $enc 0 0 80 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999520 2440690
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743639383037}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201520 1511090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743639383338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 121720 1457050
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743730323532}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 998970 1673630
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743730323537}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1828170 1274630
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743730363039}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1895370 1917230
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743730373133}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1701610 1358630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743731313233}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1997020 1995210
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743731353838}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 2252600
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743731363532}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837420 1303330
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743731373139}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1864610 1837430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743731373734}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 356940 2376920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732303338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1917220 1978760
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732313438}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1988890 1358630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732323135}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600520 2220610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732323435}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 511050 2156630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732333330}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 197340 1599570
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732343634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 446830 1593830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732353538}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 1669850
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732353631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 1670200
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732353831}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 107850 1518230
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732383433}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1139570 2316230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732383530}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1035240 2146410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732393132}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076820 2085370
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743732393536}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1702730 1593830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743733303932}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1089790 1753430
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743733363132}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1046090 1833230
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743733373234}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1978990 1837430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743733373932}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1140710 2316230
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743733393635}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1996170 795830
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743734313338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757620 1978970
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743734333534}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1997020 2262050
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743734373337}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1702350 2072630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743734393531}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1596330 1757630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743735303134}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1377070 1039430
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743735373533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1092890 1917230
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743736303037}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1815290 1274630
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743736323938}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1598020 981610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743736373537}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2012410 2072630
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743737313131}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2137850 157430
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743737323130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 560620 357490
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743737323539}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1553940 60480
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743737373733}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 171330 1593830
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743737393933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 712090 2396030
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743738303432}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 197340 1861160
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743738313732}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 456330 2072630
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743738353130}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 1129520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743738383335}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705610 2072630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743739323632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238920 1387120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743739353739}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2023830 317030
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743739393539}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 135290 1753430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830303833}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 407620 1598030
odb::dbWireEncoder_addRect $enc 0 0 110 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830323338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60810 2152430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830323939}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 816250 1358630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830333134}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 800020 1756090
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830373438}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 202490 2391830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830393339}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312040 2191000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743830393932}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 755940 2462320
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743831323131}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2116720 1343370
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743832323332}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 148910 1274630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743832323635}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1992840 1495480
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743832333733}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 2458680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743832333832}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 281150 2072630
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743832393230}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 479130 1917230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743833343037}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 998970 1514030
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743833353930}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1877320 1879570
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743833393137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 241420 1854160
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743833393339}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1438250 1354430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743834313837}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 375770 1598030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743834343939}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 602330 2076830
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743834373633}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336330 2076830
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743834383331}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 514090 1837430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743835303033}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 447970 1593830
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743835303633}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1097010 2312030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743835313136}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2065610 1913030
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743835313639}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 636240 682080
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743835343333}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1205690 1997030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743836323631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 261850 1354430
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743836353739}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 627710 1913030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743836393738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 851530 1997030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743837303132}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1717720 2355920
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743837333738}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2377230 1673630
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743837353830}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637920 2017610
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743837383131}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1478320 405370
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743837383638}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 106350 1677830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838303336}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 596340 86170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838313030}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1307930 317030
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838333436}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2471640 379120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838363530}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2341890 1917230
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838363533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2386730 2156630
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838363631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 1591450
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838363632}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2317610 1913030
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838383332}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1575050 1677830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743838383937}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2000270 401030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743839303036}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60750 1677830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743839313431}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1462190 955430
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743839333032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076820 460810
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743839333936}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 1991850
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743839393435}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1775310 237230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743930313432}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1115040 743680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743930323238}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1438420 200690
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743930373338}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401020 359730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743931323033}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1394340 869400
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743931333136}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 852250
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743931333837}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 1149680
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743931353035}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1633740 562170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743931393536}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 457520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743932333035}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 1684690
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743932353239}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 202110 2316230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743932353535}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 936650 2232230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743932383237}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1558120 298410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933303137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2272140 2018240
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933313232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2395090 2072630
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933323039}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2338090 1278830
odb::dbWireEncoder_addRect $enc 0 0 30 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933333634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1917220 75530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933353336}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2126810 161630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933363735}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 151200
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743933383236}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1836870 401030
odb::dbWireEncoder_addRect $enc 0 0 50 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934303733}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1917220 105280
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934303736}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 79520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934313733}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 1552250
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934323138}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 486010 81830
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934353335}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2236420 163450
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934353430}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1952940 77280
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934383232}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837420 986650
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934383335}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1278820 1040130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934383533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1474140 502880
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934393332}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435920 2252600
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743934393835}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1673850 241430
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935303832}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 110530 556430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935323533}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 81820 771330
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935323630}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97210 636230
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935323631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60750 640430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935353131}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2156620 304010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935353238}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1285110 1518230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935353330}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1398520 1457050
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935373937}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 2412480
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935383439}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 680320 337050
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743935393234}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676140 165760
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743936303032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 150080
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 150290
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743936333933}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1354440 510650
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743936353137}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 463330
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743937313634}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 356420 640430
odb::dbWireEncoder_addRect $enc 0 0 70 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743937323133}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 473430 556430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743937323437}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 406770
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743937343034}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2396020 926240
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743937353736}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 251890 720230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743938333837}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1342870 560630
odb::dbWireEncoder_addRect $enc 0 0 60 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743938353631}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1371370 1677830
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743938363032}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1372890 1833230
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743939303937}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 330930 317030
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6e65743939323530}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 311290
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f615c5b325c5d5b385d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2152440 684530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625c5b325c5d5b335d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198330 636230
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3130305c5d5b32315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 121720 2194640
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3131395c5d5b32315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 71450 1917230
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3132375c5d5b335d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 712830 1997030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3132385c5d5b31395d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2232240 1796130
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3135355c5d5b31365d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1432170 1598030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3137325c5d5b32315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1815210 1358630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3138375c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1039420 1986530
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3139315c5d5b32375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1313230 1757630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3139355c5d5b32375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2272140 2397850
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3139395c5d5b315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1837690 2316230
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3139395c5d5b33315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1278820 2165730
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3230375c5d5b33305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196520 2456720
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3231395c5d5b33305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2282990 2475830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3233345c5d5b31345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 2163000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3233345c5d5b31375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1428750 2076830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3234325c5d5b31325d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2201290 1917230
odb::dbWireEncoder_addRect $enc 0 0 120 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b3235355c5d5b355d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1354440 2008930
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b33355c5d5b31315d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 793010 1673630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b34365c5d5b385d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 800020 1703520
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b345c5d5b345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 589710 1115030
odb::dbWireEncoder_addRect $enc 0 0 20 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b37345c5d5b375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 915540 2247000
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b37395c5d5b31385d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 927530 2391830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b38395c5d5b32305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 728410 2312030
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b39365c5d5b32335d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 506110 1992830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5c5b39375c5d5b31345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 396840 2274440
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645c5b325c5d5b36395d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1842190 955430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645c5b375c5d5b31305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1194840 1037400
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5c5b335c5d5b33375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 802410
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1913040 802410
odb::dbWireEncoder_addRect $enc 0 0 170 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5c5b345c5d5b38395d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1558120 584010
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5c5b375c5d5b37305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1404810 955430
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5c5b375c5d5b37345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1424970 955430
odb::dbWireEncoder_addRect $enc 0 0 80 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5c5b375c5d5b375d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1315130 959630
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {70726f647563745c5b305c5d5b34365d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 1107120
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {70726f647563745c5b345c5d5b33305d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1035450 716030
odb::dbWireEncoder_addRect $enc 0 0 40 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {726f745f686967685c5b315c5d5b345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072640 1094170
odb::dbWireEncoder_addRect $enc 0 0 140 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {746f705f6e5b345d}]]]
if {$net eq "NULL"} {error "Missing exact net"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 582870 795830
odb::dbWireEncoder_addRect $enc 0 0 100 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db explicit-rectangles.odb
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-557/tasks/revision300-v-spacing-localize/selected-geometry.tcl}
bvgeom::export selected-after.tsv
drt::check_drc_cmd explicit-native-drc.rpt 0 0 0 0 native_whole_drc
