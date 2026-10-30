"""Publish existing physical revisions and NEW parent contracts; never regenerate ABC."""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy_gz(src,dst):
    with dst.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(src.read_bytes())

def stage(root):
    root=Path(root);work=root.parent
    specs=[('gemm','gemm_electrical_r03','trial-inputs-gemm-electrical-publication-r04','gemm_C_electrical_r03_all_pins.csv','electrical-r03'),
      ('mxu','mxu_repair_r03','trial-inputs-mxu-repair-r04','mxu_C_repair_r03_all_pins.csv','mxu-repair-r03')]
    for case,name,source,filename,rev in specs:
        src=work/source;out=root/'incremental_revisions'/name;out.mkdir(parents=True,exist_ok=True)
        if case=='gemm':assert sha(src/'gemm-C.tcl')==sha(work/'trial-inputs-gemm-electrical-r03/gemm-C.tcl'),'Executed XY must be unchanged'
        for p in src.iterdir():
            if p.name==filename:copy_gz(p,out/(filename+'.gz'))
            elif p.suffix in ['.json','.tcl']:shutil.copyfile(p,out/p.name)
        (out/'publication.json').write_text(json.dumps({'case':case,'physical_revision':rev,'complete_pin_table':filename+'.gz','source_input_directory':str(src.resolve()),
          'relocation_Tcl_sha256':sha(src/(case+'-C.tcl')),'original_ABC_untouched':True,
          'metadata_note':'GEMM restored-pin geometric metrics copied from A; executed Tcl exactly unchanged. MXU local point repairs screened against original geometry; actual final DRC is a separate receipt.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    parents=root/'controlled_parents';parents.mkdir(exist_ok=True)
    for name in ['parent-inputs-opentpu-act-r04','parent-inputs-llaccel-gemm-r01']:
        src=work/name;out=parents/name;out.mkdir(exist_ok=True)
        for p in src.iterdir():
            if p.is_file():copy_gz(p,out/(p.name+'.gz'))
    (parents/'scope.json').write_text(json.dumps({'scope':'NEW_CONTROLLED_PARENT_NOT_HISTORICAL','historical_handoff':'STILL_UNKNOWN','parent_STA':'NOT_QUALIFIED_UNCHARACTERIZED_PORT_ONLY_LIBERTY',
       'opentpu':{'job':'92441','revision':'r07','input':'parent-inputs-opentpu-act-r04','expected_endpoints':6618,'parent_bits':3408},
       'llaccel':{'job':'92458','revision':'ll-r01','input':'parent-inputs-llaccel-gemm-r01','expected_endpoints':27050,'parent_bits':13507},
       'status':'Read execution.json and pre_model.graph_check.json from physical snapshot; submission/graph/PG/route/independent DRC/whole geometry are separate gates.'},indent=2)+'\n',encoding='utf-8')
    src=root/'ll-fullC-actual-fixed-PG-proof-r01';actual=root/'ll-fullC-actual-fixed-PG-input-r01'
    if src.exists():
        dest=root/'fixed_pg_rejections/llaccel_aux_full_C';dest.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src/'proof.json',dest/'proof.json');copy_gz(src/'direct_contacts.csv',dest/'direct_contacts.csv.gz')
        for name in ['moved.pins.tsv','before.pdn.tsv','moved.pdn.tsv','execution.json']:copy_gz(actual/name,dest/(name+'.gz'))
        if (src/'stop-action.json').exists():shutil.copyfile(src/'stop-action.json',dest/'stop-action.json')
        if (src/'checkpoint-index.json').exists():shutil.copyfile(src/'checkpoint-index.json',dest/'checkpoint-index.json')
    print('STAGED_EXISTING_INCREMENTAL_AND_NEW_PARENT_CONTRACTS')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);stage(p.parse_args().root)
