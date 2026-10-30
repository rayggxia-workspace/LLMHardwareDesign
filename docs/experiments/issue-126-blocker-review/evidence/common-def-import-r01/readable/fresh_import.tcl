# NEW controlled parent access experiment; never a reconstruction of old handoff.
# routing_only.lib carries port declarations, not characterized timing models.
set out $::env(PINXY_PARENT_OUT)
set stages [open $out/fresh_import.stages.tsv w];puts $stages "stage\tstatus\tdetail"
proc stage {name body} {
  global stages
  puts "STAGE_START $name"
  if {[catch {uplevel 1 $body} result options]} {
    puts $stages "$name\tFAIL\t[string map [list \n { | } \t { }] $result]";flush $stages
    set f [open "$::env(PINXY_PARENT_OUT)/$name.error.txt" w];puts $f [dict get $options -errorinfo];close $f
    puts "STAGE_FAIL $name $result";return 0
  }
  puts $stages "$name\tEXECUTED\t";flush $stages;puts "STAGE_EXECUTED $name";return 1
}
proc parent_contract {prefix} {
  set b [ord::get_db_block]
  set f [open "$prefix.instances.tsv" w];puts $f "instance\tmaster\tx\ty\torientation"
  foreach i [$b getInsts] {lassign [$i getLocation] x y;puts $f [join [list [$i getName] [[$i getMaster] getName] $x $y [$i getOrient]] "\t"]};close $f
  set f [open "$prefix.endpoints.tsv" w];puts $f "kind\tinstance\tpin\tnet\tdirection\tlayer"
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} {continue}
    foreach it [$n getITerms] {
      set ls {};foreach g [$it getGeometries] {lappend ls [[lindex $g 0] getName]}
      puts $f [join [list ITERM [[$it getInst] getName] [[$it getMTerm] getName] [$n getName] [$it getIoType] [join [lsort -unique $ls] ,]] "\t"]
    }
    foreach bt [$n getBTerms] {
      set ls {};foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend ls [[$box getTechLayer] getName]}}
      puts $f [join [list BTERM {} [$bt getName] [$n getName] [$bt getIoType] [join [lsort -unique $ls] ,]] "\t"]
    }
  };close $f
  set f [open "$prefix.pins.tsv" w];puts $f "pin\tdirection\tuse\tnet\tlayer\tx0\ty0\tx1\ty1"
  foreach bt [$b getBTerms] {foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts $f [join [list [$bt getName] [$bt getIoType] [$bt getSigType] [[$bt getNet] getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}}};close $f
  set f [open "$prefix.pdn.tsv" w]
  foreach n [$b getNets] {foreach sw [$n getSWires] {foreach r [$sw getWires] {
    set via {};set xy {}
    if {[$r isVia]} {set v [$r getTechVia];if {$v eq "NULL"} {set v [$r getBlockVia]};set via [$v getName];set layer VIA;set xy [$r getViaXY]} else {set layer [[$r getTechLayer] getName]}
    puts $f [join [list [$n getName] $layer [$r xMin] [$r yMin] [$r xMax] [$r yMax] $via $xy] "\t"]
  }}};close $f
}

