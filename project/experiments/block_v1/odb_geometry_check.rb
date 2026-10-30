require 'json'
technology=RBA::Technology.new
technology.load($lyt)
options=technology.load_layout_options
config=options.lefdef_config
config.lef_files=[$tech,$macro]
config.read_lef_with_def=false
config.macro_resolution_mode=1
config.produce_lef_pins=true
config.lef_pins_datatype=0
config.lef_pins_suffix='.PIN'
config.produce_obstructions=false
config.dbu=0.0005
options.lefdef_config=config
mapping={}
File.read($lyt).scan(/'([^']+)\s+:\s+(\d+)\/(\d+)'/).each do |name,layer,datatype|
  mapping[name]=[layer.to_i,datatype.to_i] if name.match?(/\A(?:metal|via)\d+\z/)
end
raise 'Incomplete technology mapping' unless (1..12).all? { |i| mapping.key?("metal#{i}") } && (1..11).all? { |i| mapping.key?("via#{i}") }
results={}
%w[R0 R90 R180 R270 MX MY MXR90 MYR90].each do |orient|
  layout=RBA::Layout.new
  layout.read("geometry-#{orient}.def",options)
  layout.write("geometry-#{orient}.gds")
  checked=RBA::Layout.new
  checked.read("geometry-#{orient}.gds")
  wanted={}
  mapping.each_key { |name| wanted[name]=RBA::Region.new }
  File.foreach("geometry-#{orient}.tsv") do |line|
    next if line.start_with?('#')
    net,layer,kind,*bounds=line.strip.split("\t")
    raise "Unmapped geometry #{layer}" unless wanted.key?(layer)
    wanted[layer].insert(RBA::Box.new(*bounds.map(&:to_i)))
  end
  results[orient]={}
  mapping.each do |name,pair|
    layer=checked.find_layer(*pair)
    actual=layer.nil? ? RBA::Region.new : RBA::Region.new(checked.top_cell.begin_shapes_rec(layer)).merged
    expected=wanted.fetch(name).merged
    raise "ODB vs GDS mismatch #{orient} #{name}" unless (actual^expected).is_empty?
    results[orient][name]={'exact_union_match'=>true,'area_dbu2'=>actual.area}
  end
end
File.write($report,JSON.pretty_generate({'schema'=>'block-v1-odb-mask/1','passed'=>true,'orientations'=>results})+"\n")
