"""Bind real characterization views to a separately verified physical contact ECO.
Requires completed actual ngspice generation and completed original native
DRC plus transistor LVS on the modified GDS. Never changes the source views.
"""
import argparse,hashlib,json,os,re,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 for key in ['generation','eco','model_test','out']:ap.add_argument('--'+key.replace('_','-'),type=Path,required=True)
 ap.add_argument('--refined-lef',type=Path,help='Separate GDS-derived abstraction directory with geometric and native readback proofs')
 a=ap.parse_args();assert os.environ.get('SLURM_JOB_ID')
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);bank=out/'bank';bank.mkdir()
 original=a.generation.resolve();eco=a.eco.resolve()
 g=json.loads((original/'generation.json').read_text());e=json.loads((eco/'receipt.json').read_text());proof=json.loads((eco/'geometry-proof.json').read_text())
 assert g['status']=='views_generated_not_qualified' and g['returncode']==0
 assert e['passed'] and e['lvs_match'] and e['drc_items']==0 and all(c['returncode']==0 for c in e['commands'])
 assert proof['serialized_readback_exact'] and proof['all_other_cell_geometry_layers_instances_and_text_unchanged']
 assert proof['source_sha256']==g['views']['gds']['sha256']
 new=Path(proof['output']);assert sha(new)==proof['output_sha256']==e['gds_sha256']
 if 'reconstructed_lvs_sp_sha256' in g:
  circuit=original/'reconstructed-lvs.sp';expected=g['reconstructed_lvs_sp_sha256']
 else:
  # Fresh full compiler output already has the matching LVS circuit; no
  # routed-view reconstruction or substitute generation receipt is needed.
  assert Path(g['argv'][1]).name=='sram_compiler.py'
  circuit=original/'bank/s_sram_256x128_freepdk45.lvs.sp';expected=sha(circuit)
 assert sha(circuit)==expected==e['inputs'][str(circuit)]
 for log in ['lvs.log','drc.log']:
  command=next(c for c in e['commands'] if c['log']==log);assert sha(eco/log)==command['sha256']
 text=(eco/'lvs.log').read_text();assert 'CONGRATULATIONS! Netlists match.' in text and 'ERROR' not in text
 import xml.etree.ElementTree as E
 assert not E.parse(eco/'full.lyrdb').findall('.//items/item')
 refined=None;refinement_inputs=[]
 if a.refined_lef:
  folder=a.refined_lef.resolve();rp=folder/'receipt.json';np=folder/'native-receipt.json'
  r=json.loads(rp.read_text());n=json.loads(np.read_text())
  source_lef=Path(g['views']['lef']['path']);refined=Path(r['output'])
  assert r['passed'] and r['all_real_m4_covered_by_obstructions_or_unchanged_ports']
  assert r['serialized_geometry_exact'] and r['only_metal4_obs_text_changed']
  assert r['inputs'][str(new)]==sha(new) and r['inputs'][str(source_lef)]==sha(source_lef)
  assert sha(refined)==r['output_sha256']==n['refined_lef_sha256']
  assert n['passed'] and n['native_rectangles_exact'] and n['refinement_receipt_sha256']==sha(rp)
  assert sha(folder/'native-m4.tsv')==n['native_m4_sha256']
  assert sha(folder/'native-readback.tcl')==n['native_script_sha256']
  def outside_m4(text):
   obs=list(re.finditer(r'(?ms)^\s*OBS\s*\n(.*?)^\s*END\s*$',text));assert len(obs)==1
   m=list(re.finditer(r'(?s)LAYER\s+metal4\s*;(.*?)(?=\bLAYER\b|\Z)',obs[0].group(1)));assert len(m)==1
   return text[:obs[0].start(1)+m[0].start(1)],text[obs[0].start(1)+m[0].end(1):]
  assert outside_m4(source_lef.read_text())==outside_m4(refined.read_text())
  refinement_inputs=[rp,np,folder/'native-m4.tsv',folder/'native-readback.tcl',refined]
 views={};origins={}
 for kind,v in g['views'].items():
  src=Path(v['path']);assert sha(src)==v['sha256']
  use=new if kind=='gds' else refined if kind=='lef' and refined else src
  dst=bank/src.name;shutil.copyfile(use,dst);assert sha(use)==sha(dst)
  views[kind]=dict(path=str(dst),sha256=sha(dst),bytes=dst.stat().st_size)
  origins[kind]=dict(path=str(use),sha256=sha(use))
 model_test=a.model_test.resolve();m=json.loads(model_test.read_text());assert m['passed'] and m['emitted_model_sha256']==views['v']['sha256']
 shutil.copyfile(original/'run_config.py',out/'run_config.py')
 inputs={str(p):sha(p) for p in [original/'generation.json',original/'run_config.py',eco/'receipt.json',eco/'geometry-proof.json',eco/'full.lyrdb',model_test,*refinement_inputs]}
 record=dict(status='views_generated_not_qualified',returncode=0,producer='validated_physical_eco_views',qualified=False,physical_acceptance=False,internal_wire_pex=False,views=views,origins=origins,inputs=inputs,macro_drc_items=0,macro_lvs_match=True,functional_emitted_model_same_sha=True,timing_model_limitations=['Schematic transistor characterization without internal wire PEX','Upstream OpenRAM alter_lh_char_data copies HL table to LH'],scope='Actual library/model/SPICE and original LEF; deterministic contact-only GDS ECO with completed native full DRC and actual transistor LVS. Complete S layout and qualification remain separate.')
 if refined:
  record['gds_derived_m4_obstructions']=dict(geometric_proof=str(rp),native_readback_proof=str(np))
  record['scope']='Actual library/model/SPICE; deterministic contact-only GDS ECO with native full DRC and transistor LVS; separately verified GDS-derived M4 obstruction abstraction with unchanged pins and all other LEF text. Actual S routing and qualification remain separate.'
 (out/'generation.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
