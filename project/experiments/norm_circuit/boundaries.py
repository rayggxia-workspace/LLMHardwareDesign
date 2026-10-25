"""Small adversarial cases; expected answers come only from the independent receiver."""
import argparse,json,hashlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 cases=[{'name':'tie'+str(g),'h':1,'x':[4096],'gamma':[g],'epsilon':0,'original_expected':None}for g in(128,384,640,-128,-384,-640)]
 cases +=[{'name':'bad_h1537','h':1537,'x':[],'gamma':[],'epsilon':17,'original_expected':None},{'name':'min_gamma','h':1,'x':[-4096],'gamma':[-2147483648],'epsilon':0,'original_expected':None},{'name':'zero_den','h':1,'x':[0],'gamma':[1],'epsilon':0,'original_expected':None}]
 def hx(x):
  b=b''.join(int(v).to_bytes(4,'little',signed=True)for v in x);return(b+bytes((-len(b))%16)).hex()or'-'
 (a.out/'vectors.json').write_text(json.dumps(cases,indent=2)+'\n')
 (a.out/'vectors.tsv').write_text(''.join(f"{c['name']} {c['h']} {c['epsilon']} {hx(c['x'])} {hx(c['gamma'])}\n"for c in cases))
 (a.out/'manifest.json').write_text(json.dumps({'status':'SYNTHETIC_BOUNDARY_INPUTS_NOT_RTL','cases':len(cases),'artifacts':[{'path':n,'sha256':hashlib.sha256((a.out/n).read_bytes()).hexdigest()}for n in('vectors.json','vectors.tsv')]},indent=2)+'\n')
 print('BOUNDARY_INPUTS',len(cases))
if __name__=='__main__':main()
