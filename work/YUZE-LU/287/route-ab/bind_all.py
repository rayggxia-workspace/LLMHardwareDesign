import pathlib,json,re,csv,hashlib,collections
P=pathlib.Path;root=P(__file__).resolve().parent
source=P('/public/home/yuzelu/project-circuit/issue287-route-ab-20261117')
inv=json.loads((root/'inventory.json').read_text());endpoints={j['driver'] for j in inv}|{s for j in inv for s in j['sinks']}
bound={e:[] for e in endpoints}
for fam in ['C','U']:
 with (source/(fam+'-ports.tsv')).open() as f:
  for r in csv.DictReader(f,delimiter='\t'):
   e=fam+'0.'+r['port']
   if e in bound:bound[e].append(dict(instance=r['instance'],master=r['master'],pin=r['pin'],direction=r['pin_direction'],net=r['net']))
for line in P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/C-pins.tsv').read_text().splitlines():
 a=line.split('\t')
 if len(a)>=4 and a[1] in ['block_v2_g','g_s32']:
  e='C0.G.'+a[2]
  if e in bound:
   item=dict(instance=a[0],master=a[1],pin=a[2],direction=a[3])
   if item not in bound[e]:bound[e].append(item)
fmeta=json.loads(P('/public/home/yuzelu/project-circuit/algo2-current-blocks-20261116/physical-binding/F0-macro-components.json').read_text())['endpoints']
flookup={}
for line in P('/public/home/yuzelu/project-circuit/algo2-current-blocks-20261116/physical-binding/F-native-all.tsv').read_text().splitlines():
 a=line.split('\t')
 if a[0]=='ITERM':flookup[a[2]+'/'+a[3]]=dict(instance=a[2],master=a[5],pin=a[3],direction=a[4],net=a[1])
for e in endpoints:
 if e.startswith('F0.S.'):
  m=fmeta[e];bound[e]=[dict(flookup[m['physical_macro_term']],existing_parent_terms=m.get('parent_physical_terms',[]))]
native={}
if (root/'G-native-terms.tsv').exists():
 with (root/'G-native-terms.tsv').open() as f:
  for row in csv.DictReader(f,delimiter='\t'):
   e=row.pop('endpoint');native.setdefault(e,[]).append(row)
for e in endpoints:
 if e.startswith('F0.S.'):
  native[e]=[dict(t) for t in flookup.values() if t['net']==bound[e][0]['net']]
libs=[P('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')]
for f in ['C','U']:
 config=P('/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116')/f/'config.mk'
 libs += [P(p) for p in re.search(r'^export ADDITIONAL_LIBS\s*=\s*(.*)$',config.read_text(),re.M)[1].split()]
def blocks(s,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(\s*"?([^"()]+?)"?\s*\)\s*\{',s):
  start=m.end();i=start;depth=1
  while depth:
   depth+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip(),s[start:i-1]
required={(b['master'],b['pin']) for bs in list(bound.values())+list(native.values()) for b in bs};model={};lhash={}
for p in dict.fromkeys(libs):
 s=p.read_text();lhash[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.]+)\s*,\s*(ff|pf)\s*\)',s,re.I);assert unit,str(p)
 capscale=float(unit[1])*(1000 if unit[2].lower()=='pf' else 1)
 for cell,content in blocks(s,'cell'):
  if not any(k[0]==cell for k in required):continue
  for pin,ps in blocks(content,'pin'):
   if (cell,pin) not in required:continue
   item={'lib':str(p)}
   for key in ['capacitance','max_capacitance','max_transition']:
    m=re.search(r'\b'+key+r'\s*:\s*([\d.eE+-]+)',ps)
    if m:item[key]=float(m[1])*(capscale if key!='max_transition' else 1)
   model[cell,pin]=item
for e,bs in bound.items():
 for b in bs:b['model']=model.get((b['master'],b['pin']))
for e,bs in native.items():
 for b in bs:b['model']=model.get((b['master'],b['pin']))
(root/'endpoint-binding.json').write_text(json.dumps(dict(endpoints=bound,native_macro_nets=native,lib_sha256=lhash),indent=2))
print(json.dumps({'endpoints':len(bound),'unbound':[e for e,b in bound.items() if not b],'missing_models':[(e,b['master'],b['pin']) for e,bs in bound.items() for b in bs if not b['model']]},indent=2))
