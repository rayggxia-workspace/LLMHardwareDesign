# Read-only interconnect/pin geometry. OBS are keepouts, not conductors.
# Macro internals require their separately frozen leaf databases.
namespace eval bvgeom {
proc present {object} { expr {$object ne "NULL" && $object ne ""} }
proc rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  set x0 [expr {[$object xMin]+$dx}]
  set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}]
  set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {}; set ys {}
    foreach x [list $x0 $x1] {
      foreach y [list $y0 $y1] {
        set point [odb::new_Point $x $y]
        $transform apply $point
        lappend xs [$point getX]; lappend ys [$point getY]
        odb::delete_Point $point
      }
    }
    set x0 [tcl::mathfunc::min {*}$xs]; set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys]; set y1 [tcl::mathfunc::max {*}$ys]
  }
  if {$x0 >= $x1 || $y0 >= $y1} { error "Degenerate conductor rectangle" }
  puts $stream "$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
}
proc db_box {stream net box kind {transform ""}} {
  if {[$box isVia]} {
    set via [$box getTechVia]
    if {![present $via]} { set via [$box getBlockVia] }
    if {![present $via]} { error "Unresolved box via" }
    lassign [$box getViaXY] x y
    foreach part [$via getBoxes] {
      rectangle $stream $net [$part getTechLayer] $kind-via $part $x $y $transform
    }
  } else {
    rectangle $stream $net [$box getTechLayer] $kind $box 0 0 $transform
  }
}
proc wire_shape {stream net shape} {
  if {[$shape isVia]} {
    set via [$shape getTechVia]
    if {![present $via]} { set via [$shape getVia] }
    if {![present $via]} { error "Unresolved wire via" }
    lassign [$shape getViaXY] x y
    foreach box [$via getBoxes] {
      rectangle $stream $net [$box getTechLayer] wire-via $box $x $y
    }
  } else {
    rectangle $stream $net [$shape getTechLayer] wire $shape
  }
}
proc export {destination} {
  set block [ord::get_db_block]
  set output [open $destination w]
  set terms [open selected-terminals.tsv w]
  puts $output "# block-v1-odb-geometry/1 dbu_per_um=[$block getDbUnitsPerMicron]"
  set itr [odb::new_dbWirePathItr]
  set path [odb::new_dbWirePath]
  set element [odb::new_dbWirePathShape]
  set wanted [dict create]
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343239383233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343330303731}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f246466666c69626d61702e63633a3534363a6466666c69626d61702431343333393338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431333538333732}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431333539393730}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431343033383232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246175746f2472746c696c2e63633a333531333a4d7578476174652431343034333338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313035323635}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313037373135}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313134343533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313139363036}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313230373632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313235393536}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313332323737}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313335333530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313339313333}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313432313233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313433313535}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313538323234}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313539383733}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313635303039}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313639343239}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313731383435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313734353837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313737343734}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313737373837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313738313534}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313738343337}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313739333736}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313830353533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313831353439}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313832353835}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834323834}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834353935}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313837303637}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313838343137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313839363231}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313932353435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313933353236}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313938323535}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313939343334}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313939353231}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323033303338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323036333437}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323039303732}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323131393930}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323133383232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323134363133}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323135323738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323136303135}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323139333232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323231303635}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323232303834}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323237343535}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323238363237}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323333333130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323334383832}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323433333839}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323434353435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323436393431}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323438323937}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323532313938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323535373434}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323535393636}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323630313833}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323634363439}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323637363838}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323731323138}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323733363736}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323738373230}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739303135}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739303735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739363735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323739383534}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323830393132}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323838393334}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323930363732}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323937303931}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323938343434}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939383038}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939383334}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323939393830}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333031343437}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333033313637}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333033343938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333035343731}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333130303239}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333136343233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333137373030}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333137373930}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333337383838}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333435343032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333436323132}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333436383333}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333531343934}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333533373232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333536333133}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333633353833}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333633373737}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333635363930}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333735363238}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333736323731}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333736373638}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333738383539}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333833353030}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333837393334}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333930343239}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333932393034}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343032363634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343034323237}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343034383936}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343131333137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343131333933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e343135393631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3535343336}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3536343736}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3538313333}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3538323634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3539363530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3631313133}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3631323134}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3634373036}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3636313038}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3636333738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3732393130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3733363139}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3738343032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3739343438}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3739343836}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3832373331}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3932323136}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3935313932}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3935313936}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e3937383031}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133353935}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133373830}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3134313737}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3134373934}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3135313938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3135373734}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136343337}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373931}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3138323139}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3138353632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e32363230}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e32393534}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34323233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34343031}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e34353238}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e35323631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e36333735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e39303633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {63686f73656e5f69645b315d5b325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f3132395f305f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f3137305f305f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f385f385f305f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f323133305f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3237315f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f323733375f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3533305f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f3733325f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f37395f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f38345f636c6b}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e64656c7461315b315d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e66726163315b305d5b375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3130345d5b31325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3131305d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3133375d5b31315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3134315d5b32335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3135345d5b335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3136365d5b32385d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3138325d5b32305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3139375d5b325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3231325d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3232355d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3233375d5b32355d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3234395d5b31345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b32365d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b34305d5b355d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b34385d5b31345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b35365d5b31365d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b36335d5b31315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b36385d5b32325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b39325d5b355d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313031313031}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313031373532}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313032373038}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313032383538}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313032383632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313033373835}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313034333430}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313034373831}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313034383639}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313034393830}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313035373933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313036323632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313036323836}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313037303335}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313037303638}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313037313439}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313037383032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313038353639}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313038363337}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313038363630}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313038373135}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313039303034}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313039303933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313039313137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313039373738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313130313031}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313130323631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313130333037}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313130383130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313131313033}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313131343432}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313131343835}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313131383639}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313131383935}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313132333136}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313132373938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313132393432}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133313234}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133313839}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133323933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133333332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133353436}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133393332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313133393538}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313134323236}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313134353333}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313134353433}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313134353735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313134373036}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313537323233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313639393633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313731383737}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313732323633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313732363630}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313732393033}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313734323933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743638353938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743638373030}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743638383432}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743638393031}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743639383037}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743639383338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743730323532}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743730323537}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743730363039}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743730373133}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743731313233}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743731353838}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743731363532}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743731373139}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743731373734}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732303338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732313438}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732323135}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732323435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732333330}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732343634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732353538}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732353631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732353831}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732383433}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732383530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732393132}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732393536}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743733303932}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743733363132}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743733373234}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743733373932}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743733393635}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743734313338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743734333534}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743734373337}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743734393531}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743735303134}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743735373533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743736303037}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743736323938}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743736373537}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737313131}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737323130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737323539}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737373733}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737393933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743738303432}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743738313732}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743738353130}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743738383335}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743739323632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743739353739}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743739393539}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830303833}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830323338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830323939}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830333134}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830373438}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830393339}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830393932}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743831323131}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832323332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832323635}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832333733}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832333832}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832393230}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743833343037}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743833353930}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743833393137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743833393339}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834313837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834343939}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834373633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834383331}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835303033}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835303633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835313136}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835313639}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835343333}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743836323631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743836353739}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743836393738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743837303132}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743837333738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743837353830}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743837383131}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743837383638}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838303336}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838313030}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838333436}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838363530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838363533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838363631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838363632}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838383332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838383937}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743839303036}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743839313431}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743839333032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743839333936}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743839393435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743930313432}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743930323238}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743930373338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743931323033}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743931333136}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743931333837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743931353035}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743931393536}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743932333035}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743932353239}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743932353535}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743932383237}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933303137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933313232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933323039}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933333634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933353336}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933363735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743933383236}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934303733}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934303736}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934313733}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934323138}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934353335}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934353430}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934383232}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934383335}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934383533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934393332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743934393835}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935303832}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935323533}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935323630}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935323631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935353131}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935353238}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935353330}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935373937}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935383439}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935393234}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743936303032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743936333933}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743936353137}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743937313634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743937323133}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743937323437}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743937343034}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743937353736}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743938333837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743938353631}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743938363032}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743939303937}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743939323530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f615b325d5b385d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b325d5b335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3130305d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3131395d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3132375d5b335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3132385d5b31395d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3135355d5b31365d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3137325d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3138375d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139315d5b32375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139355d5b32375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139395d5b315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139395d5b33315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3230375d5b33305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3231395d5b33305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3233345d5b31345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3233345d5b31375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3234325d5b31325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3235355d5b355d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b33355d5b31315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b34365d5b385d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b345d5b345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b37345d5b375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b37395d5b31385d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b38395d5b32305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39365d5b32335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39375d5b31345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645b325d5b36395d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645b375d5b31305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b335d5b33375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b345d5b38395d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b37305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b37345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {70726f647563745b305d5b34365d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {70726f647563745b345d5b33305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {726f745f686967685b315d5b345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {746f705f6e5b345d}]] 1
set selected {};set found [dict create]
  foreach candidate [$block getNets] {
    set plain [string map [list [format %c 92] {}] [$candidate getName]]
    if {[dict exists $wanted $plain]} {
      if {[dict exists $found $plain]} {error "Ambiguous normalized net"}
      dict set found $plain 1;lappend selected $candidate
    }
  }
  if {[dict size $found] != [dict size $wanted]} {error "Missing reported net"}
  foreach net $selected {
    set alias n[$net getId]
    puts $output "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]]"
    foreach term [$net getITerms] {
      set inst [$term getInst];set mt [$term getMTerm]
      puts $terms "$alias\t[binary encode hex [encoding convertto utf-8 [$inst getName]]]\t[binary encode hex [encoding convertto utf-8 [[$inst getMaster] getName]]]\t[binary encode hex [encoding convertto utf-8 [$mt getName]]]\t[$mt getIoType]\t[$mt getSigType]"
    }
    set wire [$net getWire]
    if {[present $wire]} {
      $itr begin $wire
      while {[$itr getNextPath $path]} {
        while {[$itr getNextShape $element]} {
          wire_shape $output $alias [odb::dbWirePathShape_shape_get $element]
        }
      }
    }
    foreach special [$net getSWires] {
      foreach box [$special getWires] {
        if {![$box isVia] && [$box getDirection] in {3 OCTILINEAR}} {
          error "Nonrectangular special wire requires an exact polygon exporter"
        }
        db_box $output $alias $box special
      }
    }
    foreach term [$net getBTerms] {
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
          db_box $output $alias $box block-port
        }
      }
    }
    foreach term [$net getITerms] {
      set inst [$term getInst]
      set transform [$inst getTransform]
      foreach pin [[$term getMTerm] getMPins] {
        foreach box [$pin getGeometry] {
          db_box $output $alias $box instance-pin $transform
        }
      }
    }
  }
  close $output;close $terms
  odb::delete_dbWirePathShape $element
  odb::delete_dbWirePath $path
  odb::delete_dbWirePathItr $itr
}
}
