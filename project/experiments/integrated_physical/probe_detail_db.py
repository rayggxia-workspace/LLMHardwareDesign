"""Read-only actual detailed ODB shape API and net wire inventory probe."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);artifacts(a.stage)
s=a.out/'odb_probe.py';s.write_text("import odb,json\n"+f"db=odb.dbDatabase.create();odb.read_db(db,{str(a.stage/'final.odb')!r});b=db.getChip().getBlock()\n"+"n=next(n for n in b.getNets() if n.getWire() is not None);it=odb.dbWireShapeItr();it.begin(n.getWire());q=odb.dbShape();assert it.next(q)\n"+"d={'net':n.getName(),'wire_methods':[x for x in dir(n.getWire())if not x.startswith('_')],'shape_methods':[x for x in dir(q)if not x.startswith('_')],'is_via':q.isVia(),'nets':len(b.getNets()),'insts':len(b.getInsts())}\n"+f"open({str(a.out/'odb-api.json')!r},'w').write(json.dumps(d,indent=2))\n")
command(a.out,'odb-probe',[OR,'-python',s],120);manifest(a.out,{'status':'READONLY_DETAILED_ODB_API_CAPTURED','source':sources(),'resources':resource_snapshot(),'stage_manifest_sha256':sha(a.stage/'manifest.json')});print('READONLY_DETAILED_ODB_API_CAPTURED')
