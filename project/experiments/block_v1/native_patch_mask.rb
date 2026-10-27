# Independent complete-GDS polygon readback for the single measured M2 fill.
require 'json'
layouts = [$before_gds, $after_gds].map do |path|
  layout = RBA::Layout.new
  layout.read(path)
  raise 'Expected one complete native top' unless layout.top_cells.size == 1
  layout
end
unit = 0.0005
scales = layouts.map do |layout|
  ratio = layout.dbu / unit
  raise 'Non-integer exact native units' unless ratio >= 1 && (ratio-ratio.round).abs < 1e-9
  ratio.round
end
keys = layouts.flat_map { |l| l.layer_indices.map { |i| info=l.get_info(i); [info.layer,info.datatype] } }.uniq.sort
patch = RBA::Region.new(RBA::Box.new(282460,530600,282650,531160))
differences = []
keys.each do |key|
  masks = layouts.each_with_index.map do |layout,j|
    index = layout.find_layer(*key)
    region = index.nil? ? RBA::Region.new : RBA::Region.new(layout.top_cell.begin_shapes_rec(index))
    region.transformed(RBA::ICplxTrans.new(scales[j],0,false,0,0)).merged
  end
  before,after = masks
  expected = key == [13,0] ? (before | patch).merged : before
  raise 'Complete GDS mask differs from exact single patch: '+key.to_s unless (after ^ expected).is_empty?
  delta = (after ^ before).merged
  next if delta.is_empty?
  raise 'Changed another polygon layer' unless key == [13,0]
  raise 'Removed original polygon geometry' unless (before-after).is_empty?
  differences << {'gds_layer'=>key,'added_area_dbu2'=>delta.area,'added_bbox_dbu'=>[delta.bbox.left,delta.bbox.bottom,delta.bbox.right,delta.bbox.top]}
end
raise 'Expected actual nonempty M2 addition' unless differences.size == 1
File.write($out+'/patch-mask-readback.json',JSON.pretty_generate({
  'passed'=>true,'complete_polygon_layer_count'=>keys.size,'common_dbu_um'=>unit,
  'before_gds'=>$before_gds,'after_gds'=>$after_gds,'source_dbu_um'=>layouts.map(&:dbu),
  'exact_integer_scales'=>scales,'only_additive_expected_metal2_union'=>true,
  'missing_patch_negative_rejected'=>true,'differences'=>differences})+"\n")
