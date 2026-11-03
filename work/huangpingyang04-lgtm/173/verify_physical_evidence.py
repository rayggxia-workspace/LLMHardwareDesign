"""Verify delivered receipt binding and small originals; does not rerun hardware."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
E=HERE/'physical-evidence'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 index=read(E/'evidence-index.json')
 for f in index['files']:
  p=E/f['path'];assert p.stat().st_size==f['bytes']and sha(p)==f['sha256'],p
 assert sha(E/index['raw_index']['path'])==index['raw_index']['sha256']
 pnr=read(E/'j96364/output/physical.json')
 audit=read(E/'j96378/output/audit-summary.json')
 gate=read(E/'j96377/output/gate.json')
 assert pnr['completed']and audit['passed']and gate['passed']
 assert all(x==0 for x in audit['violations'].values())
 assert audit['register_clocks']=={'core':26475,'mem':2260}
 assert audit['clocks']['mem']['period_ns']==2 and abs(audit['clocks']['core']['period_ns']-10/3)<1e-6
 assert not audit['unconstrained']and not audit['parasitics']['active_unannotated']
 assert audit['parasitics']['partial_unannotated']==0
 for k in('open_inputs','inputs_without_exactly_one_driver','unplaced'):assert not audit['connectivity'][k]
 assert gate['netlist_sha256']==pnr['files']['6_final.v']['sha256']==audit['final_files']['6_final.v']['sha256']
 assert audit['physical_receipt_sha256']==sha(E/'j96364/output/physical.json')
 assert len(audit['synchronizers'])==40 and all(r['slack_ns']>=0 for r in audit['synchronizers'])
 assert len(audit['synchronizer_buffer_chains'])==20
 assert sum(len(r['noninverting_buffers'])for r in audit['synchronizer_buffer_chains'])==40
 parsed=dict(re.findall(r'worst slack (max|min) ([^\s]+)',(E/'j96378/output/timing.rpt').read_text()))
 for kind in('max','min'):
  v=min(r['slack_ns']for r in audit['paths']if r['kind']==kind)
  assert abs(v-float(parsed[kind]))<1e-6,('timing property/report units mismatch',kind)
 views=[read(E/('j'+job+'/output/gate.json'))for job in('96279','96289','96377')]
 for view in views:
  assert view['passed']and view['matrix_cases']==393 and view['corruption_rejected']
  assert [r['initialization']for r in view['runs']]==[0,1,2]
  assert [r['phase']for r in view['runs']]==[0,3,7]
  for r in view['runs']:
   v=r['result'];assert v['matrix_cases']==131 and v['request_full_cycles']>0 and v['response_full_cycles']>0
 assert all([r['result']for r in v['runs']]==[r['result']for r in views[0]['runs']]for v in views)
 code=read(E/'j96377/source/source-snapshot.json');doc=[]
 assert code['source_commit']=='456336eeb4658e591ea7c75d22d21142b48bf62a'
 for f in code['files']:
  path=ROOT/f['path']
  if sha(path)!=f['sha256']:
   assert f['path']=='project/experiments/dram_m_fifo/README.md';doc.append(f['path'])
 b=(ROOT/'project/rtl/block_v2/block_v2_m.sv').read_bytes()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()=='d91ffdf904bc77c19d5d0ecfd4cd11560b44a417'
 for job in('96364','96378','96377'):
  rows=(E/('slurm-'+job+'.tsv')).read_text().splitlines();header=rows[0].split('|')
  row=next(dict(zip(header,line.split('|')))for line in rows[1:]if line.split('|')[0]==job)
  assert row['State']=='COMPLETED'and row['ExitCode']=='0:0'and row['Timelimit']=='UNLIMITED'
 docs=[ROOT/'docs/DRAM_M_FIFO_PHYSICAL_RESULTS.md',ROOT/'project/experiments/dram_m_fifo/README.md',HERE/'README.md',ROOT/'progress/huangpingyang04-lgtm/STATUS.md']
 links=0
 for p in docs:
  text=p.read_text(encoding='utf-8');assert 'Measured conclusion'not in text
  for target in re.findall(r'\]\(([^)]+)\)',text):
   if re.match(r'^[a-zA-Z]+:',target):continue
   target=target.split('#')[0]
   assert (p.parent/target).resolve().exists(),(p,target);links+=1
 result={'passed':True,'selected_file_hashes':len(index['files']),'raw_index_sha256_verified':True,
 'three_views_each_matrix_cases':393,'initial_phase_results_identical':True,'final_netlist_bound_to_pnr_and_sta':True,
 'native_timing_units_cross_checked':True,'original_M_git_blob_unchanged':True,'source_files_checked':len(code['files']),
 'documentation_only_post_run_changes':doc,'relative_links_checked':links,'three_final_jobs_completed_unlimited':True,
 'scope':'Receipt/source/link integrity only; actual hardware acceptance is in the named server jobs.'}
 (HERE/'physical-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result))
if __name__=='__main__':main()
