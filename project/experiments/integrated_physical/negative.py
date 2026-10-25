"""Persist, reread, rehash and independently reject malformed physical evidence."""
import argparse,copy,shutil
from common import *
from receive_physical import audit
p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);base=a.out/'baseline-reception';base.mkdir();baseline=audit(a.stage,a.prepared,base);cases=[]
for label,expected in [('clock','one exact10ns clock'),('endpoint','complete exact setup endpoint set'),('electrical_marker','unique ordered execution markers'),('FF_data','cell pin function'),('port_width','port width/direction'),('source','independent exact upstream admission'),('config','frozen physical config')]:
 folder=a.out/label;shutil.copytree(a.stage,folder);m=load(folder/'manifest.json');changed=None
 if label=='clock':changed=folder/'final.sdc';s=changed.read_text();need(s.count('-period 10.0000')==1,'baseline clock');changed.write_text(s.replace('-period 10.0000','-period 20.0000'))
 elif label=='endpoint':changed=folder/'setup-load1.tsv';lines=changed.read_text().splitlines();changed.write_text('\n'.join([lines[0],*lines[2:]])+'\n')
 elif label=='electrical_marker':changed=folder/'flow.log';s=changed.read_text();need(s.count('BEGIN_ELECTRICAL_REPORT')==2,'baseline executed markers');changed.write_text(s.replace('BEGIN_ELECTRICAL_REPORT','MISSING_MARKER',1))
 elif label in('FF_data','port_width'):
  changed=folder/'final.json';net=load(changed);top=net['modules']['chain93']
  if label=='FF_data':
   from structure import library,signature_graph
   lib=library(LIB);canon=signature_graph(top,lib);ff=next(c for c in top['cells'].values()if any(lib[c['type']]['sequential'].values()));old=canon(ff['connections']['D'][0]);ff['connections']['D'][0]=str(1-old[0][1])if old[0][0]=='constant'else'0'
  else:top['ports']['h']['bits'].pop()
  put(changed,net)
 elif label=='source':m['admission']['source_commit']='0'*40
 elif label=='config':m['config_sha256']=True
 manifest(folder,m);received=a.out/(label+'-receive');received.mkdir()
 try:audit(folder,a.prepared,received)
 except ValueError as e:need(expected in str(e),'negative rejected for intended independent reason '+label+':'+str(e));cases.append({'case':label,'expected':expected,'actual':str(e),'manifest_sha256':sha(folder/'manifest.json'),'changed_file':None if changed is None else str(changed),'changed_sha256':None if changed is None else sha(changed)})
 else:raise ValueError('persisted rehashed malformed evidence accepted '+label)
put(a.out/'receipt.json',{'status':'PASS_PERSISTED_REHASHED_PHYSICAL_NEGATIVES','source':sources(),'resources':resource_snapshot(),'baseline_stage_manifest_sha256':sha(a.stage/'manifest.json'),'baseline_reception_passed':True,'cases':cases});print('PASS_PERSISTED_REHASHED_PHYSICAL_NEGATIVES')
