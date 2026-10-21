"""Explicit two-report refresh (--sync --source PATH), or read-only package check.

Requires beautifulsoup4. Does not run physical tools or touch unrelated files.
"""
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, unquote, quote

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parents[3]
DEST = REPO / 'ref-project' / 'llm-routing'
REPORTS = ['总报告.html', '线长报告.html']
META = {'阅读说明.txt', 'package_manifest.json', 'reference_sync_validation.json'}
ATTRS = ('href', 'src', 'poster', 'data')
URL_ATTR = re.compile(r'(?P<lead>\b(?:href|src|poster|data)\s*=\s*)(?P<q>[\"\x27])(?P<url>.*?)(?P=q)', re.I | re.S)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_html(p):
    return BeautifulSoup(p.read_bytes().decode('utf-8'), 'html.parser')


def local_target(parent, url, root):
    u = urlsplit(url)
    if u.scheme or u.netloc:
        assert u.scheme != 'file', f'Absolute file URL: {url}'
        return None
    p = (parent / unquote(u.path)).resolve() if u.path else None
    if p:
        assert p.is_relative_to(root.resolve()), f'Link escapes package/source: {url}'
        assert p.is_file(), f'Missing resource: {p}'
    return p, u


def urls(p):
    soup = read_html(p)
    for tag in soup.find_all(True):
        for attr in ATTRS:
            if tag.get(attr):
                yield tag[attr]


def check_links():
    pending = [DEST / n for n in REPORTS]
    reached, checks = set(), 0
    while pending:
        p = pending.pop().resolve()
        if p in reached:
            continue
        reached.add(p)
        if p.suffix.lower() not in ('.html', '.htm'):
            continue
        for url in urls(p):
            result = local_target(p.parent, url, DEST)
            if result is None:
                continue
            target, u = result
            checks += 1
            anchor_doc = target or p
            if u.fragment and anchor_doc.suffix.lower() in ('.html', '.htm'):
                soup = read_html(anchor_doc)
                a = unquote(u.fragment)
                assert soup.find(id=a) or soup.find('a', attrs={'name': a}), (anchor_doc, a)
            if target:
                pending.append(target)
    return reached, checks


def verify():
    manifest = json.loads((DEST / 'package_manifest.json').read_text(encoding='utf-8'))
    reached, checks = check_links()
    expected = {p.relative_to(DEST).as_posix() for p in reached} | META
    actual = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    assert actual == expected, {'extra': sorted(actual-expected), 'missing': sorted(expected-actual)}
    listed = {f['file'] for f in manifest['files']}
    assert listed == actual - {'package_manifest.json'}
    for f in manifest['files']:
        p = DEST / f['file']
        assert p.stat().st_size == f['bytes'] and sha(p) == f['sha256'], f['file']
    for n in REPORTS:
        soup = read_html(DEST / n)
        for plot in soup.find_all(['img', 'svg']):
            assert not plot.find_parent('details'), (n, 'hidden plot')
    study = read_html(DEST / REPORTS[0]).find(id='llaccel_core-engine-internal')
    assert study and len(study.find_all('img')) == 9
    result = {'status': 'PASS', 'files': len(actual), 'local_links_and_anchors': checks,
              'llaccel_new_figures': 9, 'all_plots_visible': True,
              'manifest_hashes_valid': True, 'exact_dependency_closure': True}
    print(json.dumps(result, ensure_ascii=False))
    return result


