# Use unchanged library GDS cells and the unchanged complete platform deck.
# Each negative removes real connectivity, not a reported antenna area.
require 'json'
pins = File.readlines($pins).map { |line| line.strip.split("\t") }
library = RBA::Layout.new
library.read($gds)
cases = []
def signal_center(pins, name, dbu)
  rows = pins.select { |r| r[0] == name && r[1] == 'A' && r[3] == 'metal1' }
  raise 'No actual M1 input pin' if rows.empty?
  row = rows.max_by { |r| (r[6].to_i-r[4].to_i)*(r[7].to_i-r[5].to_i) }
  b = row[4..7].map { |n| (n.to_i/2000.0/dbu).round }
  [(b[0]+b[2])/2,(b[1]+b[3])/2]
end
%w[unprotected connected disconnected missing_contact].each do |name|
  layout = RBA::Layout.new
  layout.dbu = library.dbu
  top = layout.create_cell('ANTENNA_FIXTURE_' + name)
  buffer = layout.create_cell('BUF_X1')
  buffer.copy_tree(library.cell('BUF_X1'))
  top.insert(RBA::CellInstArray.new(buffer.cell_index,RBA::Trans.new))
  bx,by = signal_center(pins,'BUF_X1',layout.dbu)
  half = (0.035/layout.dbu).round
  left = (-250.0/layout.dbu).round
  m1 = layout.layer(11,0)
  top.shapes(m1).insert(RBA::Box.new(left,by-half,bx+half,by+half))
  diode_position = nil
  unless name == 'unprotected'
    diode = layout.create_cell('ANTENNA_X1')
    diode.copy_tree(library.cell('ANTENNA_X1'))
    diode.flatten(true)
    if name == 'missing_contact'
      diode.shapes(layout.layer(10,0)).clear
    end
    dx,dy = signal_center(pins,'ANTENNA_X1',layout.dbu)
    tx = (-5.0/layout.dbu).round
    ty = name == 'disconnected' ? (4.0/layout.dbu).round : 0
    top.insert(RBA::CellInstArray.new(diode.cell_index,RBA::Trans.new(tx,ty)))
    diode_position = [tx,ty]
    unless name == 'disconnected'
      px = tx+dx
      top.shapes(m1).insert(RBA::Box.new(px-half,[by,dy].min-half,px+half,[by,dy].max+half))
    end
  end
  path = $out + '/' + name + '.gds'
  layout.write(path)
  cases << {'name'=>name,'path'=>path,'dbu_um'=>layout.dbu,
    'input_seed_dbu'=>[bx,by],'diode_position_dbu'=>diode_position,
    'wire_width_um'=>half*2*layout.dbu,'wire_length_um'=>(bx+half-left)*layout.dbu}
end
File.write($out+'/antenna-fixtures.json',JSON.pretty_generate({'cases'=>cases})+"\n")
