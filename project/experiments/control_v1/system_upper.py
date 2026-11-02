"""Route every extracted control_system boundary net on research M11/M12.

Route candidates are separate from actual GDS/ODB readback and full RC/STA.
No candidate alone grants physical-composition acceptance.
"""
import argparse,hashlib,json,math,os,time
from pathlib import Path
from tree_router import route


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,job=os.environ['SLURM_JOB_ID'],inputs={},whole_system_qualified=False)
    try:
        m=json.loads(a.manifest.read_text());g=json.loads(a.graph.read_text())
        assert g['passed'] and g['no_unassigned_active_logic'] and not g['R_instantiated']
        assert len(m['leaves'])==19 and len(g['instances'])==25
        receipt['inputs']={str(a.manifest):sha(a.manifest),str(a.graph):sha(a.graph),str(Path(__file__)):sha(Path(__file__)),
                           str(Path(__file__).with_name('tree_router.py')):sha(Path(__file__).with_name('tree_router.py'))}
        plans={}
        for name,row in m['leaves'].items():
            path=Path(row['pins']);assert sha(path)==row['pins_sha256']
            assert g['inputs'][str(path)]==row['pins_sha256']
            receipt['inputs'][str(path)]=sha(path)
            plans[name]={pin['pin']:pin for pin in json.loads(path.read_text())['pins']}
        gap=[32,64,96][a.seed%3]
        rows=[1,2,3,4,5,6,0]
        if a.seed>=3:rows=list(reversed(rows))
        placement={};y=128
        def align(v):return 4*math.ceil(v/4)
        def put(name,x,y):
            assert name in g['instances'] and name not in placement
            placement[name]=[align(x),align(y)]
            return m['leaves'][g['instances'][name]]['die_um']
        # Each queue, adapter and native compute/storage leaf has one explicit
        # physical instance. No block is resized or geometrically modified.
        for role in rows:
            x=128;height=0
            names=['queue_'+str(role),'endpoint_'+str(role)]
            if role in (1,2,3,4):names+=['macro_'+str(role)]
            elif role==5:names+=['macro_s','s_port']
            elif role==6:names+=['macro_t']
            for name in names:
                w,h=put(name,x,y);x=align(x+w+gap);height=max(height,h)
            y=align(y+height+gap)
        x=128
        for name in ('host','controller','routes','system_status'):
            w,h=put(name,x,y);x=align(x+w+gap)
        assert set(placement)==set(g['instances'])
        width=align(max(x+m['leaves'][g['instances'][n]]['die_um'][0] for n,(x,y) in placement.items())+128)
        height=align(max(y+m['leaves'][g['instances'][n]]['die_um'][1] for n,(x,y) in placement.items())+128)
        for n,(x,y) in placement.items():
            w,h=m['leaves'][g['instances'][n]]['die_um']
            for other,(xx,yy) in placement.items():
                if n>=other:continue
                ww,hh=m['leaves'][g['instances'][other]]['die_um']
                assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y,('Overlapping frozen leaves',n,other)
        def point(end):
            name=end['instance'];pin=plans[g['instances'][name]][end['pin']]
            if 'xy_um' in pin:x,y=pin['xy_um']
            else:
                b=pin['box_dbu'];x=(b[0]+b[2])/4000;y=(b[1]+b[3])/4000
            dx,dy=placement[name];gx=(x+dx-.095)/4;gy=(y+dy-.07)/4
            assert abs(gx-round(gx))<1e-7 and abs(gy-round(gy))<1e-7,(name,end['pin'],x,y)
            return round(gx),round(gy)
        nx,ny=int(width/4),int(height/4)
        border=[(x,8) for x in range(8,nx-8)]+[(nx-8,y) for y in range(9,ny-8)]+[(x,ny-8) for x in range(nx-9,7,-1)]+[(8,y) for y in range(ny-9,8,-1)]
        top_pins=sorted({e['pin'] for c in g['connections'].values() for e in [c['driver'],*c['sinks']] if e['instance']=='TOP'})
        assert len(top_pins)<len(border)
        external={pin:border[(i*len(border))//len(top_pins)] for i,pin in enumerate(top_pins)}
        terminals={}
        for bit,c in g['connections'].items():
            terminals['net_'+bit]=[external[e['pin']] if e['instance']=='TOP' else point(e) for e in [c['driver'],*c['sinks']]]
        (a.out/'placement.json').write_text(json.dumps(dict(placements_um=placement,width_um=width,height_um=height,
             external_grid_pins=external,terminals=terminals,graph=str(a.graph),graph_sha256=sha(a.graph)),indent=2)+'\n')
        def progress(row):
            row['unix_time']=time.time();(a.out/'progress.json').write_text(json.dumps(row)+'\n')
            print(json.dumps(row),flush=True)
        branches,proof=route(terminals,nx,ny,seed=a.seed,progress=progress)
        (a.out/'trees.json').write_text(json.dumps(branches)+'\n')
        (a.out/'search.json').write_text(json.dumps(proof,indent=2)+'\n')
        receipt.update(passed=True,net_count=len(terminals),instance_count=25,search=proof,
                       scope='All extracted signal, clock and reset boundary nets routed as connected disjoint grid trees. Actual geometry readback, PG and combined timing remain separate mandatory gates.')
    finally:
        receipt['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
