from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-config786-remote.py').read_text()
for a,b in [('binding-audit-786','binding-audit-802'),('sready777-fourary-heap-controls','sready791-threshold-pattern-controls'),('[7780,7781]','[7920,7921]'),('--route-weighted-pair-margin','--route-threshold-pattern-rounds'),('{7780:0,7781:4}','{7920:8,7921:16}'),('r256-fourary-heap-regression-777','r256-threshold-pattern-regression-791'),('candidates7780/7781','candidates7920/7921')]:
    assert a in s,a;s=s.replace(a,b)
a="assert json.loads((b/'r256-threshold-pattern-regression-791/receipt.json').read_text())['passed'];";assert a in s;s=s.replace(a,'')
compile(s,'config802','exec');(h/'control162-config802-remote.py').write_bytes(s.encode())
