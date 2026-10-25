"""Bounded failure triage only; no qualification or netlist changes."""
import argparse,collections
from common import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);b=load(a.prepared/'cut-source.json')['modules']['chain93'];t=load(a.prepared/'cut.json')['modules']['chain93'];f=load(a.stage/'final.json')['modules']['chain93'];missing=set(b['cells'])-set(f['cells']);added=set(f['cells'])-set(b['cells'])
 r={'source':sources(),'resources':resource_snapshot(),'input_sha256':{str(q):sha(q)for q in[a.prepared/'cut-source.json',a.prepared/'cut.json',a.stage/'final.json']},'counts':{'before':len(b['cells']),'tied':len(t['cells']),'after':len(f['cells'])},'missing_count':len(missing),'added_count':len(added),'missing':[{'name':n,**b['cells'][n]}for n in sorted(missing)[:80]],'added':[{'name':n,**f['cells'][n]}for n in sorted(added)[:80]],'histograms':{name:dict(collections.Counter(c['type']for c in net['cells'].values()))for name,net in [('before',b),('after',f)]}}
 put(a.out/'inspection.json',r);print(__import__('json').dumps({k:v for k,v in r.items()if k not in ['resources','source','histograms']}))
if __name__=='__main__':main()
