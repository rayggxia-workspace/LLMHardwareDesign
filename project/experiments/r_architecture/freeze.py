"""Freeze Git bytes, never source artifacts from a moving working tree."""
from pathlib import Path
import subprocess,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3]
BASE='e836741d334429be7d991cdc260f1ba955a7562e'
OUT=ROOT/'work/YUZE-LU/157'
FILES=['project/rtl/block_library_v1/block_v1_r.sv','project/rtl/block_v2/block_v2_m.sv','project/rtl/block_v2/block_v2_e.sv','project/rtl/block_feed_v1/block_feed_s16k.sv','docs/BLOCK_V2.md','docs/BLOCK_V2_RESULTS.md','project/experiments/block_v1/test_recurrent_macro.cpp']
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True);inputs=OUT/'inputs';inputs.mkdir(exist_ok=True);rows=[]
    for name in FILES:
        data=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
        target=inputs/Path(name).name;target.write_bytes(data)
        rows.append(dict(path=name,git_commit=BASE,git_blob=subprocess.check_output(['git','rev-parse',BASE+':'+name],cwd=ROOT,text=True).strip(),git_bytes_sha256=sha(data),working_tree_bytes_sha256=sha((ROOT/name).read_bytes())if(ROOT/name).exists()else None,bytes=len(data),frozen=str(target.relative_to(ROOT))))
    assert rows[0]['git_bytes_sha256']=='4032c5edcbee9d38e1a51dd9f9c533e414d5263dd2440d7104a1688e73ca382d'
    evidence=Path('D:/Data/电路实验/r-fanout-readonly-20261101')
    (OUT/'baseline-evidence').mkdir(exist_ok=True)
    for name in ['REPORT.md','mapped-analysis.json','physical-analysis.json','sources.json','load-density.png','SHA256SUMS.json']:
        data=(evidence/name).read_bytes();(OUT/'baseline-evidence'/name).write_bytes(data)
        rows.append(dict(path=str(evidence/name),sha256=sha(data),bytes=len(data),scope='historical run030/run342 only'))
    (OUT/'BASELINE.json').write_text(json.dumps(dict(base_commit=BASE,files=rows,original_fanout=92059,original_mapping_commit='76f8db5758ecefdd72d45b0544ecb9a79ed6bced',original_odb_sha256='085829e28b10d9118ccc48d4de6de77e0ccf19592a5c7bf8929836a13b9ac6e6',physical_qualification_transferred=False),indent=2)+'\n',encoding='utf-8')
    print('Frozen',len(rows),'inputs')
if __name__=='__main__':main()
