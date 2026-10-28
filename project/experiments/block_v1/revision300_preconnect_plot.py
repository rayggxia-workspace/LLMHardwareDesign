"""Render exact read-back geometry of the disposable native P3 risk trials."""
import argparse
import hashlib
import json
from pathlib import Path


def plot(folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Patch
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    files={}
    for kind in 'mt':
        p=folder/'tasks'/('revision300-preconnect-trial-'+kind)
        r=json.loads((p/'receipt.json').read_text())
        assert r['passed']
        for name in ('revision300-preconnect-trial.json','revision300-preconnect.json','probe-geometry.tsv','probe-native-drc.rpt'):
            assert sha(p/name)==r['outputs'][name]
        d=json.loads((p/'revision300-preconnect-trial.json').read_text())
        g=json.loads((p/'revision300-preconnect.json').read_text())
        assert d['passed'] and d['simultaneous_connected_bits']==16 and d['native_drc_count']==0
        aliases={};rows=[]
        for line in (p/'probe-geometry.tsv').read_text().splitlines():
            if line.startswith('# NET '):
                _,_,alias,encoded=line.split();aliases[alias]=bytes.fromhex(encoded).decode()
            elif not line.startswith('#'):
                alias,layer,typ,*box=line.split('\t');rows.append((aliases[alias],layer,list(map(int,box))))
        rows.extend((name,layer,[a,b,c,e])for name,layer,a,b,c,e in d['actual_rects'])
        assert len({n for n,_,_ in rows})==16
        unit=g['dbu'];assert unit==2000
        fig,ax=plt.subplots(figsize=(12,5))
        die=[v/unit for v in g['die_dbu']]
        ax.add_patch(Rectangle(die[:2],die[2]-die[0],die[3]-die[1],facecolor='#f1f3f5',edgecolor='#111827'))
        colors={'metal9':'#2679ae','metal10':'#b27c18','via9':'#cc3030'}
        for layer in ('metal9','metal10','via9'):
            seen=set()
            for name,observed,box in rows:
                if observed!=layer or (name,observed,tuple(box))in seen:continue
                seen.add((name,observed,tuple(box)));a,b,c,e=[x/unit for x in box]
                ax.add_patch(Rectangle((a,b),c-a,e-b,facecolor=colors[layer],edgecolor=colors[layer],linewidth=.2))
        x0,lo,x1,hi=[v/unit for v in g['corridor_box_dbu']]
        label_y=None
        for i,path in enumerate(g['selected_paths']):
            y=path['y']/unit
            label_y=y if label_y is None else max(y,label_y+7)
            ax.annotate(str(i),xy=(x0,y),xytext=(x0-7,label_y),
                        va='center',ha='right',fontsize=6,
                        arrowprops=dict(arrowstyle='-',linewidth=.3,color='#555555'))
        ax.set_xlim(x0-24,x1+12);ax.set_ylim(lo-5,hi+5);ax.set_aspect('equal')
        ax.set_title(kind.upper()+': 16 actual native fixed paths in a 240um band (risk-test copy)')
        ax.set_xlabel('X (um)');ax.set_ylabel('Y (um)')
        ax.legend(handles=[Patch(facecolor=colors[k],label=k)for k in colors],loc='upper center',bbox_to_anchor=(.5,-.16),ncol=3,frameon=False)
        fig.text(.5,.015,'Production macro unchanged. Native whole-chip DRC 0. No full GDS, STA or array qualification.',ha='center',fontsize=8)
        fig.subplots_adjust(bottom=.23)
        target=folder/(kind+'-fixed16.png');fig.savefig(target,dpi=180,bbox_inches='tight');plt.close(fig)
        files[target.name]=dict(sha256=sha(target),source_receipt_sha256=sha(p/'receipt.json'),
            actual_bits=16,native_drc_count=0,production_macro_changed=False)
    manifest=dict(passed=True,figures=files,generator_sha256=sha(Path(__file__)),geometry_only=True)
    (folder/'plot-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('folder',type=Path)
    plot(parser.parse_args().folder)
