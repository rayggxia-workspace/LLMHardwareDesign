# Native OpenDB read-only analysis. No write_db or geometry mutation.
from pathlib import Path
from collections import Counter,defaultdict
import os,json,hashlib,math
import odb
source=Path(os.environ['INPUT_ODB']);out=Path(os.environ['OUTPUT_JSON']);before=hashlib.sha256(source.read_bytes()).hexdigest();db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock();units=block.getDbUnitsPerMicron()
ranks=[];selected={};points={};wire_api=[n for n in dir(odb.dbWire)if not n.startswith('_')];shape_api=[n for n in dir(odb.dbShape)if not n.startswith('_')]
for net in block.getNets():
 if str(net.getSigType())in ['POWER','GROUND','CLOCK']:continue
 loads=[t for t in net.getITerms()if str(t.getMTerm().getIoType())!='OUTPUT'];ranks.append((len(loads),net))
for _,net in sorted(ranks,key=lambda x:x[0],reverse=True)[:20]:selected[net.getName()]=net
for name in ['role','bank_role','rd_index[0]','rd_index[1]','rd_index[2]','issue_row[0]','issue_row[1]','issue_row[2]']:
 n=block.findNet(name)
 if n:selected[name]=n
rows=[]
for name,net in selected.items():
 loads=[t for t in net.getITerms()if str(t.getMTerm().getIoType())!='OUTPUT'];xy=[tuple(v/units for v in t.getInst().getLocation())for t in loads];bins=Counter((int(x//128),int(y//128))for x,y in xy);wire=net.getWire();r=dict(net=name,direct_loads=len(loads),load_types=dict(Counter(t.getInst().getMaster().getName()+'/'+t.getMTerm().getName()for t in loads)),occupied_128um_bins=len(bins),groups_max256_per_bin=sum(math.ceil(v/256)for v in bins.values()),bbox_cell_origins_um=[min((p[0]for p in xy),default=0),min((p[1]for p in xy),default=0),max((p[0]for p in xy),default=0),max((p[1]for p in xy),default=0)],routed_wire_present=bool(wire));points[name]=xy
 if wire:
  try:r['wire_getLength_raw']=wire.getLength()
  except Exception as e:r['wire_length_error']=str(e)
  if hasattr(odb,'dbWireShapeItr'):
   try:
    it=odb.dbWireShapeItr();it.begin(wire);shape=odb.dbShape();layers=Counter();areas=Counter()
    while it.next(shape):
     if not shape.isVia():
      box=shape.getBox();layer=shape.getTechLayer().getName();layers[layer]+=1;areas[layer]+=box.dx()*box.dy()/units/units
    r['wire_rectangle_counts_by_layer']=dict(layers);r['sum_wire_rectangle_area_um2_by_layer']=dict(areas)
   except Exception as e:r['shape_error']=str(e)
 rows.append(r)
after=hashlib.sha256(source.read_bytes()).hexdigest();assert before==after
out.write_text(json.dumps(dict(odb=str(source),odb_sha256=before,unchanged=True,dbu_per_um=units,wire_api=wire_api,shape_api=shape_api,nets=rows,load_cell_origins=points,instance_counts=dict(Counter(i.getMaster().getName()for i in block.getInsts()))),indent=2)+'\n')
