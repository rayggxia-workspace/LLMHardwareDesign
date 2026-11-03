"""Conservative placement search guard from the exact fixed-clock DEF paths.

This is a candidate-selection heuristic, never a DRC/STA acceptance substitute.
All low-metal wire/via projected envelopes near each search window are retained.
"""
from pathlib import Path
import re

def clock_access_boxes(source,dbu,cells,sites,rows):
    path=Path(source)/'CLOCK_FIXED.def'
    radius=(dbu+4)//5  # 0.20um conservative envelope, not a rule threshold.
    windows=[]
    # Nangate45's actual pitch/height are checked by the native consumer below.
    for cell in cells.values():
        x,y=map(int,cell['location'].split())
        windows.append((x-(sites+32)*380,y-(rows+2)*2800,x+(sites+32)*380,y+(rows+2)*2800))
    boxes=[];nets=0;paths=0
    for line in path.open():
        if not line.startswith('- '):continue
        nets+=1;parts=re.split(r'\s+(?:\+\s+FIXED|NEW)\s+',line.strip())
        assert len(parts)>1 and '+ USE CLOCK' in parts[0]
        name=parts[0].split()[1];assert not any(c in name for c in '{}\t\r\n')
        for fragment in parts[1:]:
            words=fragment.split();assert re.fullmatch(r'metal(?:[1-9]|10)',words[0])
            metal=int(words[0][5:]);points=re.findall(r'\(\s*([^()]*)\)',fragment)
            assert len(points) in [1,2]
            parsed=[]
            for values in points:
                values=values.split();assert len(values) in [2,3]
                if len(values)==3:assert abs(int(values[2]))<=radius
                xy=[]
                for i,value in enumerate(values[:2]):
                    if value=='*':assert parsed;value=parsed[-1][i]
                    xy.append(int(value))
                parsed.append(xy)
            tail=re.sub(r'\([^()]*\)','',fragment).split()[1:]
            tail=[x for x in tail if x!=';']
            if len(points)==2:
                assert not tail and (parsed[0][0]==parsed[1][0] or parsed[0][1]==parsed[1][1])
                low=metal<=2
            else:
                assert len(tail)==1 and re.fullmatch(r'via[1-9]_\d+',tail[0])
                low=int(tail[0][3])<=2
            if not low:continue
            paths+=1;x0=min(x for x,y in parsed)-radius;y0=min(y for x,y in parsed)-radius
            x1=max(x for x,y in parsed)+radius;y1=max(y for x,y in parsed)+radius
            if any(x0<b[2] and x1>b[0] and y0<b[3] and y1>b[1] for b in windows):
                boxes.append((x0,y0,x1,y1,name,words[0]))
    assert nets>0 and paths>0 and boxes
    return boxes,dict(nets=nets,low_metal_paths=paths,nearby_envelopes=len(boxes),radius_dbu=radius,dbu=dbu,scope='Conservative XY low-metal clock wire/via envelope guard for placement search only. Full native/GDS/STA/PG gates mandatory; never a geometry or rule exclusion.')
