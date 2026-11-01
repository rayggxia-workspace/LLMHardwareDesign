"""One simultaneous full-inventory pin/escape plan, four directional strips.

This is a declared candidate until actual native P&R and readback pass. Metal11
horizontal left/right strips avoid the two metal11 landing rows for vertical
metal12 top/bottom escapes. No port is omitted or serialized.
"""
import json,math
from pathlib import Path
from revision300_geometry import u,box,verify,DBU


def generate(ports,side,technology):
    g=technology['geometry_um'];ox=u(g['track_offset_x']);oy=u(g['track_offset_y']);step=u(8)
    width=u(side)
    def nearest(v,offset):return offset+step*round((v-offset)/step)
    xl=nearest(width/3,ox);xr=nearest(2*width/3,ox)
    yb=nearest(width/3,oy);yt=nearest(2*width/3,oy)
    xx=list(range(ox+step*math.ceil((u(24)-ox)/step),width-u(24),step))
    yy=[v for v in range(oy+step*math.ceil((u(24)-oy)/step),width-u(24),step)if abs(v-yb)>=u(8)and abs(v-yt)>=u(8)]
    slots={'left':yy,'right':yy,'bottom':xx,'top':xx};used={k:0 for k in slots}
    pins=[];connections=[];shapes=[];groups=[]
    def add(layer,b,net):shapes.append(dict(layer=layer,box_dbu=list(map(int,b)),net=net))
    def wire(layer,a,b,net):add(layer,[min(a[0],b[0])-u(1),min(a[1],b[1])-u(1),max(a[0],b[0])+u(1),max(a[1],b[1])+u(1)],net)
    # Keep each bus chunk physically contiguous, with at most sixteen pins.
    # Alternate sides within direction to use actual distinct track capacities.
    hgroup=vgroup=0
    for port,p in sorted(ports.items()):
        count=p['bits'];assert count>0 and p['direction']in ('input','output')
        direction='H'if p['direction']=='input'else'V'
        for begin in range(0,count,16):
            n=min(16,count-begin)
            if direction=='H':side_name=('left','right')[hgroup%2];hgroup+=1
            else:side_name=('bottom','top')[vgroup%2];vgroup+=1
            assert used[side_name]+n<=len(slots[side_name]),('Insufficient full-port tracks; enlarge native footprint',side,port,side_name)
            group_id='%s-%d'%(port,begin//16);groups.append(dict(id=group_id,port=port,first=begin,bits=n,side=side_name,direction=direction))
            for i in range(begin,begin+n):
                track=slots[side_name][used[side_name]];used[side_name]+=1
                net=port if count==1 else '%s[%d]'%(port,i)
                if direction=='H':
                    x=xl if side_name=='left'else xr;y=track
                    end=[ox-u(32)if side_name=='left'else ox+step*math.ceil(width/step)+u(32),y]
                else:
                    x=track;y=yb if side_name=='bottom'else yt
                    end=[x,oy-u(32)if side_name=='bottom'else oy+step*math.ceil(width/step)+u(32)]
                pins.append(dict(pin=net,port=port,index=i,direction=p['direction'],role='clock'if port=='clk'else'signal',layer='metal10',
                                 xy_um=[x/DBU,y/DBU],size_um=[2.,2.],region='internal',group=group_id,escape_side=side_name))
                add('metal10',box(x,y),net);add('via10',box(x,y),net)
                if direction=='H':wire('metal11',[x,y],end,net)
                else:
                    add('metal11',box(x,y),net);add('via11',box(x,y),net);wire('metal12',[x,y],end,net)
                connections.append(dict(net=net,source_m10_dbu=[x,y],external_endpoint_dbu=end,endpoint_layer='metal11'if direction=='H'else'metal12'))
    fixture=dict(schema='coarse-interface-fixture/1',name='all-ports',expected_bits=len(pins),dbu_per_um=DBU,
                 macro_box_dbu=[0,0,width,width],test_boundary_dbu=[-u(40),-u(40),width+u(40),width+u(40)],ports=connections,shapes=shapes)
    proof=verify(fixture,technology)
    plan=dict(schema='block-v1-pin-plan/1',policy='coarse-four-direction-strips-v1',pins=pins,ports=len(pins),internal_ports=len(pins),
              groups=groups,track_capacity={k:len(v)for k,v in slots.items()},track_demand=used,qualified_access=False,
              scope='Exact candidate M10 rectangles and simultaneous external coarse paths; actual native reconnection/DRC/RC/readback not yet accepted')
    return plan,fixture,proof


def independent(root,out,fixture,run):
    folder=root/'project/experiments/block_v1'
    (out/'all-ports.json').write_text(json.dumps(fixture,indent=2)+'\n')
    manifest=[dict(name='all-ports',json_path=str(out/'all-ports.json'),gds_path=str(out/'all-ports.gds'))]
    (out/'fixtures.json').write_text(json.dumps(manifest,indent=2)+'\n')
    script=(folder/'revision300_klayout.py').read_text().replace('FIXTURE_MANIFEST_PLACEHOLDER',str(out/'fixtures.json'))
    (out/'coarse_check.py').write_text(script)
    run(['klayout','-b','-r',out/'coarse_check.py'],'coarse-check.log')
    observed=json.loads((out/'klayout-results.json').read_text());assert observed['passed']
    return observed
