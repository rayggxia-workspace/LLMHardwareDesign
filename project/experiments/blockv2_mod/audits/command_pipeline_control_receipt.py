"""Admit fresh XML only if source snapshots are unchanged across elaboration."""
import argparse,json,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from check_parent_service_structure import inspect
from check_pr185_control_admission import validate
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('hardware',type=Path);p.add_argument('--snapshot',action='store_true');a=p.parse_args()
root=Path.cwd();base=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project')
dirs=[root/'rtl'/n for n in ('projection','control','services','resources','p_services')]+[base/n for n in ('experiments/shared_x_control/rtl','rtl/block_local_native','rtl/w8a16_v1','rtl/s_sram','rtl/block_feed_v1')]
dirs.append(Path('/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include'))
if a.snapshot:
 a.directory.mkdir(parents=True,exist_ok=True)
 sources={str(f.resolve()):sha(f) for d in dirs for f in d.iterdir() if f.is_file() and f.suffix in ('.sv','.svh','.v')}
 (a.directory/'before.json').write_text(json.dumps(sources,indent=2)+'\n')
else:
 before=json.loads((a.directory/'before.json').read_text());sources={};rows=[]
 for family in ('p','n','e'):
  xml=a.directory/(family+'.xml');tree=ET.parse(xml).getroot()
  for f in tree.findall('./files/file'):
   path=Path(f.get('filename',''));path=path if path.is_absolute() else root/path
   if path.suffix not in ('.sv','.svh','.v'):continue
   key=str(path.resolve())
   if key not in before or sha(path)!=before[key]:raise ValueError('source changed or absent before elaboration: '+key)
   sources[key]=before[key]
  rows.append({'family':family,'instances':inspect(xml),'xml_sha256':sha(xml)})
 receipt=a.directory/'receipt.json';receipt.write_text(json.dumps({'schema':'command-control-elaboration/1','sources':sources,'rows':rows},indent=2)+'\n')
 result=validate(json.loads(a.hardware.read_text()),receipt_path=receipt,xml_directory=a.directory)
 (a.directory/'admission.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'receipt':str(receipt),'receipt_sha256':sha(receipt),'families':3,'sources':len(sources)}))
