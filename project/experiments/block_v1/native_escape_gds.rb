# Diagnostic masks from all actual ODB M9/M10/via9 conductor boxes.
# This is not the complete library GDS or complete native physical receiver.
require 'json'
result = {}
native = RBA::Layout.new
native.read($source_gds)
raise 'Ambiguous native top cell' unless native.top_cells.size == 1
scale = native.dbu / 0.0005
raise 'Native mask cannot scale exactly to probe DBU' unless (scale-scale.round).abs < 1e-9 && scale >= 1
%w[before after].each do |stage|
  layout = RBA::Layout.new
  layout.dbu = 0.0005
  top = layout.create_cell('ESCAPE_' + stage)
  expected = {'metal9'=>RBA::Region.new,'via9'=>RBA::Region.new,'metal10'=>RBA::Region.new}
  mapping = {'metal9'=>27,'via9'=>28,'metal10'=>29}
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
  raise 'Diagnostic mask units changed' unless readback.dbu == layout.dbu
  areas = {}
  expected.each do |name,region|
    index = readback.find_layer(mapping[name],0)
    actual = index.nil? ? RBA::Region.new : RBA::Region.new(readback.top_cell.begin_shapes_rec(index)).merged
    raise 'Diagnostic mask XOR failed' unless (actual ^ region.merged).is_empty?
    areas[name] = actual.area
    if stage == 'before'
      source_index = native.find_layer(mapping[name],0)
      source_mask = source_index.nil? ? RBA::Region.new : RBA::Region.new(native.top_cell.begin_shapes_rec(source_index))
      source_mask = source_mask.transformed(RBA::ICplxTrans.new(scale,0,false,0,0)).merged
      raise 'Actual ODB upper mask differs from full native GDS: '+name unless (source_mask ^ region.merged).is_empty?
    end
  end
  result[stage] = {'exact_union_readback'=>true,'areas_dbu2'=>areas,'path'=>path}
  result[stage]['exact_full_native_upper_mask_xor_zero'] = true if stage == 'before'
end
result['native_source'] = {'path'=>$source_gds,'dbu_um'=>native.dbu,'probe_dbu_um'=>0.0005,'exact_integer_scale'=>scale.round}
File.write($out+'/upper-mask-readback.json',JSON.pretty_generate(result)+"\n")
