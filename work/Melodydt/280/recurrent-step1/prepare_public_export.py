"""Export project measurements without proprietary simulator transcript fields.

Original receipts remain unchanged in the local complete bundle. No part of an
omitted transcript is republished except this project's own PASS counters.
"""
from pathlib import Path
from hashlib import sha256, sha1
import json, re, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPORT = ROOT / 'tmp/recurrent-step1/public-export-root'
DEST = EXPORT / HERE.relative_to(ROOT)
read = lambda p: json.loads(p.read_bytes())
manifest = read(HERE / 'public-files.json')
paths = [row['path'] for row in manifest]
paths.append(Path(__file__).relative_to(ROOT).as_posix())
for name in paths:
    target = EXPORT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
omitted = []
for path in DEST.glob('*.json'):
    original = path.read_bytes()
    data = json.loads(original)
    fields = []
    def remove_logs(obj, prefix=''):
        if isinstance(obj, dict):
            for key in list(obj):
                value = obj[key]
                where = prefix + key
                if key in ('rtl_log', 'log') and isinstance(value, str):
                    # Remove the complete transcript, including all vendor text.
                    del obj[key]
                    fields.append(dict(field=where, sha256=sha256(value.encode()).hexdigest()))
                    marks = re.findall(r'(?:RTL_REPLAY_PASS commands=\d+ execs=\d+ cycles=\d+|GATE_REPLAY_PASS)', value)
                    if marks:
                        obj[key + '_project_test_summary'] = marks
                else:
                    remove_logs(value, where + '.')
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                remove_logs(value, prefix + str(i) + '.')
    remove_logs(data)
    if fields:
        info = dict(original_receipt_sha256=sha256(original).hexdigest(), omitted_transcripts=fields,
                    policy='Complete simulator transcripts retained locally; public data contains project-owned numerical measurements and counters only.')
        data['public_export'] = info
        path.write_text(json.dumps(data, indent=2) + '\n')
        omitted.append(dict(path=path.relative_to(EXPORT).as_posix(), **info))
assert len(omitted) == 8

# Keep the original source receipts intact; independently regenerate public
# provenance using the public receipt hashes and require identical model values.
original_result = read(HERE / 'candidate-rollup.json')
for name in original_result['input_sha256']:
    if name.startswith(HERE.relative_to(ROOT).as_posix() + '/'):
        continue
    target = EXPORT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
for suffix in ([], ['qwen35']):
    for script in ('rollup_candidate.py', 'verify_candidate.py'):
        subprocess.run([sys.executable, '-B', str(DEST / script), *suffix], check=True)
assert read(DEST / 'candidate-rollup.json')['models'] == original_result['models']
assert read(DEST / 'rollup-check.json') == read(HERE / 'rollup-check.json')
note = '''\n\n## 公开副本说明\n\n本次公开版将八份数值回执中的完整商业仿真器原始日志留在本地，仅保留项目自身的数值、窗口计数、PASS 摘要和原件 SHA。原始回执未修改；公开副本新增 public_export 来源说明，并独立重算输入散列，所有模型数值与完整本地包逐字一致。详见 public-export.json。\n\n公开 checkout 可运行 rollup_candidate.py 和 verify_candidate.py 复算模型积分。validate_delivery.py 检查完整本地回收包，包含未公开的构建日志，不作为公开 checkout 的检查入口。原始捕获 ZIP 与大网表/VCD 不在公开交付范围；复跑 RTL 仍需获授权输入和工具。\n'''
for name in ('README.md', 'DELIVERY.md'):
    with (DEST / name).open('a', encoding='utf-8') as f:
        f.write(note)
handoff = EXPORT / 'docs/handoffs/2026-11-18-issue-280-recurrent-first-round.md'
with handoff.open('a', encoding='utf-8') as f:
    f.write(note.replace('详见 public-export.json', '详见 work/Melodydt/280/recurrent-step1/public-export.json'))
receipt = dict(omitted=omitted, model_numbers_unchanged=True, public_rollup_pass=True,
               original_model_rollup_sha256=sha256((HERE / 'candidate-rollup.json').read_bytes()).hexdigest(),
               public_model_rollup_sha256=sha256((DEST / 'candidate-rollup.json').read_bytes()).hexdigest(),
               original_files_modified=False,
               reason='Automatic review rejected publication of proprietary simulator transcripts. All transcript fields are excluded from the public export.')
(DEST / 'public-export.json').write_text(json.dumps(receipt, indent=2) + '\n')
paths.append((DEST / 'public-export.json').relative_to(EXPORT).as_posix())
rows = []
for name in sorted(set(paths)):
    p = EXPORT / name
    raw = p.read_bytes()
    if p.suffix in ('.json', '.log', '.txt', '.md'):
        assert not re.search(rb'Mentor Graphics Corporation|Trade Secrets Act|Freedom of Information Act', raw), name
    rows.append(dict(path=name, source_path=p.relative_to(ROOT).as_posix(), bytes=len(raw),
                     sha256=sha256(raw).hexdigest(), git_blob_sha1=sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()))
(ROOT / 'tmp/recurrent-step1/public-upload-files.json').write_text(json.dumps(rows, indent=2) + '\n')
print('PUBLIC_EXPORT_PASS', len(rows), 'files;', len(omitted), 'receipts exclude complete vendor logs; model values unchanged')
