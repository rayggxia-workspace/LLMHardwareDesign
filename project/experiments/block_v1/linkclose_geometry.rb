require 'json'
request=JSON.parse(File.read($request))
spec=JSON.parse(File.read($spec))
aliases={};geometry={}
File.foreach($geometry) do |line|
  if line.start_with?('# NET ')
    _,_,key,encoded=line.split
    aliases[key]=[encoded].pack('H*');geometry[aliases[key]]=[]
  elsif !line.start_with?('#')
    key,layer,kind,*box=line.split
    geometry.fetch(aliases.fetch(key)) << [layer,kind,box.map(&:to_i)]
  end
end
regions={};all={};connectivity={};lengths={}
request.fetch('links').each do |link|
  name=link.fetch('id');shapes=geometry.fetch(name)
  raise 'Unexpected native routing layer' unless shapes.all?{|layer,kind,box| %w[metal10 via10 metal11 via11 metal12].include?(layer)}
  r={}
  shapes.each do |layer,kind,box|
    r[layer] ||= RBA::Region.new
    r[layer].insert(RBA::Box.new(*box))
    all[layer] ||= RBA::Region.new
    all[layer].insert(RBA::Box.new(*box))
  end
  r.transform_values!(&:merged)
  regions[name]=r
  # Every new M10 polygon must fit wholly inside the existing selected pins.
  native=RBA::Region.new
  shapes.select{|layer,kind,box|layer=='metal10' && kind=='instance-pin'}.each{|layer,kind,box|native.insert(RBA::Box.new(*box))}
  raise "M10 ownership violation #{name}" unless (r.fetch('metal10')-native).is_empty?
  %w[via10 via11].each do |cut|
    next unless r[cut]
    level=cut[3..].to_i
    %W[metal#{level} metal#{level+1}].each do |metal|
      raise "Via enclosure #{name} #{cut}" unless (r[cut]-r.fetch(metal)).is_empty?
    end
  end
  # Connectivity is checked independently from router status: each polygon
  # is a node, touching conductors in the same layer or across an actual cut
  # are adjacent. Both native terminal polygons must belong to one component.
  nodes=shapes.map{|layer,kind,box| [layer,RBA::Box.new(*box)]}
  adjacent=Array.new(nodes.size){[]}
  nodes.each_with_index do |(la,a),i|
    nodes.each_with_index do |(lb,b),j|
      next unless j<i
      same=la==lb
      via= (la.start_with?('via') && [la[3..].to_i,la[3..].to_i+1].map{|v|"metal#{v}"}.include?(lb)) ||
           (lb.start_with?('via') && [lb[3..].to_i,lb[3..].to_i+1].map{|v|"metal#{v}"}.include?(la))
      if (same||via) && a.touches?(b)
        adjacent[i]<<j;adjacent[j]<<i
      end
    end
  end
  seen={};todo=[0]
  until todo.empty?
    n=todo.pop;next if seen[n];seen[n]=true;todo.concat(adjacent[n])
  end
  raise "Disconnected route #{name}" unless seen.size==nodes.size
  connectivity[name]={'shapes'=>nodes.size,'components'=>1,'m10_preserved'=>true}
  # Wire area / nominal width gives centerline length after merging corners;
  # extraction uses DEF centerlines separately, never treats this as exact RC.
  lengths[name]=%w[metal11 metal12].sum{|l|r[l] ? r[l].area/4_000_000.0/2.0 : 0}
end
all.transform_values!(&:merged)
%w[via10 metal11 via11 metal12].each{|layer|all[layer] ||= RBA::Region.new}
spacing={}
%w[metal11 metal12 via10 via11].each do |layer|
  region=all.fetch(layer)
  distance=((layer.start_with?('via') ? 2.2 : 2.0)*2000).round
  width_errors=region.width_check(4000).size
  space_errors=region.space_check(distance).size
  spacing[layer]={'width_errors'=>width_errors,'spacing_errors'=>space_errors}
  raise "Research DRC #{layer}: #{spacing[layer]}" unless width_errors==0 && space_errors==0
end
keys=regions.keys
shorts=0
keys.each_with_index do |a,i|
  keys.take(i).each do |b|
    (regions[a].keys & regions[b].keys).each do |l|
      shorts+=1 unless (regions[a][l]&regions[b][l]).is_empty?
    end
  end
end
raise 'Cross-net short' unless shorts==0
layout=RBA::Layout.new;layout.dbu=0.0005;cell=layout.create_cell('representative_upper_interconnect')
%w[via10 metal11 via11 metal12].each do |layer|
  cell.shapes(layout.layer(*spec.fetch('gds').fetch(layer))).insert(all.fetch(layer))
end
layout.write('interconnect-upper.gds')
File.write($report,JSON.pretty_generate({'passed'=>true,'links'=>keys.size,'cross_net_shorts'=>shorts,
  'connectivity'=>connectivity,'research_drc'=>spacing,'native_m10_signal_metal_unchanged'=>true,
  'wire_area_equivalent_um'=>lengths,'scope'=>'Routed signal overlay only; independent native candidates retain their separate full acceptance. Top supply and common clock distribution are outside this finite experiment.'})+"\n")
