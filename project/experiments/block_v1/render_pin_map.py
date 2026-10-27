"""Render a static engineering SVG from actual exported ODB pin rectangles."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def render(index,pins,output):
    meta=json.loads(index.read_text(encoding='utf-8'));data=json.loads(pins.read_text(encoding='utf-8'))
    digest=hashlib.sha256(pins.read_bytes()).hexdigest();assert digest==meta['pins']['sha256']
    rows=data['pins'];w,h=meta['die_um'];assert len(rows)==meta['pins']['signal_bits']
    assert len({p['pin'] for p in rows})==len(rows)
    assert all(p['layer']=='metal10' and 0<=p['box_um'][0]<p['box_um'][2]<=w and 0<=p['box_um'][1]<p['box_um'][3]<=h for p in rows)
    groups={name:[p for p in rows if p['pin'].startswith(name+'[')] for name in ('cmd_data','rsp_data')}
    colors={'cmd_data':'#1769c2','rsp_data':'#c55209'}
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">',
         '<rect width="1200" height="760" fill="white"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#213348} .small{font-size:13px} .title{font-size:23px;font-weight:bold}</style>',
         '<text x="30" y="33" class="title">'+html.escape(meta['top'])+' — actual M10 signal pins</text>',
         '<text x="30" y="58" class="small">'+str(w)+' × '+str(h)+' µm; '+str(len(rows))+' actual boxes; signal pins only</text>']
    def box(p,ox,oy,scale,bottom,label=False):
        a,b,c,d=p['box_um'];name=p['pin'];group=next((key for key in colors if name.startswith(key+'[')),None)
        color=colors.get(group,'#a22468' if name=='clk' else '#16766b')
        x=ox+a*scale;y=oy+(bottom-d)*scale
        result='<rect x="%g" y="%g" width="%g" height="%g" fill="%s"><title>%s: %s µm</title></rect>'%(x,y,(c-a)*scale,(d-b)*scale,color,html.escape(name),html.escape(str(p['box_um'])))
        if label:
            index=re.search(r'\[(\d+)\]',name).group(1)
            result+='<text x="%g" y="%g" text-anchor="middle" font-size="8">%s</text>'%(x+(c-a)*scale/2,y-2,index)
        return result
    scale=min(610/w,610/h);ox=40;oy=85
    svg.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#f6f9fc" stroke="#506277"/>'%(ox,oy,w*scale,h*scale))
    svg.extend(box(p,ox,oy,scale,h) for p in rows)
    svg.append('<text x="40" y="718" class="small">Full macro; the two wide data buses occupy internal windows. Clock/control remain near the left edge.</text>')
    for k,key in enumerate(('cmd_data','rsp_data')):
        values=groups[key];assert values
        xmin=min(p['box_um'][0] for p in values)-3;xmax=max(p['box_um'][2] for p in values)+3
        ymin=min(p['box_um'][1] for p in values)-3;ymax=max(p['box_um'][3] for p in values)+3
        x0=760;y0=100+300*k;s=min(390/(xmax-xmin),235/(ymax-ymin))
        svg.append('<text x="760" y="%g" font-size="17" fill="%s">%s — %d real pins, enlarged</text>'%(y0-16,colors[key],key,len(values)))
        svg.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#f6f9fc" stroke="#a6b3c1"/>'%(x0,y0,(xmax-xmin)*s,(ymax-ymin)*s))
        svg.extend(box(p,x0-xmin*s,y0,s,ymax,True) for p in values)
        svg.append('<text x="760" y="%g" class="small">x %.3f..%.3f µm; y %.3f..%.3f µm</text>'%(y0+260,xmin,xmax,ymin,ymax))
    svg.append('<text x="30" y="746" class="small">Source pins.json SHA-256: '+digest+'</text>')
    svg.append('<metadata>'+html.escape(json.dumps(dict(source_index_sha256=hashlib.sha256(index.read_bytes()).hexdigest(),source_pins_sha256=digest,full_macro_pin_rectangles=len(rows),scope='Actual ODB signal pin locations; no routing/OBS or M11/M12 access qualification')) )+'</metadata></svg>')
    result='\n'.join(svg)+'\n';ET.fromstring(result)
    with output.open('w',encoding='utf-8',newline='\n') as stream:stream.write(result)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('index',type=Path);p.add_argument('pins',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();render(a.index,a.pins,a.output)
