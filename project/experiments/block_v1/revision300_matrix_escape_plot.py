"""Plot receipt-bound actual M geometry; never synthesizes missing connections."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def plot(fixture_path,proof_folder,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Patch
    receipt=json.loads((proof_folder/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode']=='revision300-escape-m'
    assert sha(fixture_path)==receipt['outputs']['actual-escape.json']
    for name in ('revision300-escape.json','joined-readback.json'):
        assert sha(proof_folder/name)==receipt['outputs'][name]
    proof=json.loads((proof_folder/'revision300-escape.json').read_text())
    readback=json.loads((proof_folder/'joined-readback.json').read_text())
    assert proof['passed'] and readback['passed'] and proof['independent_joined_gds']==readback
    assert all(readback['native_all_mask_xor_zero'].values())
    assert readback['actual_added_native_m10_negative_rejected']
    data=json.loads(fixture_path.read_text());unit=data['dbu_per_um']
    assert unit==2000 and data['expected_bits']==proof['all_signal_bits']==275
    out.mkdir(parents=True,exist_ok=True)
    colors=dict(metal10='#374151',via10='#d62728',metal11='#bd8000',via11='#a23aaf',metal12='#087cad')
    inputs={str(p):sha(p)for p in (fixture_path,proof_folder/'receipt.json',proof_folder/'revision300-escape.json',proof_folder/'joined-readback.json')}
    figures=[]
    names={p['net']for p in data['ports']}
    for name,selected,title in [('all-ports',names,'M: all 275 real signal bits'),
        ('cmd-data16',{'cmd_data[%d]'%i for i in range(16)},'cmd_data[0:15]:16 real input bits'),
        ('response-data16',{'rsp_data[%d]'%i for i in range(16)},'rsp_data[0:15]:16 real output bits')]:
        assert selected<=names
        rows=[s for s in data['shapes']if s['net']in selected]
        fig,ax=plt.subplots(figsize=(9,9)if name=='all-ports'else(10,5))
        macro=[v/unit for v in data['macro_box_dbu']]
        ax.add_patch(Rectangle(macro[:2],macro[2]-macro[0],macro[3]-macro[1],facecolor='#f1f3f5',edgecolor='#202830',linewidth=1,zorder=0))
        seen=set()
        for layer in ('metal11','metal12','metal10','via10','via11'):
            for row in rows:
                if row['layer']!=layer:continue
                key=(row['net'],layer,tuple(row['box_dbu']))
                if key in seen:continue
                seen.add(key);a,b,c,d=[v/unit for v in row['box_dbu']]
                ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor=colors[layer],edgecolor=colors[layer],linewidth=.15,zorder=2 if layer.startswith('metal') else 3))
        if name=='all-ports':
            a,b,c,d=[v/unit for v in data['test_boundary_dbu']]
            ax.set_xlim(a-10,c+10);ax.set_ylim(b-10,d+10)
        else:
            ax.set_xlim(min(s['box_dbu'][0]for s in rows)/unit-15,max(s['box_dbu'][2]for s in rows)/unit+15)
            ax.set_ylim(min(s['box_dbu'][1]for s in rows)/unit-15,max(s['box_dbu'][3]for s in rows)/unit+15)
        ax.set_aspect('equal');ax.set_xlabel('X (um)');ax.set_ylabel('Y (um)');ax.set_title(title)
        ax.legend(handles=[Patch(facecolor=colors[k],label=k)for k in colors],loc='upper center',bbox_to_anchor=(.5,-.12),ncol=5,frameon=False)
        fig.text(.5,.025,'Native M1-M10 fixed; M11/M12 geometry only. Combined interface timing unqualified.',ha='center',fontsize=8)
        fig.subplots_adjust(bottom=.2)
        files={}
        for extension in ('png','svg'):
            p=out/(name+'.'+extension);fig.savefig(p,dpi=180,bbox_inches='tight')
            if extension=='svg':
                original=p.read_bytes()
                normalized=b'\n'.join(line.rstrip(b' \t\r')for line in original.splitlines())+b'\n'
                assert re.sub(rb'\s+',b' ',original).strip()==re.sub(rb'\s+',b' ',normalized).strip()
                p.write_bytes(normalized)
            files[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size)
        plt.close(fig);figures.append(dict(name=name,actual_bits=len(selected),files=files))
    assert inputs=={name:sha(Path(name))for name in inputs}
    report=dict(passed=True,source_inputs=inputs,geometry_only=True,figures=figures,
        generator_sha256=sha(Path(__file__)),hardware_source_commit=receipt['source_commit'],
        python_version=sys.version,matplotlib_version=matplotlib.__version__,
        generated_svg_trailing_space_normalized=True,
        full_interface_bits=275,combined_interface_timing_qualified=False,
        scope='Plots of exact receipt-bound actual DEF/ODB geometry independently compared against joined GDS. Native internal routing is not reconstructed; grey area is the frozen native boundary.16-bit panels are explicit subsets.')
    (out/'plot-manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('fixture',type=Path);parser.add_argument('proof',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();plot(args.fixture,args.proof,args.out)
