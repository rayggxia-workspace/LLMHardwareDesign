require 'json'
layout=RBA::Layout.new
layout.read($gds)
top=layout.top_cell
raise 'Wrong top' unless top.name=='block_v1_v'
li=layout.find_layer($layer.to_i,$datatype.to_i)
raise 'Missing actual metal2 layer' if li.nil?
box=RBA::Box.new(*[495,70,501,76].map { |x| (x/layout.dbu).round })
region=RBA::Region.new(top.begin_shapes_rec(li))
clipped=(region & RBA::Region.new(box)).merged
rows=[]
clipped.each do |polygon|
  holes=[]
  polygon.holes.times do |i| holes << polygon.each_point_hole(i).map { |p| [p.x,p.y] } end
  rows << {'hull'=>polygon.each_point_hull.map { |p| [p.x,p.y] },'holes'=>holes}
end
raise 'Empty actual metal2 window' if rows.empty?
File.write('gds-metal2-window.json',JSON.pretty_generate({'dbu_um'=>layout.dbu,'clipped_window_um'=>[495,70,501,76],'layer'=>[$layer.to_i,$datatype.to_i],'polygons'=>rows})+"\n")
