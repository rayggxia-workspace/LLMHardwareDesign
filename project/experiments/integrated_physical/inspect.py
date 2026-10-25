"""Bounded failure triage only; no qualification or netlist changes."""
import argparse,collections
from common import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reparse',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False);b=load(a.prepared/'cut-source.json')['modules']['chain93'];t=load(a.prepared/'cut.json')['modules']['chain93'];f=load(a.stage/'final.json')['modules']['chain93'];missing=set(b['cells'])-set(f['cells']);added=set(f['cells'])-set(b['cells'])
 r={'source':sources(),'resources':resource_snapshot(),'input_sha256':{str(q):sha(q)for q in[a.prepared/'cut-source.json',a.prepared/'cut.json',a.stage/'final.json']},'counts':{'before':len(b['cells']),'tied':len(t['cells']),'after':len(f['cells'])},'missing_count':len(missing),'added_count':len(added),'missing':[{'name':n,**b['cells'][n]}for n in sorted(missing)[:80]],'added':[{'name':n,**f['cells'][n]}for n in sorted(added)[:80]],'histograms':{name:dict(collections.Counter(c['type']for c in net['cells'].values()))for name,net in [('before',b),('after',f)]}}
 if a.reparse:
  for stem in ('cut-source','cut'):
   ys=a.out/(stem+'.ys');ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {a.prepared}/{stem}.v\nhierarchy -top chain93\ncheck -assert\nwrite_json {a.out}/{stem}-parsed.json\n')
   command(a.out,stem,['yosys','-s',ys],300)
  bb=load(a.out/'cut-parsed.json')['modules']['chain93'];ss=load(a.out/'cut-source-parsed.json')['modules']['chain93'];missing2=set(bb['cells'])-set(f['cells']);added2=set(f['cells'])-set(bb['cells'])
  r['canonical_diagnostic']={'source_parsed_cells':len(ss['cells']),'tied_parsed_cells':len(bb['cells']),'after_cells':len(f['cells']),'missing':[{'name':n,**bb['cells'][n]}for n in sorted(missing2)],'added':[{'name':n,**f['cells'][n]}for n in sorted(added2)],'raw_vs_verilog_histogram_delta':dict(collections.Counter(c['type']for c in bb['cells'].values())-collections.Counter(c['type']for c in t['cells'].values()))}
 put(a.out/'inspection.json',r);print(__import__('json').dumps({k:v for k,v in r.items()if k not in ['resources','source','histograms']}))
if __name__=='__main__':main()
