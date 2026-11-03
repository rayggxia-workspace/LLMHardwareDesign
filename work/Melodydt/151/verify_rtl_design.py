"""Check RTL-derived document contracts; does not execute or model hardware."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

AUX='work/Melodydt/151/'
DOCS=['docs/SIX_CONNECTION_SYSTEM_DESIGN.md','docs/SIX_CONNECTION_CONTROL_SPEC.md',
      'docs/SIX_CONNECTION_TEMPLATE_SPEC.md','docs/RTL_NATIVE_CONNECTION_AUDIT.md',
      'docs/rtl-contracts/MST_NATIVE.md','docs/rtl-contracts/NEG_NATIVE.md',
      'docs/rtl-contracts/R_NATIVE.md',
      'docs/decisions/0006-fixed-product-hierarchical-control-candidate.md',
      'docs/handoffs/2026-10-31-issue-151-six-connections.md',
      'progress/Melodydt/STATUS.md',AUX+'README.md']
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path)
    a=p.parse_args(); root=a.root.resolve(); errors=[]; checks={}
    c=json.loads((root/AUX/'rtl-derived-contract.json').read_text(encoding='utf-8'))
    s=json.loads((root/AUX/'system-design-contract.json').read_text(encoding='utf-8'))
    def need(ok,code):
        if not ok: errors.append(code)
    need(c['research_baseline']==s['rtl_research_baseline']==
         'faabeda68b3b098ba562d68517319e02725f5bc3','research_baseline')
    need(c['source_commit']=='643c6012a11cbf461146ac40fbf61485223fe946','source_commit')
    need(c['proposed_system_hardware_implemented'] is False and
         c['numeric_quality_accepted'] is False,'unsupported_claim')
    need(set(c['interfaces'])==set('MNEG SRT'.replace(' ','')),'seven_interfaces')
    for macro,row in c['interfaces'].items():
        raw=(root/row['path']).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        need(blob==row['git_blob_sha'] and hashlib.sha256(raw).hexdigest()==row['sha256'],
             'source_drift:'+macro)
        text=re.sub(r'//[^\n]*','',raw.decode('utf-8'))
        h=re.search(r'module\s+(\w+)\s*\((.*?)\);',text,re.S)
        need(bool(h) and h.group(1)==row['module'] and
             re.sub(r'\s+',' ',h.group(2)).strip()==row['ansi_header_normalized'],
             'interface_drift:'+macro)
    checks['native_interfaces_hash_and_signature']=len(c['interfaces'])
    # Actual example fields are decoded rather than accepted as a magic constant.
    cmds=s['examples']['ffn8_s8']['native_commands']; v=cmds['exec']['data']
    fields={'fmtA':v&1,'fmtB':(v>>1)&1,'clear':(v>>2)&1,'lastK':(v>>4)&15,
            'N':(v>>8)&15,'tiles':(v>>12)&7,'rows':(v>>15)&15}
    need(fields=={'fmtA':1,'fmtB':0,'clear':1,'lastK':8,'N':8,'tiles':1,'rows':1}
         and v>>19==0 and v&8==0 and cmds['exec']['index']==0,'FFN_EXEC_fields')
    need(cmds['scale']=={'op':4,'index':0,'data':1},'FFN_scale')
    need(cmds['read_s16']=={'op':5,'indices':[0,1],'data':256} and
         cmds['pack']=={'E_op':13,'shift':0},'FFN_read_pack')
    checks['ffn_native_commands']={'scale':'0x1','EXEC':hex(v),'read_S16':'0x100','fields':fields}
    need(c['observed_native']==s['rtl_corrections'],'native_correction_drift')
    n=c['observed_native']
    need(n['M_op3_can_feed_E13'] is False and n['G_gated_sigmoid_output_frac']==10 and
         n['R_s32_frac']=='product_declared' and n['R_ssm_requires_param_valid'] is True and
         n['T_steady_read_II']==1 and n['T_has_commit_error'] is False,'numeric_lifecycle_contract')
    e=s['examples']['softmax257']
    need(e['native_has_expected_total'] is False and e['expected_total_enforced_by']=='N_CTRL'
         and e['S_reserved_span_bytes']==97*16,'softmax_counter_or_span')
    checks['native_corrections']=len(n)
    g=next(t for t in s['templates'] if t['id']=='gdn')['qk_post_l2']
    need(g['q_E_op']==2 and g['q_shift']==14 and g['q_coefficient_raw']==1448 and
         g['k_additional_scale'] is False and g['source_heads']==16 and g['value_heads']==32
         and g['numeric_quality_accepted'] is False,'GDN_Q_scale_and_head_repeat')
    checks['GDN_Q_scale_candidate']={'coefficient_raw':1448,'shift':14,'quality':'NOT_ACCEPTED'}
    indexes=[]
    for f in ['source-index.json','system-source-index.json']:
        indexes.extend(json.loads((root/AUX/f).read_text(encoding='utf-8'))['sources'])
    by_url={unquote(x['url']):x for x in indexes}
    links=0; artifacts=[]
    files=DOCS+[AUX+'system-design-contract.json',AUX+'rtl-derived-contract.json',
                AUX+'verify_rtl_design.py',AUX+'verify_system_design.py']
    for name in files:
        raw=(root/name).read_bytes(); text=raw.decode('utf-8')
        need(b'\r' not in raw and raw.endswith(b'\n') and
             all(x.rstrip()==x for x in text.splitlines()),'whitespace:'+name)
        artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if not name.endswith('.md'): continue
        for target in LINK.findall(text):
            links+=1; u=urlsplit(target.strip('<>'))
            if not u.scheme and u.path:
                need((root/name).parent.joinpath(unquote(u.path)).resolve().exists(),
                     'local_link:'+name+':'+target)
            elif u.scheme in {'http','https'} and '/blob/' in u.path:
                row=by_url.get(unquote(u.scheme+'://'+u.netloc+u.path))
                need(row is not None,'unindexed_blob:'+target)
                if row and u.fragment.startswith('L'):
                    m=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',u.fragment)
                    need(bool(m) and 1<=int(m.group(1))<=int(m.group(2) or m.group(1))<=row['lines'],
                         'source_line:'+target)
    checks['markdown_links']=links
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
            'passed':not errors,'python':sys.version.split()[0],'research_baseline':c['research_baseline'],
            'source_commit':c['source_commit'],'checks':checks,'artifacts':artifacts,'errors':errors,
            'not_executed':['RTL/SystemC simulation','integer numeric oracle','full product program compilation',
                            'deadlock proof','synthesis','placement/routing','system hardware qualification',
                            'live Projects synchronization']}
    if a.output: a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'passed':not errors,'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
    return 0 if not errors else 1

if __name__=='__main__': raise SystemExit(main())
