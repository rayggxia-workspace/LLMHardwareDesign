from pathlib import Path
import json
p=Path(__file__).parent
for n in range(2048):
 q=(n*683)>>11
 assert q==n//3 and n-3*q==n%3
s=(p/'loader-original.sv').read_text()
helper=''' function automatic [10:0] div3_exact(input [10:0] index);
  reg [20:0] product;
  begin product=index*21'd683;div3_exact={1'b0,product[20:11]};end
 endfunction
 function automatic [2:0] mod3_exact(input [10:0] index);
  reg [10:0] q,r;
  begin q=div3_exact(index);r=index-(q+(q<<1));mod3_exact=r[2:0];end
 endfunction
'''
s=s.replace(' function automatic [10:0] row_of',helper+' function automatic [10:0] row_of')
assert s.count("index/11'd3")==1 and s.count("3'(index%11'd3)")==1
s=s.replace("index/11'd3",'div3_exact(index)').replace("3'(index%11'd3)",'mod3_exact(index)')
(p/'loader-arithmetic-only.sv').write_text(s)
(p/'div3-only-exhaustive.json').write_text(json.dumps({'tested_inputs':2048,'failures':0,'input_width':11,'product_width':21,'formula':'q=(index*683)>>11;r=index-3*q'})+'\n')
