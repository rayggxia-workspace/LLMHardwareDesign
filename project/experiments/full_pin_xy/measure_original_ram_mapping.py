"""Map the exact original synchronous masked SRAM RTL to real Nangate cells.

Capacity, synchronous read enable/hold, mask and collision-X semantics remain
those of the source RTL. No macro replacement or altered block is performed.
"""
from pathlib import Path
import datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from verify_ram_sync_wrapper import REFERENCE,YOSYS
DRIVER=Path(__file__).resolve().parent
def run(revision):
    assert sha(REFERENCE)=='79d5f143c4226b600aaaebd9b579055636653c3bbc0e39054cd5be501c85a0f6'
    out=ROOT/'original_ram_stdcell_mapping'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'EXACT_ORIGINAL_RAM_RTL_REAL_CELL_MAPPING_AREA_NOT_PHYSICAL_MACRO_REPLACEMENT','source_SHA':{str(REFERENCE):sha(REFERENCE)},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'original_leaf_or_macro_modified':False,'original_macro_outline_um':[68.210,75.600],'preserved_source_contract':'64 words x64 bits; original synchronous enabled read/hold, bit write mask and same-address X semantics; no added architectural latency','DRC_RC_STA_GDS_mapped_equivalence':'NOT_EXECUTED_MAPPING_MEASUREMENT_ONLY'}
    try:
        (out/'original_exact.v').write_bytes(REFERENCE.read_bytes());lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),IMAGE]
        rec['actual_Yosys_version']=subprocess.check_output(common+[YOSYS,'-V']).decode().strip();rec['actual_Yosys_binary_SHA256']=subprocess.check_output(common+['sha256sum',YOSYS]).decode().split()[0];rec['actual_Liberty_SHA256']=subprocess.check_output(common+['sha256sum',lib]).decode().split()[0]
        assert rec['actual_Liberty_SHA256']=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        script=['read_verilog original_exact.v','hierarchy -check -top fakeram45_1r1w_64x64','synth -top fakeram45_1r1w_64x64','dfflibmap -liberty '+lib,'abc -liberty '+lib,'clean','tee -o mapped_stat.json stat -json -liberty '+lib,'write_verilog -noattr mapped.v','write_json mapped.json']
        (out/'map.ys').write_text('\n'.join(script)+'\n')
        with (out/'mapping.log').open('x') as f:rec['native_Yosys_mapping_returncode']=subprocess.call(common+[YOSYS,'-s','map.ys'],stdout=f,stderr=subprocess.STDOUT)
        assert rec['native_Yosys_mapping_returncode']==0
        stat=json.loads((out/'mapped_stat.json').read_text());rec['actual_mapped_statistics']=stat
        mod=stat['modules']['\\fakeram45_1r1w_64x64'];area=mod['area']
        rec.update(mapped_standard_cell_master_area_um2=area,original_abstract_area_um2=68.210*75.600,cell_area_over_original_macro_area=area/(68.210*75.600),drop_in_original_footprint_impossible_by_cell_area_alone=area>68.210*75.600)
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec['all_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
