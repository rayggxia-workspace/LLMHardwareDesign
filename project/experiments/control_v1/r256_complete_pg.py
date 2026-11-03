"""Reuse the exact accepted R256 complete-die checker, with fresh controls.

Fragmented diagnostics remain intact. No rule, marker, geometry, connection or
DEF group is excluded. A distinct pinned tool is never called a container pass.
"""
import json,shutil,subprocess,sys
from pathlib import Path


def check(out,odb,inputs,sha):
    from r256_native_reuse import PACKAGE,QUAL_SHA
    original=PACKAGE/'evidence/physical/complete-native'
    receipt=json.loads((original/'receipt.json').read_text());assert receipt['passed']
    tool=receipt['checker'];assert tool['kind']=='pinned-unmodified-upstream'
    assert tool['binary_sha256']=='944848ca2b5181d570e21841fa9c54e53c062b4ebea74cd3955a6c5b30343ee0'
    assert tool['build_receipt_sha256']=='3b81aad72d36b77c24fca0df2f797446eefd4dd4cb3372a8b37c2244ef7e2cd4'
    sources={
      'native_complete.py':'de9ba52f34cc97088ebc759d323733e3c6be68fa8d0be2950bbb10dd372d0f86',
      'native_interchange.py':'633496bca77815f4b8a7392c8bcf141bd987e7361f28a88db5e5f5329742cac0',
      'native_fixed_fixtures.py':'48bddd4baccc9f4c9f6a4c94f77a44dc583c1ccf44d69e2fe805b91e6c044377'}
    def bind(path,expected=None):
        path=Path(path);digest=sha(path)
        if expected is not None:assert digest==expected,str(path)
        inputs[str(path)]=digest
    bind(PACKAGE/'QUALIFICATION.json',QUAL_SHA)
    bind(Path(__file__));bind(original/'receipt.json')
    for name,digest in sources.items():bind(PACKAGE/'source/runners'/name,digest)
    bind(tool['binary'],tool['binary_sha256'])
    root=Path(tool['root']);bind(root/'BUILD_RECEIPT.json',tool['build_receipt_sha256'])
    recheck=original/'CHECKER_SOURCE_RECHECK.json';bind(recheck,tool['post_source_sha256'])
    own=out/'complete-checker';own.mkdir()
    physical=own/'physical';target=physical/'flow/results/nangate45/r166_256/base';target.mkdir(parents=True)
    (target/'6_final.odb').symlink_to(odb)
    before=sha(odb)
    command=[sys.executable,str(PACKAGE/'source/runners/native_complete.py'),'--physical',str(physical),'--capacity','256','--checker-root',str(root),'--source-recheck',str(recheck)]
    (own/'SOURCE_BINDING.json').write_text(json.dumps(dict(inputs=dict(inputs),command=command,original_fragmented_report=str(out/'native-fragmented-drc.rpt'),wrapper_odb_sha256=before,whole_system_qualified=False),indent=2)+'\n')
    with(own/'run.log').open('w')as f:q=subprocess.run(command,cwd=own,stdout=f,stderr=subprocess.STDOUT)
    assert q.returncode==0,'R256 complete-die rule check or fresh positive/negative/interchange control failed'
    path=own/'native-complete/receipt.json';r=json.loads(path.read_text())
    assert r['passed']and r['original_source_unchanged']and r['identical_geometry_and_connections']and r['no_marker_or_rule_exclusions']
    assert r['original_odb_sha256']==before==sha(odb)and r['native_drc_count']==0
    assert r['checker']['binary_sha256']==tool['binary_sha256']
    assert r['controls']and all(v['passed']for v in r['controls'].values())
    assert {'positive','short','spacing','notch'}<=set(r['controls'])
    actual=own/'native-complete/complete.rpt';assert sha(actual)==r['native_report_sha256']and not actual.read_text().strip()
    destination=out/'native-whole-drc.rpt';assert not destination.exists();shutil.copyfile(actual,destination)
    return dict(passed=True,receipt=str(path),receipt_sha256=sha(path),checker=r['checker'],scope=r['scope'],original_fragmented_report=str(out/'native-fragmented-drc.rpt'),actual_complete_report=str(actual),actual_complete_report_sha256=sha(actual),fresh_controls=r['controls'],all_artifacts={str(p.relative_to(out)):sha(p)for p in own.rglob('*')if p.is_file()})