proc common_shared_snapshot {file} {
 set f [open $file w];puts $f "pad\tnet\tlayer\tx0\ty0\tx1\ty1"
 set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
 foreach pad $::common_shared_pads {
  set bt [[ord::get_db_block] findBTerm $pad];set n [$bt getNet];set w [$n getWire]
  if {$w eq "NULL"} {error "Shared physical conductor missing: $pad"}
  $itr begin $w
  while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
   set s [odb::dbWirePathShape_shape_get $ps];if {[$s isVia]} {error "Unexpected via in fixed M10-only resource"}
   puts $f [join [list $pad [$n getName] [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]] "\t"]
  }}
 };close $f
}
set common_shared_pads {access_0001 access_0002 access_0003 access_0004 access_0005 access_0006 access_0007 access_0008 access_0009 access_0010 access_0011 access_0012 access_0013 access_0014 access_0015 access_0016 access_0017 access_0018 access_0019 access_0020 access_0021 access_0022 access_0023 access_0024 access_0025 access_0026 access_0027 access_0028 access_0029 access_0030 access_0031 access_0032 access_0033 access_0034 access_0035 access_0036 access_0037 access_0038 access_0039 access_0040 access_0041 access_0042 access_0043 access_0044 access_0045 access_0046 access_0047 access_0048 access_0049 access_0050 access_0051 access_0052 access_0053 access_0054 access_0055 access_0056 access_0057 access_0058 access_0059 access_0060 access_0061 access_0062 access_0063 access_0064 access_0065 access_0066 access_0067 access_0068 access_0069 access_0070 access_0071 access_0072 access_0073 access_0074 access_0075 access_0076 access_0077 access_0078 access_0079 access_0080 access_0081 access_0082 access_0083 access_0084 access_0085 access_0086 access_0087 access_0088 access_0089 access_0090 access_0091 access_0092 access_0093 access_0094 access_0095 access_0096 access_0097 access_0098 access_0099 access_0100 access_0101 access_0102 access_0103 access_0104 access_0105 access_0106 access_0107 access_0108 access_0109 access_0110 access_0111 access_0112 access_0113 access_0114 access_0115 access_0116 access_0117 access_0118 access_0119 access_0120 access_0121 access_0122 access_0123 access_0124 access_0125 access_0126 access_0127 access_0128 access_0129 access_0130 access_0131 access_0132 access_0133 access_0134 access_0135 access_0136 access_0137 access_0138 access_0139 access_0140 access_0141 access_0142 access_0143 access_0144 access_0145 access_0146 access_0147 access_0148 access_0149 access_0150 access_0151 access_0152 access_0153 access_0154 access_0155 access_0156 access_0157 access_0158 access_0159 access_0160 access_0161 access_0162 access_0163 access_0164 access_0165 access_0166 access_0167 access_0168 access_0169 access_0170 access_0171 access_0172 access_0173 access_0174 access_0175 access_0176 access_0177 access_0178 access_0179 access_0180 access_0181 access_0182 access_0183 access_0184 access_0185 access_0186 access_0187 access_0188 access_0189 access_0190 access_0191 access_0192 access_0193 access_0194 access_0195 access_0196 access_0197 access_0198 access_0199 access_0200 access_0201 access_0202 access_0203 access_0204 access_0205 access_0206 access_0207 access_0208 access_0209 access_0210 access_0211 access_0212 access_0213 access_0214 access_0215 access_0216 access_0217 access_0218 access_0219 access_0220 access_0221 access_0222 access_0223 access_0224 access_0225 access_0226 access_0227 access_0228 access_0229 access_0230 access_0231 access_0232 access_0233 access_0234 access_0235 access_0236 access_0237 access_0238 access_0239 access_0240 access_0241 access_0242 access_0243 access_0244 access_0245 access_0246 access_0247 access_0248 access_0249 access_0250 access_0251 access_0252 access_0253 access_0254 access_0255 access_0256}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_layer_probe/r01/model/research12.tech.lef}
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_act.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_act.lib}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_mxu.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_mxu.lib}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_opentpu_aux.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_opentpu_aux.lib}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_gemm.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_gemm.lib}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_vector.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_vector.lib}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_llaccel_aux.lef}
read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_current_resume/r01/p126resume_llaccel_aux.lib}
if {![stage import_exact_checkpoint {read_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/current_fixed.def}}]} {close $stages;exit 1}
parent_contract {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/after}
common_shared_snapshot {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/after.shared.tsv}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/imported_current_NOT_ROUTED_NOT_FROZEN.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/imported_current.def}
stage VDD {check_power_grid -net VDD -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/VDD.rpt}}
stage VSS {check_power_grid -net VSS -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/VSS.rpt}}
close $stages
