"""Join early PG computation to the exact, genuinely qualified native S.

This reuses geometry computation only. No native gate is skipped, fabricated,
or inherited from a different physical source. PG RC/STA/continuity and final
delivery still run on the exact copied wrapper after this join.
"""
import json
import os
from pathlib import Path
import shutil


FILES={'6_final.'+suffix for suffix in ('v','sdc','def','odb','spef','gds')}


def match_files(candidate,accepted,sha):
    assert set(candidate)==set(accepted)==FILES
    result={}
    for name in sorted(FILES):
        old,new=candidate[name],accepted[name]
        assert old['sha256']==new['sha256'] and old['bytes']==new['bytes'],name
        for row in (old,new):
            path=Path(row['path'])
            assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],str(path)
        result[name]=dict(sha256=new['sha256'],bytes=new['bytes'],candidate=old['path'],accepted=new['path'])
    return result


def rebind(a,sha):
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
    old=a.reuse_computation.resolve();out=a.out.resolve();manifest=a.manifest.resolve()
    assert a.leaf=='block_feed_s_macro'
    assert old==base/'s-escape-pg-compute-01/1350/wrapper'
    assert base in out.parents and base in manifest.parents and out!=old
    out.mkdir(parents=True,exist_ok=False)
    r=dict(passed=False,job=os.environ['SLURM_JOB_ID'],leaf=a.leaf,native_leaf_qualified=False,whole_system_qualified=False,
           inputs={},scope='Exact early PG geometry computation joined to actual four-gate native S; fresh PG RC/STA/continuity and final delivery remain mandatory.')
    def bind(path,digest=None):
        value=sha(path)
        if digest is not None:assert value==digest,str(path)
        r['inputs'][str(path)]=value
        return value
    try:
        bind(Path(__file__));bind(Path(__file__).with_name('pg_fixed_access.py'))
        bind(old/'receipt.json');computed=json.loads((old/'receipt.json').read_text())
        assert computed['passed'] and computed['construction_completed'] and computed['native_drc_zero']
        assert not computed['native_leaf_qualified'] and not computed['whole_system_qualified']
        assert computed['leaf']==a.leaf and computed['full_deck']['total_items']==0
        for path,digest in computed['inputs'].items():bind(Path(path),digest)
        candidate=old.parent/'candidate-inputs.json';bind(candidate)
        c=json.loads(candidate.read_text());assert not c['native_leaf_qualified'] and not c['whole_system_qualified']
        assert computed['inputs'][str(candidate)]==sha(candidate)
        binding=old.parent/'input-binding.json';bind(binding);b=json.loads(binding.read_text())
        assert b['passed'] and b['metadata_only'] and not b['native_leaf_qualified']
        for path,digest in b['inputs'].items():bind(Path(path),digest)
        bind(manifest);selection=manifest.parent/'receipt.json';bind(selection)
        selected=json.loads(selection.read_text());assert selected['passed'] and selected['outputs']['physical.json']==sha(manifest)
        row=json.loads(manifest.read_text())['leaves'][a.leaf]
        entry=row['selection_delivery'];native=Path(entry['path']);receipt=Path(entry['receipt'])
        bind(native,entry['sha256']);bind(receipt,entry['receipt_sha256'])
        nr=json.loads(receipt.read_text());delivery=json.loads(native.read_text())
        assert nr['passed'] and nr['outputs']['delivery.json']==sha(native)
        assert delivery['passed'] and delivery['native_leaf_accepted'] and delivery['top']==a.leaf
        assert delivery['final_files']==row['final_files']
        drive=delivery['S_internal_drive'];assert drive==row['S_internal_drive'] and drive['all_four_gates_fresh']
        assert drive['owner']=='block_feed_s_macro M1-M10' and drive['no_new_registers']
        assert Path(drive['raw_producer'])==base/'s-escape-repair-01/candidate-1350'
        assert set(delivery['gate_receipts'])=={'physical','drc','function','formal'}
        reports={}
        for op,gate in delivery['gate_receipts'].items():
            path=Path(gate['path']);bind(path,gate['sha256']);gr=json.loads(path.read_text());assert gr['passed'] and gr['operation']==op
            name={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[op]
            report=path.parent/name;bind(report,gate['report_sha256']);assert gr['outputs'][name]==sha(report)
            data=json.loads(report.read_text());assert data['passed'] and data['source_receipt_sha256']==delivery['source_receipt_sha256']
            reports[op]=data
        assert all(reports['physical']['checks'].values())
        assert reports['drc']['full_deck']['total_items']==0 and not reports['drc']['native_report'].strip()
        assert all(reports['formal']['strict_native_lec']['checks'].values())
        assert reports['formal']['function_receipt_sha256']==delivery['gate_receipts']['function']['sha256']
        same=match_files(c['leaves'][a.leaf]['final_files'],row['final_files'],sha)
        for name,proof in same.items():assert b['file_sha256'][proof['candidate']]==proof['sha256']
        for name,digest in computed['outputs'].items():
            assert Path(name).name==name and name!='receipt.json'
            source=old/name;bind(source,digest);shutil.copyfile(source,out/name);assert sha(out/name)==digest
        # Preserve the complete original calculation receipt separately; never
        # overwrite it or reinterpret its false qualification fields.
        shutil.copyfile(old/'receipt.json',out/'computation-receipt.json')
        bind(Path(row['final_files']['6_final.odb']['path']),row['final_files']['6_final.odb']['sha256'])
        r.update(passed=True,construction_completed=True,native_drc_zero=True,native_drc=computed['native_drc'],full_deck=computed['full_deck'],
            reused_computation=dict(path=str(old),receipt_sha256=sha(old/'receipt.json'),accepted_native_delivery_sha256=sha(native),
                                    exact_six_input_files=same,all_four_native_gates_actually_passed=True))
    finally:
        r['outputs']={p.name:sha(p)for p in out.iterdir()if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