def sync(source):
    source = source.resolve()
    old = json.loads((DEST / 'package_manifest.json').read_text(encoding='utf-8'))
    mapping = {Path(f['source']).resolve(): f['file'] for f in old['files'] if f.get('source')}
    mapping.update({(source / n).resolve(): n for n in REPORTS})
    copied, pending, rendered = {}, [(source / n).resolve() for n in REPORTS], {}
    while pending:
        p = pending.pop()
        if p in copied:
            continue
        assert p.is_relative_to(source) and p.is_file(), p
        rel = mapping.get(p, p.relative_to(source).as_posix())
        copied[p] = rel
        if p.suffix.lower() in ('.html', '.htm'):
            def relocate(m):
                result = local_target(p.parent, m['url'], source)
                if result is None or result[0] is None:
                    return m.group(0)
                target, u = result
                pending.append(target)
                target_rel = mapping.get(target, target.relative_to(source).as_posix())
                import os
                path = os.path.relpath(DEST / target_rel, (DEST / rel).parent).replace('\\', '/')
                if path == unquote(u.path):
                    return m.group(0)
                url = quote(path, safe='/._-')
                if u.query:
                    url += '?' + u.query
                if u.fragment:
                    url += '#' + u.fragment
                return m['lead'] + m['q'] + url + m['q']
            rendered[p] = URL_ATTR.sub(relocate, p.read_bytes().decode('utf-8'))
    assert len(set(copied.values())) == len(copied), 'Destination collision'
    # Planning and source traversal finish before the first destination write.
    keep = set(copied.values()) | META
    for p, rel in copied.items():
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if p in rendered:
            out.write_bytes(rendered[p].encode('utf-8'))
            def content(doc):
                soup = BeautifulSoup(doc, 'html.parser')
                for t in soup.find_all(True):
                    for a in ATTRS:
                        t.attrs.pop(a, None)
                return str(soup)
            assert content(p.read_bytes().decode('utf-8')) == content(out.read_bytes().decode('utf-8'))
        else:
            shutil.copyfile(p, out)
            assert sha(p) == sha(out)
    removed = []
    for p in DEST.rglob('*'):
        if p.is_file() and p.relative_to(DEST).as_posix() not in keep:
            assert p.resolve().is_relative_to(DEST.resolve())
            removed.append(p.relative_to(DEST).as_posix())
            p.unlink()  # Single verified file; no recursive directory deletion.
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    info = {}
    for n in REPORTS:
        soup = read_html(DEST / n)
        info[n] = {'source': str(source / n), 'source_sha256': sha(source / n),
                   'portable_sha256': sha(DEST / n), 'tables': len(soup.find_all('table')),
                   'images': len(soup.find_all('img')), 'inline_svgs': len(soup.find_all('svg')),
                   'prose_tables_svg_preserved': True, 'only_change': 'Local resource URLs rebased',
                   'all_plots_outside_disclosures': True}
    reached, checks = check_links()
    assert {p.relative_to(DEST).as_posix() for p in reached} == set(copied.values())
    validation = {'status': 'PASS', 'updated_at': now, 'source_root': str(source),
                  'destination': str(DEST), 'reports': info,
                  'local_resource_links_checked': checks, 'all_local_links_and_anchors_valid': True,
                  'copied_assets_byte_identical_to_source': True, 'browser_render_checked': False,
                  'physical_flow_or_formal_checks_rerun': False,
                  'permission': 'Explicit user request to refresh two reports and submit to GitHub',
                  'package_policy': 'Two reports, reachable local resources, metadata; no backups or extra index',
                  'obsolete_files_removed': removed, 'report_dependency_files': len(copied),
                  'clean_package_exact_file_set_verified': True,
                  'llaccel_new_figures': 9, 'issue': 'https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3'}
    readme = '''布线分析报告阅读说明（2026-10-20）

正式入口：总报告.html、线长报告.html。直接打开即可离线阅读。
总报告：五个项目、七个案例；补入 llaccel GEMM、ATTENTION、VECTOR 的中文功能分析和九张图。
线长报告：同步源目录当前正式版本；本轮未新增该报告的线长测量结果。
所有图直接展示，较长的表格和复核说明保留在折叠区。

llaccel 状态：源分析记录确认主流程和最终 LEC 已通过；归档、派生统计任务和独立 STA 在该记录时仍待执行。
这里同步的是已保存的分析结果，没有重跑物理流程，也不把独立 STA 标为完成。
推断分类表示按网表连接推定的用途，不能当作完整恢复的 RTL 模块层级；具体边界见总报告的方法说明。
本包含报告引用的少量 RTL 片段及审计分类表，不含完整工程、原始 ODB/DEF/GDS、全量网表或工具环境，不能独立复跑物理实现。
原跨案例工作簿及汇总 CSV 保留原统计口径；llaccel 新增引擎细分表独立列出，未混入原六案例汇总。

来源：用户指定的 llm_routing_analysis 两份正式报告及引用资源；仅为便携阅读调整资源 URL。
文件与来源校验记录：package_manifest.json、reference_sync_validation.json。
GitHub 提交与审查进度以仓库 Issue #3、关联 PR 和 progress/YUZE-LU/STATUS.md 为准。
不保留备份、无用首页、未被报告引用的大体积原始物理数据。
'''
    (DEST / '阅读说明.txt').write_bytes(readme.encode('utf-8'))
    (DEST / 'reference_sync_validation.json').write_bytes((json.dumps(validation, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    files = []
    origins = {rel: str(p) for p, rel in copied.items()}
    for p in sorted(DEST.rglob('*')):
        if p.is_file() and p.name != 'package_manifest.json':
            rel = p.relative_to(DEST).as_posix()
            files.append({'file': rel, 'bytes': p.stat().st_size, 'sha256': sha(p), 'source': origins.get(rel)})
    manifest = {'created_at': now, 'scope': '5 projects / 7 cases; llaccel final LEC passed per source receipt; independent STA pending',
                'canonical_reports': REPORTS, 'source_report_preserved_except_portable_links': True,
                'aggregate_tables_scope': 'Existing six-case aggregates unchanged; llaccel engine detail tables separate',
                'package_policy': validation['package_policy'], 'checks': validation, 'files': files}
    (DEST / 'package_manifest.json').write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    return verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync', action='store_true')
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.sync:
        assert args.source, '--sync requires explicit --source'
        sync(args.source)
    else:
        verify()
