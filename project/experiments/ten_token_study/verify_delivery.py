"""Verify copied evidence, native integer outputs and exact source/input provenance."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys

root=Path(__file__).resolve().parents[3]
receipt=root/'work/YUZE-LU/240/ten-token';evidence=receipt/'evidence'
native=evidence/'native-m';study=root/'project/experiments/ten_token_study'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lfsha=lambda raw:hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--write-manifest',action='store_true');args=p.parse_args()

for line in (native/'receipt-sha256.txt').read_text().splitlines():
 digest,path=line.split(maxsplit=1)
 assert sha(native/path)==digest,('native artifact mismatch',path)
assert sha(evidence/'native-n/nexp-native-run.log')=='ed8f72052e75a454bedeb2cda5e747df1baa1cd1a652533c1da3dbcb54f57a4f'
assert sha(evidence/'native-n/nexp-source-sha256.txt')=='25d95cde0132091a9b98853fa69256f98bee91661cedf84706abf25a469339f0'
for k in [16,32]:
 folder=native/f'vectors{k}'
 subprocess.run([sys.executable,'-B',str(study/'m_vectors.py'),'verify',str(folder),'--check-only'],check=True)
 assert 'longest_II1=31' in (folder/'rtl.log').read_text()
nlog=(evidence/'native-n/nexp-native-run.log').read_text()
assert 'NEXP_BATCH_PASS values=66440 frames=8419' in nlog

code_commit='1bc6e0b04'
sources={}
for p in study.iterdir():
 if p.suffix not in ['.sv','.cpp','.py','.sbatch']:continue
 sources[str(p.relative_to(root)).replace('\\','/')]=dict(raw_sha256=sha(p),lf_sha256=lfsha(p.read_bytes()))
for name in ['m_s32_stream_candidate.sv','tb_m_stream.sv']:
 blob=subprocess.run(['git','show',f'{code_commit}:project/experiments/ten_token_study/{name}'],cwd=root,capture_output=True,check=True).stdout
 assert lfsha(blob)==lfsha((study/name).read_bytes()),('M source changed since native test',name)
native_sources={}
for name in ['block_v2_n.sv','block_v2_n_group.sv','block_v2_n_exp.svh']:
 p=root/'project/rtl/block_v2'/name
 native_sources[str(p.relative_to(root)).replace('\\','/')]=dict(raw_sha256=sha(p),lf_sha256=lfsha(p.read_bytes()))
trace_sources={}
for name in ['prefill2','decode128','decode512','decode2048']:
 p=root/'work/YUZE-LU/240/inputs'/(name+'.trace')
 trace_sources[name]=dict(path=str(p.relative_to(root)).replace('\\','/'),raw_sha256=sha(p),lf_sha256=lfsha(p.read_bytes()))
trace_sources['decode640']=dict(path='evidence/systemc/decode640.trace',raw_sha256=sha(evidence/'systemc/decode640.trace'))
trace_sources['decode2']=dict(path='evidence/systemc/decode2.trace',raw_sha256=sha(evidence/'systemc/decode2.trace'),derivation='unchanged systemc_block_study/extract.py decode_graph(2), write_trace()')
auditsha=json.loads((evidence/'systemc/candidate-audit.json').read_text())['model_sha256']
assert auditsha=='57245ef3c4a5dfb28a018cc6e2ebd345ddfaab3ba8644ae719385ea603583067','unexpected audited timing source'
assert lfsha((study/'model.cpp').read_bytes())=='a9c62b456049fb9fa48e0bf84fe91dacf8da288bc37b844e9123c3745fdab91f','timing source changed since native study'
files={str(p.relative_to(receipt)).replace('\\','/'):sha(p) for p in evidence.rglob('*') if p.is_file()}
manifest=dict(date='2026-11-09',scope='conditional SystemC and separate native M/N RTL; no whole-model numeric/RTL/physical qualification',
 model_source_commit='5a94faa1b',M_native_source_commit=code_commit,N_native_source_commit='9b4367a2c',
 source_sha256=sources,native_N_source_sha256=native_sources,trace_sources=trace_sources,evidence_sha256=files,
 native_jobs=[dict(id=101746,state='COMPLETED',exit_code='0:0',root='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue240-ten-token-20261109-03'),
              dict(id=101753,state='COMPLETED',exit_code='0:0',root='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue240-ten-token-20261109-06')],
 tools=dict(SystemC='3.0.2',local_GCC='14.2',native_GCC='11.4',Verilator='5.042',Python='3.12.4',native_container='orfs-26Q1-repacked.sif'),
 qualification=dict(whole_model_numeric=False,whole_model_RTL=False,physical=False,energy=False),
 local_run='D:/Data/电路实验/side-ten-token-systemc-20261109-02',native_vectors='D:/Data/电路实验/side-ten-token-native-m-20261109-02')
if args.write_manifest:
 (receipt/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
else:
 locked=json.loads((receipt/'manifest.json').read_text(encoding='utf-8'))
 assert locked['evidence_sha256']==files,'copied evidence changed'
 for name,entry in locked['source_sha256'].items():
  assert entry['lf_sha256']==sources[name]['lf_sha256'],('source changed',name)
print('DELIVERY_VERIFIED',len(files),'evidence files;',len(sources),'source files')
