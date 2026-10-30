"""Installed KLayout decomposition API probe, not a physical-view qualification."""
import hashlib,json,os,datetime
from pathlib import Path
import pya

out=Path(os.environ['PINXY_OBS_PROBE_OUT'])
q={'scope':'INSTALLED_KLAYOUT_EXACT_RECTANGLE_UNION_DECOMPOSITION_API_PROBE_ONLY',
   'full_qualification':False,'klayout_version':pya.__version__,
   'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(Path(__file__).parent/'driver_commit.txt').read_text().strip()}
try:
    names=[n for n in dir(pya.Region) if 'decompos' in n or n in ['merged','xor','area']]
    q['actual_methods']=names
    method=getattr(pya.Region,'decompose_trapezoids_to_region')
    q['actual_decomposition_documentation']=method.__doc__
    region=pya.Region()
    for box in [(0,0,1000,200),(0,800,1000,1000),(0,200,200,800),(800,200,1000,800),(1000,0,1200,200)]:
        region.insert(pya.Box(*box))
    union=region.merged();pieces=union.decompose_trapezoids_to_region()
    rebuilt=pya.Region();boxes=[]
    for poly in pieces.each():
        b=poly.bbox();assert poly.area()==b.area()
        rebuilt.insert(b);boxes.append([b.left,b.bottom,b.right,b.top])
    q['actual_sample_boxes']=boxes
    q['sample_has_hole']=any(poly.holes()>0 for poly in union.each())
    q['exact_integer_XOR_empty']=(union^rebuilt).is_empty()
    q['sample_area_DBU2']=union.area()
    assert q['sample_has_hole'] and q['exact_integer_XOR_empty']
except Exception:
    import traceback
    q['actual_failure']=traceback.format_exc()
q['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'execution.json').write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps(q,indent=2))
