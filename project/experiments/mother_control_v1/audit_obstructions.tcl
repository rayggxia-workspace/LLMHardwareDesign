set stream [open physical-obstructions.tsv w]
foreach obstruction [[ord::get_db_block] getObstructions] {
 set b [$obstruction getBBox]
 puts $stream "[[$b getTechLayer] getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]"
}
close $stream