"""One-time, non-overwriting import of the already generated model graph archive."""
import hashlib,json,pathlib,re,shutil
ROOT=pathlib.Path(__file__).resolve().parents[3]
SOURCE=ROOT.parent/'model-operator-graphs-20261026'
TARGET=ROOT/'docs/model-analysis'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert ROOT.name=='LLMHardwareDesign'
assert SOURCE.is_dir() and not TARGET.exists()
baseline={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (ROOT/'work/YUZE-LU/114').rglob('*') if p.is_file()}
TARGET.mkdir();graph=TARGET/'graphs';graph.mkdir()
copied={}
def copy(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copyfile(src,dest)
 assert sha(src)==sha(dest);copied[str(dest.relative_to(ROOT)).replace('\\','/')]={'source':str(src),'sha256':sha(dest),'bytes':dest.stat().st_size}
for name in ['operator-graphs.html','README.md','comparison.csv','delivery-manifest.json','qa-browser.json','qa-data.json','slurm-status.txt']:
 copy(SOURCE/name,graph/name)
for folder in ['results/manual02','results/render01','results/native02','results/native03','results/native04','sources']:
 for src in sorted((SOURCE/folder).rglob('*')):
  if src.is_file():
   assert src.suffix not in ['.onnx','.whl','.tgz','.pyc']
   copy(src,graph/src.relative_to(SOURCE))
old=ROOT/'docs/MODEL_EXPERIMENT_ANALYSIS.md';original=old.read_text(encoding='utf-8')
def relocate(match):
 target=match[1]
 return ']('+('../'+target if target.startswith('../') else target)+')'
moved=re.sub(r'\]\(([^)]+)\)',relocate,original)
(TARGET/'MODEL_EXPERIMENT_ANALYSIS.md').write_text(moved,encoding='utf-8')
old.write_text('# 模型实验分析报告已迁移\n\n正式报告已归档至 [model-analysis/MODEL_EXPERIMENT_ANALYSIS.md](model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)。\n\n统一入口：[模型分析与计算图](model-analysis/README.md)，包含精简字符图、完整手工/ONNX/onnxsim图册及实验分析。\n\n本页保留旧路径兼容；原报告由 [PR #115](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/115) 合并，历史实验结论与来源资格不变。\n',encoding='utf-8')
simple=(SOURCE/'八模型_精简字符算子计算图.md').read_text(encoding='utf-8')
simple=simple.replace('(./operator-graphs.html)','(./graphs/operator-graphs.html)').replace('(./README.md)','(./COMPUTATION_GRAPHS_FULL.md)').replace('(./results/render01/manifest.json)','(./graphs/results/render01/manifest.json)')
simple=simple.replace('本次仅新增此 Markdown 参考文档，未修改主项目仓库、未重新导出 ONNX、未提交 GitHub 或更改项目状态。','本文件由独立实验目录的字符图文档归档而来，原始文件保留。此次目录整理未重新运行模型或导出 ONNX；任务为 Issue #116。')
(TARGET/'COMPUTATION_GRAPHS_SIMPLIFIED.md').write_text(simple,encoding='utf-8')
for filename in ['README.md','研究资料导读.md','progress/YUZE-LU/STATUS.md']:
 p=ROOT/filename;s=p.read_text(encoding='utf-8');s=s.replace('docs/MODEL_EXPERIMENT_ANALYSIS.md','docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md');p.write_text(s,encoding='utf-8')
record={'issue':'https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116','source_root':str(SOURCE),'base_commit':'2113afef4afc1f16391e0ed929158bdfc3f70b94','byte_identical_imports':copied,'historical_issue114_files':baseline,'analysis_migration':{'original_path':'docs/MODEL_EXPERIMENT_ANALYSIS.md','new_path':'docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md','original_sha256':hashlib.sha256(original.encode()).hexdigest(),'change':'Only ../ relative link targets gain one ../ component; original path now redirects.'}}
(ROOT/'work/YUZE-LU/116/archive-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'copied_files':len(copied),'copied_bytes':sum(x['bytes'] for x in copied.values()),'analysis_relative_links_rebased':True,'historical_evidence_unchanged':all(sha(ROOT/k)==v for k,v in baseline.items())}))
