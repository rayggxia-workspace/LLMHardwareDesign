# Routing-only keepouts for the fixed compact C/F acceptance fixtures.
# Coordinates are DBU (2000/um), not reusable top-level placement constraints.
# Preserve the original leaf GDS, Liberty, LEF pin declarations and DRC rules.
# The independent final native GDS must still pass the complete native deck.
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
switch -- $::env(DESIGN_NAME) {
    cfj_group_c {
        odb::dbObstruction_create $block [$tech findLayer via9] 190000 1925000 194400 1932000
        odb::dbObstruction_create $block [$tech findLayer metal10] 3196500 1660400 3198100 1662040
        odb::dbObstruction_create $block [$tech findLayer metal10] 2782300 1162160 2783440 1164000
    }
    cfj_group_f {
        odb::dbObstruction_create $block [$tech findLayer metal9] 1188000 1469600 1200000 1474800
    }
    default {error "Compact native edge guards require the declared C or F fixture"}
}
