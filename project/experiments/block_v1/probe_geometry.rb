# Independent KLayout LEF/DEF -> GDS readback and integer geometry checks.
# This is the declared research extension's access fixture, not a foundry deck.
require 'json'
technology = RBA::Technology.new
technology.load($lyt)
options = technology.load_layout_options
options.lefdef_config.lef_files = [$tech_lef, $landing_lef]
def load_regions(path, options, gds)
  layout = RBA::Layout.new
  layout.read(path, options)
  layout.write(gds)
  checked = RBA::Layout.new
  checked.read(gds)
  top = checked.top_cell
  regions = {}
  {'metal10'=>[29,0], 'via10'=>[210,0], 'metal11'=>[211,0], 'via11'=>[212,0], 'metal12'=>[213,0]}.each do |name,pair|
    layer = checked.find_layer(*pair)
    regions[name] = layer.nil? ? RBA::Region.new : RBA::Region.new(top.begin_shapes_rec(layer)).merged
  end
  [checked.dbu, regions]
end
dbu, reference = load_regions($unrouted, options, $out+'/unrouted.gds')
dbu_after, original = load_regions($routed, options, $out+'/routed.gds')
raise 'Readback units changed' unless dbu == dbu_after
unit = lambda { |um| (um/dbu).round }
point = lambda { |x,y| RBA::Point.new(unit.call(x),unit.call(y)) }
labels = {'link'=>[['metal10',point.call(34.4,34.4)],['metal10',point.call(136.8,136.8)]]}
def geometry_errors(regions, reference, unit, labels)
  errors = []
  errors << 'FIXED_M10' unless (regions['metal10'] ^ reference['metal10']).is_empty?
  ['metal11','metal12'].each do |name|
    errors << 'WIDTH' unless regions[name].width_check(unit.call(0.8)).is_empty?
    errors << 'SPACING' unless regions[name].space_check(unit.call(0.8)).is_empty?
    errors << 'NOTCH' unless regions[name].notch_check(unit.call(0.8)).is_empty?
  end
  [['via10','metal10','metal11'],['via11','metal11','metal12']].each do |cut,lower,upper|
    errors << 'CUT_WIDTH' unless regions[cut].width_check(unit.call(0.6)).is_empty?
    errors << 'CUT_SPACING' unless regions[cut].space_check(unit.call(0.6)).is_empty?
    # Minkowski enclosure check includes corners; no M10 landing patch.
    enclosure = regions[cut].sized(unit.call(0.1))
    errors << 'ENCLOSURE' unless (enclosure-regions[lower]).is_empty? && (enclosure-regions[upper]).is_empty?
  end
  nodes=[];by_layer={}
  ['metal10','metal11','metal12'].each do |layer|
    by_layer[layer]=[]
    regions[layer].each do |polygon|
      by_layer[layer] << nodes.length
      nodes << [layer,polygon]
    end
  end
  parents=(0...nodes.length).to_a
  find = lambda do |i|
    i=parents[i] while parents[i]!=i
    i
  end
  [['via10','metal10','metal11'],['via11','metal11','metal12']].each do |cut,lower,upper|
    regions[cut].each do |polygon|
      center=polygon.bbox.center
      a=by_layer[lower].find { |i| nodes[i][1].inside(center) }
      b=by_layer[upper].find { |i| nodes[i][1].inside(center) }
      if a.nil? || b.nil?
        errors << 'OPEN_VIA'
      else
        parents[find.call(a)]=find.call(b)
      end
    end
  end
  names={}
  labels.each do |name,terminals|
    roots=[]
    terminals.each do |layer,location|
      i=by_layer[layer].find { |k| nodes[k][1].inside(location) }
      if i.nil?
        errors << 'OPEN_PIN'
      else
        root=find.call(i);roots << root;(names[root] ||= []) << name
      end
    end
    errors << 'OPEN_NET' unless roots.uniq.length==1
  end
  names.each_value { |nets| errors << 'SHORT' if nets.uniq.length>1 }
  errors << 'FLOATING' unless parents.map { |i| find.call(i) }.uniq.sort==names.keys.sort
  errors.uniq
end
checks=[]
def clone_regions(regions)
  regions.transform_values { |region| region.dup }
end
verify = lambda do |name,regions,expected,terminals=labels|
  errors=geometry_errors(regions,reference,unit,terminals)
  raise "#{name}: unexpected #{errors}" if expected.nil? ? !errors.empty? : !errors.include?(expected)
  checks << {'name'=>name,'errors'=>errors,'expected_rejection'=>expected}
end
verify.call('actual-routed-readback',original,nil)
thin=clone_regions(original)
thin['metal11'].insert(RBA::Box.new(unit.call(50),unit.call(150),unit.call(60),unit.call(150.4)))
verify.call('thin-wire',thin,'WIDTH')
close=clone_regions(original)
close['metal12'].insert(RBA::Box.new(unit.call(137.6),unit.call(50),unit.call(138.4),unit.call(60)))
verify.call('too-close-wire',close,'SPACING')
missing=clone_regions(original)
cuts=[];missing['via11'].each { |polygon| cuts << polygon }
raise 'Expected two via11 cuts' unless cuts.length==2
missing['via11'] -= RBA::Region.new(cuts.first)
verify.call('missing-via',missing,'OPEN_NET')
offset=clone_regions(original)
cuts=[];offset['via10'].each { |polygon| cuts << polygon }
offset['via10'] -= RBA::Region.new(cuts.first)
offset['via10'].insert(cuts.first.transformed(RBA::Trans.new(unit.call(0.2),0)))
verify.call('via-enclosure',offset,'ENCLOSURE')
# A real additional isolated conductor, then a physical bridge to short it.
separate=clone_regions(original)
separate['metal12'].insert(RBA::Box.new(unit.call(141),unit.call(50),unit.call(141.8),unit.call(100)))
two_labels=labels.merge('other'=>[['metal12',point.call(141.4,80)]])
verify.call('two-isolated-nets',separate,nil,two_labels)
bridged=clone_regions(separate)
bridged['metal12'].insert(RBA::Box.new(unit.call(136.8),unit.call(79.6),unit.call(141.4),unit.call(80.4)))
bridged['metal12']=bridged['metal12'].merged
verify.call('physical-short',bridged,'SHORT',two_labels)
File.write($out+'/geometry-check.json',JSON.pretty_generate({'schema'=>'block-v1-probe-geometry/1',
  'dbu_um'=>dbu,'native_m10_mask_union_unchanged'=>true,'checks'=>checks,
  'scope'=>'Independent access-fixture research geometry/connectivity only; full native/new-layer deck and RC still separate'})+"\n")
puts 'PASS_INDEPENDENT_RESEARCH_ACCESS_GEOMETRY'
