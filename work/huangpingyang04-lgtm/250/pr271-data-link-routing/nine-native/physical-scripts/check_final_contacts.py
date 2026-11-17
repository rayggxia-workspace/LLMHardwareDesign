from collections import defaultdict
import csv,gzip,json
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/'engine'))
from geometry import Occupancy,too_close
expected=json.loads((root/'final/native-expected-contacts.json').read_text())
tech=json.loads((root/'final/spec.json').read_text())['technology']
for kind in ('C','P'):
    ports={}; owners={};terms={}
    with (root/f'native-final-{kind}/ports.tsv').open() as f:
        for r in csv.reader(f,delimiter='\t'):
            if r[0]=='term':owners[r[1]]=r[4];terms[r[1]]=r[2:]
            if r[0]=='pin' and r[2]=='metal10':ports.setdefault(r[1],[]).append(list(map(int,r[3:])))
    fixed=Occupancy(tech)
    with gzip.open(root/f'native-final-{kind}/native.tsv.gz','rt') as f:
        for line in f:
            if line.startswith('#'):continue
            owner,layer,role,*b=line.split()
            if layer!='metal10':continue
            fixed.add([('M10',list(map(int,b)))],(owner,role))
    failures=[];checked=0
    for pin,box in expected.items():
        block,name=pin.split('.',1)
        if block not in (('C0',) if kind=='C' else ('P2',)):continue
        assert box in ports[name],(pin,'not in actual ODB',box,ports.get(name))
        checked+=1;seen=set()
        for key in fixed.keys('M10',[box[0]-3000,box[1]-3000,box[2]+3000,box[3]+3000]):
            for (other,role),b in fixed.occupants(key):
                sig=(other,role,tuple(b))
                if sig in seen:continue
                seen.add(sig)
                if other!=owners[name] and too_close(box,b,3000):
                    failures.append({'pin':pin,'box':box,'other':other,'role':role,'other_box':b})
    (root/f'native-final-{kind}/contact-check.json').write_text(json.dumps({'checked':checked,'conflicts':failures},indent=2)+'\n')
    print(kind,'actual native ports',checked,'M10 conflicts',len(failures),'affected',len(set(x['pin'] for x in failures)),flush=True)
