# Additional access-side restrictions diagnosed from the _64 compact fixtures.
# DBU=2000/um. Original compact macro locations and pin shapes are unchanged.
# Block the off-pin approach that creates a narrow overlap; retain on-pin access.
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
switch -- $::env(DESIGN_NAME) {
    cfj_group_c {
        odb::dbObstruction_create $block [$tech findLayer via9] 189000 1845600 194200 1851000
        odb::dbObstruction_create $block [$tech findLayer metal10] 3380800 1445200 3384800 1446990
        odb::dbObstruction_create $block [$tech findLayer metal10] 2461600 1929600 2463190 1932800
    }
    cfj_group_j {
        odb::dbObstruction_create $block [$tech findLayer metal10] 2461600 1489600 2463190 1495200
    }
    default {error "Expected fixed compact C or J _64 fixture"}
}
