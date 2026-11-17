import pathlib,re,json,hashlib
p=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');s=p.read_text()
def block(text,pattern):
 m=re.search(pattern,text);start=text.index('{',m.start());depth=1;i=start+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start+1:i-1]
out={'lib':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'units':re.findall(r'(?:time_unit|capacitive_load_unit)[^;]*;',s)}
for cell,pin in [('BUF_X1','Z'),('BUF_X4','A')]:
 c=block(s,r'cell\s*\(\s*'+cell+r'\s*\)');b=block(c,r'pin\s*\(\s*'+pin+r'\s*\)')
 out[cell+'/'+pin]={k:re.findall(r'\b'+k+r'\s*:\s*([^;]+)',b) for k in ['direction','capacitance','max_capacitance','max_transition']}
print(json.dumps(out,indent=2))
