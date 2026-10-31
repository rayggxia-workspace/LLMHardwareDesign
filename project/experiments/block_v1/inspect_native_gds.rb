# Read-only audit of actual native GDS layer/datatype use.
require 'json'
records = []
Dir.glob($platform + '/gds/*.gds').sort.each do |path|
  layout = RBA::Layout.new
  layout.read(path)
  layers = layout.layer_indices.map { |index| info = layout.get_info(index); [info.layer, info.datatype] }.sort
  records << {'path' => path, 'dbu_um' => layout.dbu, 'layers' => layers}
end
raise 'No native GDS input found' if records.empty?
custom = [[210,0],[211,0],[212,0],[213,0]]
records.each { |record| raise 'Native GDS mapping collision' unless (record['layers'] & custom).empty? }
File.write($report, JSON.pretty_generate({'schema' => 'block-v1-native-gds-audit/1',
  'records' => records, 'custom_layers' => custom,
  'scope' => 'Actual GDS layer use only; declared native layer maps need separate comparison'}) + "\n")
