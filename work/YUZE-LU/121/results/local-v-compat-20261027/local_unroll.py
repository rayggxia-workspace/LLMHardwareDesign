import re
from pathlib import Path
p=Path('project/rtl/block_library_v1/block_v1_v_function.sv');text=p.read_text()
start='   for(l=0;l<2;l=l+1)begin\n';end='\n   end\n  end\n end\nendmodule\n'
assert text.count(start)==1 and text.endswith(end)
before,body=text.split(start);body=body[:-len(end)]
result=before+'\n'.join('   begin\n'+re.sub(r'\bl\b',str(l),body)+'\n   end' for l in range(2))+'\n  end\n end\nendmodule\n'
Path('.local/issue121/function-local.sv').write_text(result)
