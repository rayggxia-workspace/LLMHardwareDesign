"""KLayout batch entry point to copy named hard macros from a stream donor."""

import pya

source = pya.Layout()
source.read(input_gds)
result = pya.Layout()
result.dbu = source.dbu
targets = {name: result.create_cell(name) for name in masters.split(",")}
roots = {target.cell_index() for target in targets.values()}
for name, target in targets.items():
    cell = source.cell(name)
    if cell is None or cell.is_empty():
        raise ValueError(f"Missing donor master {name}")
    target.copy_tree(cell)
for cell in result.each_cell():
    if cell.cell_index() not in roots:
        cell.name = f"PR271_U0_LEAF_{cell.cell_index()}_{cell.name}"
result.write(output_gds)
