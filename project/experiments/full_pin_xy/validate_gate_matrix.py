"""Validate reported gate scope and numbers against immutable native receipts."""
from pathlib import Path
import gzip,hashlib,json,re


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def check(out):
    data=out/'data';matrix=data/'qualification_matrix.json'
    if not matrix.exists():return
    j=read(matrix);rows={r['case']:r for r in j['blocks']}
    assert len(rows)==6 and sum(r['original_signal_pins'] for r in rows.values())==24767
    assert all(r['full_qualification'] is False and r['mapped_design_formal_equivalence']=='NOT_EXECUTED' for r in rows.values())
    assert not j['common_base_qualified_or_frozen'] and not j['two_complete_M11_M12_modes_implemented']
    native_files=0
    for index in (data/'gate_milestones').glob('gate-*/snapshot.json'):
        meta=read(index);assert not meta['full_qualification']
        for r in meta['records']:
            if r['storage']!='LOSSLESS_SNAPSHOT':continue
            p=index.parent/r['relative'];stored=p.read_bytes();raw=gzip.decompress(stored)
            assert hashlib.sha256(stored).hexdigest()==r['stored_sha256']
            assert hashlib.sha256(raw).hexdigest()==r['sha256'] and len(raw)==r['bytes']
            native_files+=1
    latest=out/j['source_snapshot'];assert latest.exists();folder=latest.parent
    for case in ['gemm','mxu']:
        failed=folder/'streamout/costed-r01'/(case+'-C_ECO');old=read(failed/'execution.json.gz')
        assert old['merge_returncode']==1 and old.get('DRC_returncode') is None
        assert 'Duplicate MACRO name:' in gzip.decompress((failed/'merge.log.gz').read_bytes()).decode()
        fixed=folder/'streamout/costed-r02'/(case+'-C_ECO');cfg=read(fixed/'reader_configuration.json.gz');inputs=read(fixed/'input.json.gz')
        assert cfg['read_lef_with_def_before'] is True and cfg['read_lef_with_def_after'] is False
        assert cfg['explicit_LEFs_roundtrip_exact'] and cfg['explicit_LEFs']==inputs['lefs']
        merge=read(fixed/'merge.json.gz');assert merge['allow_empty']=='DISABLED' and merge['no_missing_macro_waiver']
        assert rows[case]['strict_GDS_merge_errors']==merge['merge_errors']
        if case=='gemm':assert merge['merge_errors']==0
        else:assert merge['merge_errors']==4 and rows[case]['complete_rules'].startswith('FAILED_STRICT_GDS')
        version='r03' if case=='gemm' else 'r04'
        paths=sorted((data/'continuation/resume').glob('resume-*/leaf_eco/'+version+'/'+case+'-C/execution.json.gz'));assert paths
        physical=read(paths[-1]);assert rows[case]['native_DRC_count']==physical['fresh_DRC_count']==0
        for kind in ['setup','hold']:
            text=gzip.decompress((paths[-1].parent/(kind+'.txt.gz')).read_bytes()).decode()
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)[1]);assert rows[case][kind+'_ns']==value
        if (fixed/'execution.json.gz').exists():
            end=read(fixed/'execution.json.gz')
            assert rows[case]['available_deck_findings']==end.get('available_deck_findings')
            assert not end['full_qualification']
    assert rows['llaccel_aux']['native_DRC_count']==4 and rows['llaccel_aux']['newer_attempt']['three_pin_job'].endswith('FAILED_DRT_1231')
    print('PASS_GATE_MATRIX_NATIVE_EVIDENCE',len(rows),'blocks;',native_files,'raw files; duplicate-LEF failure and real strict-merge outcomes preserved; NOT full qualification')
