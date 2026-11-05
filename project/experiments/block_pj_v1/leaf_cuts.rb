# Export exact upper cut rectangles for conservative parent routing.
layout = RBA::Layout.new
layout.read($in_gds)
top = layout.top_cell
raise "Expected one leaf top" unless top
scale = layout.dbu * 2000
File.open($cut_rectangles, "w") do |out|
  {24 => "via7", 28 => "via9"}.each do |layer, name|
    index = layout.find_layer(layer, 0)
    raise "Missing cut layer #{name}" unless index
    boxes = []
    it = top.begin_shapes_rec(index)
    until it.at_end?
      unless it.shape.is_text?
        raise "Expected rectangular cut in #{it.cell.name}" unless it.shape.is_box?
        b = it.shape.bbox.transformed(it.trans)
        coords = [b.left, b.bottom, b.right, b.top].map do |v|
          scaled = scale * v
          raise "Cut is off the native DBU grid" if (scaled - scaled.round).abs > 1e-6
          scaled.round
        end
        boxes << coords
      end
      it.next
    end
    raise "No cuts on #{name}" if boxes.empty?
    boxes.uniq.sort.each { |coords| out.puts [name, *coords].join(" ") }
  end
end
