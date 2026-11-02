"""Positive real-geometry replay and independent corruption controls."""
import argparse,copy,json,sys
from pathlib import Path
from check_pin_access import check

ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--original',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
original=a.original.read_text();refined=(a.fixture/'bank.lef').read_text();proof=json.loads((a.fixture/'receipt.json').read_text())
native=[(x[0],x[1],*map(int,x[2:]))for x in (line.split()for line in (a.fixture/'native-pins.tsv').read_text().splitlines())]
positive=check(original,refined,proof,native);controls={}
def reject(name,text=refined,p=proof,n=native):
    try:check(original,text,p,n)
    except (AssertionError,KeyError,ValueError):controls[name]=True;return
    raise AssertionError('Accepted corrupt '+name)
reject('macro_size',refined.replace('SIZE ','SIZE 1 ',1))
reject('pin_name',refined.replace('PIN din0[0]','PIN corrupt',1))
reject('obstruction',refined.replace('OBS','OBS\n LAYER metal10 ; RECT 0 0 1 1 ;',1))
reject('window_coordinate',refined.replace('RECT ','RECT 1 ',1))
bad=copy.deepcopy(proof);bad['rectangles'][0]['access'][0]+=10;reject('proof_geometry',p=bad)
bad=copy.deepcopy(proof);bad['manufacturing_grid_dbu']=1;reject('grid_relaxation',p=bad)
bad=list(native);row=list(bad[0]);row[2]+=10;bad[0]=tuple(row);reject('native_geometry',n=bad)
a.out.write_text(json.dumps(dict(passed=True,positive=positive,negative_controls=controls),indent=2)+'\n')
print('PASS: real pin replay and '+str(len(controls))+' corruption controls')
