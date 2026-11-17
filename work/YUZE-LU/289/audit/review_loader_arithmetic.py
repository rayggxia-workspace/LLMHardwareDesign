"""Independent exact substitution binding and finite-domain arithmetic audit."""
import hashlib,json
from pathlib import Path
p=Path(__file__).parent
original=p.parent/'cu/loader-original.sv'
a=original.read_text()
helper=''' function automatic [10:0] div3_exact(input [10:0] index);
  reg [20:0] product;
  begin product=index*21'd683;div3_exact={1'b0,product[20:11]};end
 endfunction
 function automatic [2:0] mod3_exact(input [10:0] index);
  reg [10:0] q,r;
  begin q=div3_exact(index);r=index-(q+(q<<1));mod3_exact=r[2:0];end
 endfunction
'''
old="bb+({48'd0,f}+64'(row_of(flat(word_index,lane))))*bst+64'(col_of(flat(word_index,lane)))*cst"
new="bb+({48'd0,f}*{32'd0,bst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst})"
records={}
for filename,distributed in [('loader-arithmetic-only-reviewed.sv',False),('loader-distributed-reviewed.sv',True),('loader-distributed-parallel-reviewed.sv',True)]:
    path=p/filename;b=path.read_text()
    assert b.count(helper)==1
    b=b.replace(helper,'')
    assert b.count('3:row_of=div3_exact(index);')==1
    assert b.count('3:col_of=mod3_exact(index);')==1
    b=b.replace('3:row_of=div3_exact(index);',"3:row_of=index/11'd3;")
    b=b.replace('3:col_of=mod3_exact(index);',"3:col_of=3'(index%11'd3);")
    if distributed:
        assert b.count(new)==1;b=b.replace(new,old)
    reference=p.parent/'cu/loader-parallel.sv' if filename=='loader-distributed-parallel-reviewed.sv' else original
    assert b==reference.read_text(),filename
    records[filename]={'raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'inverse_substitution_exact_to_reference':True,'reference':str(reference),'reference_raw_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()}
for i in range(2048):
    prod=(i*683)&((1<<21)-1)
    q=prod>>11
    r=(i-((q+((q<<1)&2047))&2047))&2047
    assert q==i//3 and r==i%3
report={'scope':'two-state source-level exact arithmetic substitutions; not whole-module SAT, X propagation, or physical signoff','original_raw_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'candidates':records,'div3_exhaustive_inputs':2048,'div3_failures':0,'distribution_basis':'Unsigned arithmetic in Z/(2^64); original sum is explicitly64bit and context extends32bit strides; new operands all explicitly64bit. Distributivity holds for every operand, including overflow.'}
(p/'LOADER-ARITHMETIC-REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
