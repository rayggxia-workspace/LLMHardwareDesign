require 'json'
technology=RBA::Technology.new
technology.load($lyt)
options=technology.load_layout_options
config=options.lefdef_config
config.lef_files=[$lef]
config.read_lef_with_def=false
config.macro_resolution_mode=1
config.produce_lef_pins=true
config.lef_pins_datatype=0
config.lef_pins_suffix='.PIN'
config.dbu=0.0005
options.lefdef_config=config
layout=RBA::Layout.new
layout.read($input,options)
layout.write($output)
checked=RBA::Layout.new
checked.read($output)
raise 'Unexpected GDS units' unless checked.dbu==0.0005
mapping={'metal10'=>[29,0],'via10'=>[210,0],'metal11'=>[211,0],'via11'=>[212,0],'metal12'=>[213,0]}
expected=JSON.parse(File.read($expected))
results={}
mapping.each do |name,pair|
  layer=checked.find_layer(*pair)
  actual=layer.nil? ? RBA::Region.new : RBA::Region.new(checked.top_cell.begin_shapes_rec(layer)).merged
  wanted=RBA::Region.new
  expected.fetch(name).each { |box| wanted.insert(RBA::Box.new(*box.map { |v| (v/checked.dbu).round })) }
  wanted=wanted.merged
  raise "Mask mismatch #{name}" unless (actual^wanted).is_empty?
  results[name]={'area_dbu2'=>actual.area,'exact_union_match'=>true}
end
File.write($report,JSON.pretty_generate({'schema'=>'block-v1-primitive-mask/1','dbu_um'=>checked.dbu,'layers'=>results})+"\n")
