set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-705/tasks/revision300-v-joint-via-compose/local-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set wanted [dict create]
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313436343639}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743936323232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e3136383739}]] 1
set selected [dict create]
foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}
if {[dict size $selected] != 3} {error "Missing target"}
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313436343639}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2314390 480620
odb::dbWireEncoder_addPoint $enc 2314390 483140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312490 480620
odb::dbWireEncoder_addPoint $enc 2314390 480620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2316290 482580
odb::dbWireEncoder_addPoint $enc 2316290 482860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2314390 482580
odb::dbWireEncoder_addPoint $enc 2316290 482580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2314390 483140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2312490 480620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2316290 482860
odb::dbWireEncoder_addPoint $enc 2316290 482855
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2316290 482855
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2316150 482790
odb::dbWireEncoder_addRect $enc 0 0 280 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743936323232}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 319620
odb::dbWireEncoder_addPoint $enc 536370 320740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 319620
odb::dbWireEncoder_addPoint $enc 555370 319620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 555370 319620
odb::dbWireEncoder_addPoint $enc 555370 321580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 537890 324660
odb::dbWireEncoder_addPoint $enc 537890 326340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 324660
odb::dbWireEncoder_addPoint $enc 537890 324660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 320740
odb::dbWireEncoder_addPoint $enc 536370 324660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534850 295260
odb::dbWireEncoder_addPoint $enc 534850 296940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534090 296940
odb::dbWireEncoder_addPoint $enc 534850 296940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534090 296940
odb::dbWireEncoder_addPoint $enc 534090 319620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534470 292740
odb::dbWireEncoder_addPoint $enc 534470 294980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534470 294980
odb::dbWireEncoder_addPoint $enc 534850 294980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534850 294980
odb::dbWireEncoder_addPoint $enc 534850 295260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 531050 294980
odb::dbWireEncoder_addPoint $enc 531050 295260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 531050 294980
odb::dbWireEncoder_addPoint $enc 534470 294980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 642390 311220
odb::dbWireEncoder_addPoint $enc 642390 312900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 532570 424900
odb::dbWireEncoder_addPoint $enc 532570 425180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 532570 424900
odb::dbWireEncoder_addPoint $enc 537130 424900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 537130 424060
odb::dbWireEncoder_addPoint $enc 537130 424900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 708890 277060
odb::dbWireEncoder_addPoint $enc 708890 277620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 708890 277620
odb::dbWireEncoder_addPoint $enc 723710 277620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 723710 275940
odb::dbWireEncoder_addPoint $enc 723710 277620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520410 323260
odb::dbWireEncoder_addPoint $enc 520430 323260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 319060
odb::dbWireEncoder_addPoint $enc 520430 323260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 508630 319060
odb::dbWireEncoder_addPoint $enc 520430 319060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 508630 317660
odb::dbWireEncoder_addPoint $enc 508630 319060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 319620
odb::dbWireEncoder_addPoint $enc 536370 319620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520030 396060
odb::dbWireEncoder_addPoint $enc 520030 396900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520030 396900
odb::dbWireEncoder_addPoint $enc 520430 396900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 522690 384860
odb::dbWireEncoder_addPoint $enc 522690 385980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 385980
odb::dbWireEncoder_addPoint $enc 522690 385980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 385980
odb::dbWireEncoder_addPoint $enc 520430 396900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 385980
odb::dbWireEncoder_addPoint $enc 520990 385980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 570570 321580
odb::dbWireEncoder_addPoint $enc 570570 321860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 570570 321860
odb::dbWireEncoder_addPoint $enc 592110 321860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 555370 321580
odb::dbWireEncoder_addPoint $enc 570570 321580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 376740
odb::dbWireEncoder_addPoint $enc 592230 377020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 377020
odb::dbWireEncoder_addPoint $enc 592670 377020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 585010 376740
odb::dbWireEncoder_addPoint $enc 585010 378980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 585010 378980
odb::dbWireEncoder_addPoint $enc 592230 378980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 377020
odb::dbWireEncoder_addPoint $enc 592230 378980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 664810 292740
odb::dbWireEncoder_addPoint $enc 664810 293860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 662910 293860
odb::dbWireEncoder_addPoint $enc 664810 293860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 662910 293860
odb::dbWireEncoder_addPoint $enc 662910 311220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 664810 293860
odb::dbWireEncoder_addPoint $enc 665470 293860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 642390 311220
odb::dbWireEncoder_addPoint $enc 662910 311220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 347340
odb::dbWireEncoder_addPoint $enc 520990 347340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 323260
odb::dbWireEncoder_addPoint $enc 520430 347340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520990 347340
odb::dbWireEncoder_addPoint $enc 520990 385980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 526490 418180
odb::dbWireEncoder_addPoint $enc 526490 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 523790 418180
odb::dbWireEncoder_addPoint $enc 526490 418180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 523790 418180
odb::dbWireEncoder_addPoint $enc 523790 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 525350 418180
odb::dbWireEncoder_addPoint $enc 525350 425180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 396900
odb::dbWireEncoder_addPoint $enc 520430 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 525350 425180
odb::dbWireEncoder_addPoint $enc 532570 425180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 592110 332780
odb::dbWireEncoder_addPoint $enc 592670 332780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 592110 312620
odb::dbWireEncoder_addPoint $enc 592110 332780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 592670 332780
odb::dbWireEncoder_addPoint $enc 592670 377020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 665950 275940
odb::dbWireEncoder_addPoint $enc 665950 277340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 665950 277340
odb::dbWireEncoder_addPoint $enc 678910 277340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 678910 277060
odb::dbWireEncoder_addPoint $enc 678910 277340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 665470 277340
odb::dbWireEncoder_addPoint $enc 665950 277340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 665470 277340
odb::dbWireEncoder_addPoint $enc 665470 293860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 678910 277060
odb::dbWireEncoder_addPoint $enc 708890 277060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 510530 417900
odb::dbWireEncoder_addPoint $enc 510530 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510530 417900
odb::dbWireEncoder_addPoint $enc 510910 417900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 417900
odb::dbWireEncoder_addPoint $enc 510910 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 502930 421680
odb::dbWireEncoder_addPoint $enc 502930 421960
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 502910 421960
odb::dbWireEncoder_addPoint $enc 502930 421960
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 502910 421960
odb::dbWireEncoder_addPoint $enc 502910 422100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 502910 422100
odb::dbWireEncoder_addPoint $enc 503310 422100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 422100
odb::dbWireEncoder_addPoint $enc 503310 423780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 423780
odb::dbWireEncoder_addPoint $enc 510910 423780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 418460
odb::dbWireEncoder_addPoint $enc 510910 423780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 418460
odb::dbWireEncoder_addPoint $enc 523790 418460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 628710 312060
odb::dbWireEncoder_addPoint $enc 628710 312620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 636310 312060
odb::dbWireEncoder_addPoint $enc 636310 312900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 628710 312900
odb::dbWireEncoder_addPoint $enc 636310 312900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 628710 312620
odb::dbWireEncoder_addPoint $enc 628710 312900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 592110 312620
odb::dbWireEncoder_addPoint $enc 628710 312620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 636310 312900
odb::dbWireEncoder_addPoint $enc 642390 312900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 320740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 319620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 555370 319620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 555370 321580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 537890 326340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 537890 324660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 536370 324660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 534850 295260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534090 319620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 534470 292740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 531050 295260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 531050 294980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 534470 294980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 642390 311220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 642390 312900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 537130 424900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 537130 424060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 723710 277620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 723710 275940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 520410 323260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520410 323260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 323260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 319060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 508630 319060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 508630 317660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 319620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 520030 396060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 396900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 522690 384860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 522690 385980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 385980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 592110 312620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 592110 321860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 376740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 377020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 592670 377020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 585010 376740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 585010 378980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 592230 378980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 664810 292740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 664810 293860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 662910 293860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 662910 311220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 665470 293860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 526490 418460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 526490 418180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 523790 418180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 523790 418460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 520430 418460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 525350 425180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 525350 418180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 665950 275940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 665950 277340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 665470 277340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 510530 418460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 510530 417900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 417900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 418460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 502930 421680
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 423780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 423780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 628710 312060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 628710 312620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 636310 312060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 636310 312900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520030 396900
odb::dbWireEncoder_addPoint $enc 520035 396900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520035 396900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 519960 396760
odb::dbWireEncoder_addRect $enc 0 0 140 280
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e3136383739}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1753500
odb::dbWireEncoder_addPoint $enc 2371790 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1855140
odb::dbWireEncoder_addPoint $enc 2371790 1855140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2371790 1753500
odb::dbWireEncoder_addPoint $enc 2371790 1855140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1753500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2371790 1753500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2371790 1855140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1855140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1855140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2371390 1753500
odb::dbWireEncoder_addPoint $enc 2371395 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2371395 1753500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2371320 1753360
odb::dbWireEncoder_addRect $enc 0 0 140 280
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db local-candidate.odb
write_def local-candidate.def
drt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc
