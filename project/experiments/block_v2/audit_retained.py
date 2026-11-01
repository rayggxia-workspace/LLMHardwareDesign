"""Receive exact unchanged S/T leaves; never transfers acceptance to new RTL."""
import argparse
import json
from pathlib import Path
import tarfile
from run_rtl import ROOT,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--macro',choices=['s','t'],required=True)
    p.add_argument('--delivery',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--geometry',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);members={}
    def add(path,name):
        path=Path(path);assert path.is_file() and name not in members
        members[name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
    def receive(folder,report):
        r=json.loads((folder/'receipt.json').read_text());assert r['passed']
        assert sha(folder/report)==r['outputs'][report]
        v=json.loads((folder/report).read_text());assert v['passed'];return r,v
    delivery_name='delivery.json'if a.macro=='s'else'five-macro-delivery.json'
    receipt,index=receive(a.delivery,delivery_name);assert index['native_leaf_accepted'] and index['macro']==a.macro.upper()
    src_name='final-source.json'if a.macro=='s'else'revision300-final-source.json'
    sr,src=receive(a.source,src_name);assert sha(a.source/'receipt.json')==index['source_receipt_sha256']
    assert src['pipeline_completed'];budget=json.loads((ROOT/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    for key in ['clock_ns','uncertainty_ns','clock_transition_ns','input_delay_max_ns','input_delay_min_ns','output_delay_max_ns','output_delay_min_ns','input_driver','output_load_pf','corner']:
        assert src['budget'][key]==budget[key],key
    assert src['rtl_sha256']
    for path,h in src['rtl_sha256'].items():assert sha(ROOT/path)==h,path
    reports={}
    for op,row in index['gate_receipts'].items():
        rp=Path(row['path']);report=Path(row['report_path'])
        assert sha(rp)==row['sha256'] and sha(report)==row['report_sha256']
        r,v=receive(rp.parent,report.name);assert v['source_receipt_sha256']==index['source_receipt_sha256']
        reports[op]=v;add(rp,'evidence/'+op+'/receipt.json');add(report,'evidence/'+op+'/'+report.name)
    assert all(reports['physical']['checks'].values())
    assert reports['drc']['full_deck']['total_items']==0 and not reports['drc']['native_report'].strip()
    function=reports.get('function',reports.get('final-function'));assert function and len(function['initial_runs'])==3
    assert all(x['result']['passed'] for x in function['initial_runs'].values())
    assert reports['formal']['strict_native_lec']['passed'] and all(reports['formal']['strict_native_lec']['checks'].values())
    files=index['final_files'];assert {Path(p).suffix for p in files}=={'.v','.sdc','.def','.odb','.spef','.gds'}
    for name,row in files.items():
        path=Path(row['path']);assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'];add(path,'native/'+path.name)
    for key,name in [('pins','pins.json'),('image','layout.png')]:
        row=index[key];assert sha(row['path'])==row['sha256'];add(row['path'],'native/'+name)
    assert sha(reports['drc']['gds']['path'])==reports['drc']['gds']['sha256']
    add(a.delivery/delivery_name,'evidence/original-delivery.json')
    add(a.delivery/'receipt.json','evidence/original-delivery-receipt.json')
    add(a.source/src_name,'evidence/original-source.json');add(a.source/'receipt.json','evidence/original-source-receipt.json')
    geo_receipt,geo=receive(a.geometry,'five-macro-geometry.json')
    assert geo['source_odb_sha256']==files['6_final.odb']['sha256']
    for name in ['receipt.json','five-macro-geometry.json','candidate.lef','m10-access.json','native-pins.tsv','occupancy-summary.tsv','native-rect-completion.json']:
        assert name=='receipt.json' or sha(a.geometry/name)==geo_receipt['outputs'][name]
        add(a.geometry/name,'geometry/'+name)
    archive=a.out/('retained-'+a.macro+'-native.tar.gz')
    with tarfile.open(archive,'w:gz',compresslevel=3)as stream:
        for name,row in sorted(members.items()):
            assert sha(row['path'])==row['sha256'];stream.add(row['path'],arcname=name,recursive=False)
            assert sha(row['path'])==row['sha256']
    result=dict(passed=True,macro=a.macro.upper(),native_leaf_accepted=True,unchanged_rtl_sha256=src['rtl_sha256'],
        original_delivery=str(a.delivery),source_receipt_sha256=index['source_receipt_sha256'],
        original_budget=src['budget'],final_files=files,members=members,
        archive=dict(path=str(archive),bytes=archive.stat().st_size,sha256=sha(archive)),
        source_code_sha256=sha(Path(__file__)),scope='Exact unchanged previously accepted native300MHz leaf; all original files/gates rehashed. No new RTL or system acceptance.')
    (a.out/'bundle.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,macro=a.macro,archive=result['archive'])))

if __name__=='__main__':main()
