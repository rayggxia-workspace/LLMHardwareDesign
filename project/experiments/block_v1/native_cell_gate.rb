# Native Region connectivity follows the existing deck's poly/contact/metal
# chain. It does not invent diode factors or connect transistor source/drain.
# API: https://www.klayout.de/doc/code/class_Region.html
require 'json'
pins = File.readlines($pins).map { |line| line.strip.split("\t") }
wanted = pins.map { |row| row[0] }.uniq.sort
records = []
def connected(regions, seeds, links)
  selected = regions.keys.to_h { |key| [key, RBA::Region.new] }
  seeds.each do |layer, seed|
    selected[layer] = (selected[layer] | regions.fetch(layer).interacting(seed)).merged
  end
  100.times do
    before = selected.values.sum(&:area)
    links.each do |a,b|
      selected[b] = (selected[b] | regions[b].interacting(selected[a])).merged
      selected[a] = (selected[a] | regions[a].interacting(selected[b])).merged
    end
    return selected if selected.values.sum(&:area) == before
  end
  raise 'Native cell connectivity did not converge'
end
Dir.glob($platform + '/gds/*.gds').sort.each do |path|
  layout = RBA::Layout.new
  layout.read(path)
  wanted.each do |name|
    cell = layout.cell(name)
    next if cell.nil?
    rows = pins.select { |row| row[0] == name }
    regions = {}
    ([9,10] + (11..29).to_a).each do |number|
      index = layout.find_layer(number,0)
      regions[number] = index.nil? ? RBA::Region.new : RBA::Region.new(cell.begin_shapes_rec(index)).merged
    end
    region = lambda do |number|
      index = layout.find_layer(number,0)
      index.nil? ? RBA::Region.new : RBA::Region.new(cell.begin_shapes_rec(index)).merged
    end
    active = region.call(1)
    diode = ((region.call(4) & active) - region.call(3)).merged
    links = [[9,10],[10,11]] + (11..28).map { |number| [number,number+1] }
    terms = []
    rows.group_by { |row| [row[1],row[2]] }.each do |(term,direction), geometry|
      seeds = geometry.map do |row|
        match = /\Ametal(\d+)\z/.match(row[3])
        raise 'Unsupported signal pin layer' if match.nil?
        layer = 9 + 2 * match[1].to_i
        coordinates = row[4..7].map do |value|
          scaled = value.to_i / 2000.0 / layout.dbu
          raise 'Master pin cannot be represented on GDS grid' if (scaled-scaled.round).abs > 1e-7
          scaled.round
        end
        [layer,RBA::Region.new(RBA::Box.new(*coordinates))]
      end
      selected = connected(regions,seeds,links)
      gate_area = (selected[9] & active).area * layout.dbu**2
      diode_area = diode.interacting(selected[10]).area * layout.dbu**2
      without_contacts = regions.dup
      without_contacts[10] = RBA::Region.new
      disconnected = connected(without_contacts,seeds,links)
      missing_contact_gate = (disconnected[9] & active).area * layout.dbu**2
      terms << {'term' => term, 'direction' => direction,
        'gate_area_um2' => gate_area, 'diode_area_um2' => diode_area,
        'missing_contact_gate_area_um2' => missing_contact_gate,
        'seed_covered_um2' => seeds.sum { |layer, seed| (seed & regions[layer]).area } * layout.dbu**2}
    end
    records << {'master' => name, 'gds_file' => path, 'dbu_um' => layout.dbu,
      'all_gate_area_um2' => (regions[9] & active).area * layout.dbu**2,
      'all_deck_diode_area_um2' => diode.area * layout.dbu**2, 'terminals' => terms}
  end
end
raise 'Missing or duplicated GDS master' unless records.map { |r| r['master'] }.sort == wanted
File.write($report, JSON.pretty_generate({'schema' => 'block-v1-native-cell-gate-geometry/1',
  'masters' => records, 'connection_layers' => 'poly-cont-metal1-via1-...-metal10',
  'diode_definition' => '(nplus & active) - nwell; connected through actual contact geometry',
  'scope' => 'Native master input geometry only; no fabricated antenna LEF fields, diode factors, device characterization or repaired block'}) + "\n")
