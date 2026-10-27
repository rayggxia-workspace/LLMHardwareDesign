"""Keep the exact original pilot cohort, update only its C XY to revision r02."""
from pathlib import Path
import argparse,hashlib,json,shutil
import pandas as pd
def main(root,previous,out):
    root=Path(root);previous=Path(previous);out=Path(out);shutil.copytree(previous,out)
    selections=json.loads((out/'selection.json').read_text());shutil.copy2(root/'coverage_gate.json',out/'coverage_gate.json')
    for c in ['mxu','vector','opentpu_aux','llaccel_aux']:
        d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False);d=d[d.plan=='C'].set_index('pin').loc[selections[c]['pins']]
        old=pd.read_csv(previous/(c+'-C.csv')).set_index('pin').loc[d.index]
        assert (old.layer==d.layer).all()
        selections[c]['grid_revision']='r02 actual 0.005um manufacturing grid; same original cohort; no layer/semantic change'
        selections[c]['max_axis_delta_from_r01_um']=float(abs(d[['x_um','y_um']].to_numpy()-old[['x_um','y_um']].to_numpy()).max())
        d.reset_index().to_csv(out/(c+'-C.csv'),index=False,float_format='%.6f')
        with (out/(c+'-C.tcl')).open('w',encoding='utf-8',newline='\n') as f:
            for pin,r in d.iterrows():f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    (out/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='input_hashes.json'},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--previous',required=True);p.add_argument('--out',required=True);a=p.parse_args();main(a.root,a.previous,a.out)
