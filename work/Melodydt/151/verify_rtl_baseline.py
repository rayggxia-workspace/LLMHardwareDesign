"""Verify imported RTL bytes and integration records; this is not RTL simulation."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib,json,re,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path)
    a=p.parse_args();root=a.root.resolve();aux=root/'work/Melodydt/151'
    m=json.loads((aux/'rtl-baseline.json').read_text(encoding='utf-8'))
    errors=[];artifacts=[]
    def check(name,expected=None):
        q=root/name
        if not q.is_file():errors.append('missing:'+name);return
        b=q.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        row={'path':name,'git_blob_sha':blob,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
        artifacts.append(row)
        if expected and any(row[k]!=expected[k] for k in ('git_blob_sha','sha256','bytes')):
            errors.append('upstream_bytes_changed:'+name)
        return b
    if len(m['core_files'])!=14 or len({r['path'] for r in m['core_files']})!=14:
        errors.append('incomplete_core_inventory')
    for r in m['core_files']:
        if not r['path'].startswith('project/rtl/') or 'ref-project' in r['path']:
            errors.append('invalid_scope:'+r['path']);continue
        b=check(r['path'],r)
        if b is None:continue
        for inc in re.findall(r'`include\s+"([^"]+)"',b.decode('utf-8')):
            if not (root/r['path']).parent.joinpath(inc).is_file():
                errors.append('include_missing:'+r['path']+':'+inc)
    expected={'project/rtl/block_v2/block_v2_m.sv':'block_v2_m',
              'project/rtl/block_v2/block_v2_n.sv':'block_v2_n',
              'project/rtl/block_v2/block_v2_e.sv':'block_v2_e',
              'project/rtl/block_v2/block_v2_g.sv':'block_v2_g',
              'project/rtl/block_library_v1/block_v1_r.sv':'block_v1_r',
              'project/rtl/block_feed_v1/block_feed_s_macro.sv':'block_feed_s_macro',
              'project/rtl/block_v1/transaction6k.sv':'transaction6k'}
    for name,module in expected.items():
        if not re.search(r'\bmodule\s+'+module+r'\b',(root/name).read_text(encoding='utf-8')):
            errors.append('module_missing:'+module)
    docs=['README.md','docs/ARCHITECTURE.md','docs/STATUS.md','progress/YUZE-LU/STATUS.md',
          'docs/SEVEN_BLOCK_RESEARCH_BASELINE.md','docs/SIX_CONNECTION_SYSTEM_DESIGN.md',
          'docs/SIX_CONNECTION_CONTROL_SPEC.md','docs/SIX_CONNECTION_TEMPLATE_SPEC.md',
          'docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md','progress/Melodydt/STATUS.md',
          'docs/handoffs/2026-10-31-issue-151-six-connections.md','work/Melodydt/151/README.md']
    for name in docs:
        b=check(name)
        if b and any(s.startswith(('<<<<<<<','|||||||','=======','>>>>>>>')) for s in b.decode('utf-8').splitlines()):
            errors.append('unresolved_merge_marker:'+name)
    check('work/Melodydt/151/rtl-baseline.json')
    check('work/Melodydt/151/system-verification.json')
    check('work/Melodydt/151/verify_rtl_baseline.py')
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'passed':not errors,'python':sys.version.split()[0],'source_commit':m['source_commit'],
        'source_tree':m['source_tree'],'target_before_merge':m['target_before_merge'],
        'checks':{'core_files':len(m['core_files']),'macro_modules':len(expected),
                  'include_existence':True,'research_documents_preserved':True,
                  'unresolved_conflict_markers':False},
        'artifacts':artifacts,'errors':errors,
        'not_executed':['RTL/SystemC simulation','synthesis','placement/routing','new physical qualification'],
        'scope':'Byte equality and selected static checks only; remote ancestry/tree and actual lightweight commands recorded in PR receipt.'}
    encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_bytes(encoded.encode('utf-8'))
    print(json.dumps({'passed':result['passed'],'checks':result['checks'],'errors':errors},ensure_ascii=True))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
