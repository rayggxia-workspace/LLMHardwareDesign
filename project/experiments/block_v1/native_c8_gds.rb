# Complete actual upper ODB rectangle unions; diagnostic, not full library GDS.
require 'json'
result = {}
%w[before after].each do |stage|
  layout = RBA::Layout.new
  layout.dbu = 0.0005
  top = layout.create_cell('C8_' + stage)
  mapping = {'metal9'=>27,'via9'=>28,'metal10'=>29}
  expected = mapping.transform_values { RBA::Region.new }
  File.foreach($out + '/' + stage + '-geometry.tsv') do |line|
    fields = line.strip.split("\t")
    next unless mapping.key?(fields[1])
    expected[fields[1]].insert(RBA::Box.new(*fields[3..6].map(&:to_i)))
  end
  expected.each { |name,region| top.shapes(layout.layer(mapping[name],0)).insert(region.merged) }
  path = $out + '/' + stage + '-upper.gds'
  layout.write(path)
  readback = RBA::Layout.new
  readback.read(path)
  raise 'Units or top changed' unless readback.dbu == layout.dbu && readback.top_cells.size == 1
  areas = {}
  expected.each do |name,region|
    index = readback.find_layer(mapping[name],0)
    actual = index.nil? ? RBA::Region.new : RBA::Region.new(readback.top_cell.begin_shapes_rec(index)).merged
    raise 'Actual ODB upper union readback differs' unless (actual ^ region.merged).is_empty?
    areas[name] = actual.area
  end
  result[stage] = {'exact_union_readback'=>true,'areas_dbu2'=>areas,'path'=>path}
end
result['scope'] = 'Actual complete upper ODB conductor unions only; no full native GDS/library comparison or full physical qualification'
File.write($out+'/upper-mask-readback.json',JSON.pretty_generate(result)+"\n")
