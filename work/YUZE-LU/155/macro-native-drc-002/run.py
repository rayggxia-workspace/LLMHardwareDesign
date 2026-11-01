from pathlib import Path
import hashlib,json,shutil,subprocess,time,os,xml.etree.ElementTree as ET
assert os.environ.get('SLURM_JOB_ID')
src=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/macro-lvs-001/s_sram_256x128_freepdk45.gds')
deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(src);gds=Path.cwd()/src.name;shutil.copyfile(src,gds);assert sha(gds)==before==sha(src)
copy=Path.cwd()/deck.name;shutil.copyfile(deck,copy);assert sha(copy)==sha(deck)
text=ET.parse(copy).getroot().findtext('text')
for flag in ('FEOL','BEOL','OFFGRID','ANTENNA'):assert __import__('re').search(r'(?m)^'+flag+r'\s*=\s*true\b',text)
record=dict(passed=False,qualified=False,source_gds=str(src),gds_sha256=before,deck_source=str(deck),deck_sha256=sha(deck),scope='Unmodified complete ORFS Nangate45 deck on actual routed SRAM bank, all FEOL/BEOL/OFFGRID/ANTENNA groups enabled. Not complete S qualification.')
argv=['klayout','-b','-r',str(copy),'-rd','in_gds='+str(gds),'-rd','report_file='+str(Path.cwd()/'full.lyrdb')]
record['argv']=argv;Path('receipt.json').write_text(json.dumps(record,indent=2)+'\n')
start=time.monotonic()
with Path('drc.log').open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
record.update(returncode=r.returncode,seconds=time.monotonic()-start,log_sha256=sha('drc.log'))
if Path('full.lyrdb').is_file():
 root=ET.parse('full.lyrdb').getroot();items=root.findall('.//items/item')
 record.update(items=len(items),report_sha256=sha('full.lyrdb'),categories=len(root.findall('.//categories/category')))
 record['passed']=r.returncode==0 and not items
Path('receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));assert record['passed']
