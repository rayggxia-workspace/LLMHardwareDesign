from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-upper-metal-guard-v1';p.mkdir(exist_ok=False)
(p/'export.tcl').write_text('''read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb
set db [ord::get_db]
set f [open master-geometry.tsv w]
foreach name {r_stream_local local_s_base} {
set m [$db findMaster $name]
puts $f "MASTER\t$name\t[$m getWidth]\t[$m getHeight]"
foreach box [$m getObstructions] {
set layer [[$box getTechLayer] getName]
if {$layer in {metal7 metal8 metal9 metal10}} {puts $f [join [list OBS $name $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}
}
foreach mt [$m getMTerms] {foreach mp [$mt getMPins] {foreach box [$mp getGeometry] {
set layer [[$box getTechLayer] getName]
if {$layer in {metal7 metal8 metal9 metal10}} {puts $f [join [list PIN $name $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$mt getName]] "\t"]}
}}}
}
close $f
''')
(p/'derive.py').write_text('''from pathlib import Path
import pya,json,hashlib,collections
p=Path.cwd();r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');g=r/'cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds';l=pya.Layout();l.read(str(g));assert abs(l.dbu-0.0005)<1e-12,l.dbu
regions={};size={}
for s in (p/'master-geometry.tsv').read_text().splitlines():
 a=s.split('\\t')
 if a[0]=='MASTER':size[a[1]]=list(map(int,a[2:]));continue
 k,n,layer,*v=a;regions.setdefault((k,n,layer),pya.Region()).insert(pya.Box(*map(int,v[:4])))
rows=[];stats=[]
for n in size:
 c=l.cell(n);assert c
 for layer,lnum in [('metal7',23),('metal8',25),('metal9',27),('metal10',29)]:
  actual=pya.Region(c.begin_shapes_rec(l.layer(lnum,0))).merged();obs=regions.get(('OBS',n,layer),pya.Region());pins=regions.get(('PIN',n,layer),pya.Region());missing=(actual-obs-pins).merged();parts=missing.decompose_trapezoids_to_region();count=0;recovered=pya.Region()
  for poly in parts.each():
   b=poly.bbox();assert b.area()==poly.area();assert b.left>=0 and b.bottom>=0 and b.right<=size[n][0] and b.top<=size[n][1];rows.append((n,layer,b.left,b.bottom,b.right,b.top));recovered.insert(b);count+=1
  assert (recovered^missing).is_empty() and (recovered&pins).is_empty();stats.append(dict(master=n,layer=layer,new_rectangles=count,missing_area_um2=missing.area()*l.dbu*l.dbu))
(p/'missing-metal.tsv').write_text(''.join('\\t'.join(map(str,x))+'\\n' for x in rows));v=dict(scope='Exact actual macro M7-M10 material missing from installed OBS, excluding actual master port rectangles; no GDS/pin edit, no signoff acceptance',stats=stats,rectangles=len(rows),source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [g,p/'master-geometry.tsv',p/'missing-metal.tsv',Path(__file__)]});(p/'receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
''')
s=(r/'audit/c-main-material.sbatch').read_text();s=s[:s.index('set -euo pipefail')]+'''set -euo pipefail
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-upper-metal-guard-v1
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit export.tcl > export.log 2>&1; klayout -b -r derive.py > derive.log 2>&1'
''';(p/'run.sbatch').write_text(s.replace('yzl-C-material','yzl-C-metalguard').replace('C-material-%j.log','C-metalguard-%j.log'))
