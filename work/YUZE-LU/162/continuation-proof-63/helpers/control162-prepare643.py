from pathlib import Path
h=Path(__file__).parent
for old,new in [(640,643),(641,644)]:
 s=(h/('control162-refill'+str(old)+'-remote.py')).read_text(encoding='utf-8').replace('sready'+str(old)+'-directional-bidirectional-refill','sready'+str(new)+'-directional-bidirectional-refill')
 s=s.replace("assert source.name==expected_source and graph==current and '--route-trial-attempts'not in a", "assert source.name==expected_source and graph==current and '--route-trial-attempts'in a and a[a.index('--route-trial-attempts')+1]=='64';actual=next(x for x in json.loads((b/'r256-old407-live-spec-readback-642/receipt.json').read_text())['rows']if x['seed']==seed);assert sha(path)==actual['sha256']")
 s=s.replace("assert len(attempts)==16;", "assert 16<=len(attempts)<=64;")
 s=s.replace('fixed16attempt','16active64attempt').replace('Preserve all16 old logs','Preserve all old logs')
 (h/('control162-refill'+str(new)+'-remote.py')).write_bytes(s.encode())
