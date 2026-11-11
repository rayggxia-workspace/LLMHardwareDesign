"""Independent run34 receipt audit. Pure data processing; never invokes EDA."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import tarfile

EXPECTED_RESULT = 'dfd2271bccfd9c13e846fcc190e5fd0b2b321752c0c890e07e3ff3eb7957bce1'
EXPECTED_ARCHIVE = '685d99fb6a271ea597afe1b92f97d5d309beb7d028b64beb9a957a1804cc8993'
SOURCE = 'e7e8becca866e8257e026fddfc6e6215169e4015'
MACRO = 's_sram_256x128_freepdk45'


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def hash_stream(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024*1024), b''):
        h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def hash_index(path):
    pairs = [line.split('  ', 1) for line in Path(path).read_text().splitlines()]
    need(len({name for _, name in pairs}) == len(pairs), 'duplicate SHA entry')
    return {name: value for value, name in pairs}


def fields(line):
    result = {}
    for word in line.split()[1:]:
        key, value = word.split('=', 1)
        need(key not in result, 'duplicate measurement key')
        result[key] = int(value) if re.fullmatch(r'-?\d+', value) else value
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parent)
    args = p.parse_args()
    run, output = args.run.resolve(), args.out.resolve()
    rec, results = run/'receipts', run/'receipts/results'
    r, col, manifest = read(results/'result.json'), read(rec/'collection.json'), read(rec/'inputs.json')
    need(sha(results/'result.json') == EXPECTED_RESULT, 'result SHA changed')
    need(sha(run/'receipts.tar') == EXPECTED_ARCHIVE, 'archive SHA changed')
    need(r['passed'] and r['functional_passed'] and col['whole_run_passed'] and col['functional_passed'], 'run did not pass')
    need(col['terminal_state'] == 'COMPLETED' and col['exit_code'] == '0:0', 'Slurm terminal failure')
    need(int(r['job']) == col['job'] == 102033 and r['workers'] == 4 and col['node'] == r['node'] == 'node1', 'job/CPU/node mismatch')
    need(r['source_commit'] == col['source_commit'] == manifest['source_commit'] == SOURCE, 'source commit mismatch')
    need(sha(rec/'inputs.json') == r['manifest_sha256'], 'manifest SHA mismatch')
    need(hash_index(rec/'source-files.sha256') == manifest['code_sha256'], 'server source index mismatch')
    need(hash_index(rec/'input-files.sha256') == manifest['input_sha256'] == {}, 'unexpected extra inputs')
    need(len(manifest['code_sha256']) == col['source_files_verified'] == 73, 'source count mismatch')
    need(sha(run/'payload.tar') == manifest['payload_sha256'], 'payload archive mismatch')
    with tarfile.open(run/'payload.tar') as archive:
        need(len(archive.getnames()) == 73 and len(set(archive.getnames())) == 73, 'payload membership mismatch')
        for name, expected in manifest['code_sha256'].items():
            need(hash_stream(archive.extractfile('source/'+name)) == expected, 'actual archived source mismatch '+name)
    need(all(manifest['code_sha256'][name] == digest for name, digest in r['source_sha256'].items()), 'runner source subset mismatch')
    all_hash = hash_index(rec/'output-files.sha256')
    need(len(all_hash) == col['total_result_files_hashed'] == 1790, 'server output index count mismatch')
    local = [p for p in results.rglob('*') if p.is_file()]
    need(len(local) == col['result_files_selected'] == 151, 'returned output missing')
    for path in local:
        name = path.relative_to(rec).as_posix()
        need(all_hash[name] == sha(path), 'returned output SHA mismatch '+name)
    for name, digest in r['output_files_sha256'].items():
        need(all_hash['results/'+name] == digest, 'job/server output receipt disagreement '+name)
    metadata = [p for p in rec.iterdir() if p.is_file()]
    need(len(metadata) == 10, 'metadata count mismatch')
    with tarfile.open(run/'receipts.tar') as archive:
        members = archive.getnames()
        need(len(members) == len(set(members)) == 161, 'receipt archive membership mismatch')
        need(set(members) == {p.relative_to(rec).as_posix() for p in local+metadata}, 'extracted archive differs')
        for path in metadata:
            need(hash_stream(archive.extractfile(path.name)) == sha(path), 'local metadata differs from archive '+path.name)
    need(sha(rec/'job.sh') == manifest['code_sha256']['project/experiments/shared_a32_native/job.sh'], 'Slurm wrapper source differs')
    tool_hash = hash_index(rec/'tools.sha256')
    need(tool_hash[r['bank']['path']] == r['bank']['sha256'] == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7', 'SRAM model identity mismatch')
    need(r['verilator_binary_sha256'] in tool_hash.values(), 'Verilator identity missing')

    counts = dict(runs=0,builds=0,main_numeric=0,refill_numeric=0,compat_pairs=0,compared_events=0,
                  invalid_masks=0,duplicate_tags=0,busy_stall_cycles=0,control_categories={},pool_word_checks=0)
    prefix_counts = {}
    for cmd in r['commands']:
        need(cmd['exit_code'] == 0 and not cmd['timed_out'], 'RTL command failure')
        need(sha(results/cmd['log']) == cmd['sha256'], 'RTL command log differs')
        if '-build.log' in cmd['log']:
            counts['builds'] += 1
            need(cmd['command'][cmd['command'].index('-j')+1] == '4', 'build exceeded/missed CPU allocation')
    need(counts['builds'] == 24 and len(r['commands']) == 100, 'build/lint/tool command count')
    need(len(r['tests']) == 24 and all(t['passed'] for t in r['tests'].values()), 'incomplete functional suite')
    for label, test in r['tests'].items():
        need([(x['reset_mode'], x['seed']) for x in test['runs']] == [(1,247),(2,247),(2,248)], 'seed coverage mismatch')
        kind = label.split('-')[0]
        prefix = 'POOL' if kind == 'pool' else 'A32_M' if kind == 'm' else 'A32_CONTROL' if kind == 'control' else 'A32_PAIR' if kind == 'pair' else 'SHARED_PAIR'
        prefix_counts.setdefault(kind, dict(runs=0, main_numeric=0, refill_numeric=0))
        for item in test['runs']:
            counts['runs'] += 1; prefix_counts[kind]['runs'] += 1
            path = results/item['log']; need(sha(path) == item['log_sha256'], 'test log SHA mismatch')
            text = path.read_text(errors='strict')
            passed = [fields(line) for line in text.splitlines() if line.startswith(prefix+'_PASS')]
            measures = [fields(line) for line in text.splitlines() if line.startswith(prefix+'_MEASURE ')]
            need(passed == [item['checks']] and measures == item['measurements'], 'raw PASS/MEASURE differs from parsed receipt '+label)
            need(all(m['cycles'] > 0 for m in measures), 'nonpositive measurement')
            num = item['checks'].get('numeric',0)
            counts['main_numeric'] += num; prefix_counts[kind]['main_numeric'] += num
            refill = sum(m.get('refill_numeric',0) for m in measures)
            counts['refill_numeric'] += refill; prefix_counts[kind]['refill_numeric'] += refill
            for field in ('invalid_masks','duplicate_tags'):
                counts[field] += sum(m.get(field,0) for m in measures)
            counts['busy_stall_cycles'] += sum(m.get('busy_stalls',0) for m in measures)
            if kind == 'pool':
                need(item['checks']['reads'] == 522 and item['checks']['writes'] == 525 and item['checks']['a_words'] == 1659, 'pool fixed work changed')
                need(item['checks']['fifo0_peak'] == item['checks']['fifo1_peak'] == 4 and item['checks']['errors'] == 15, 'pool credit/negative coverage missing')
                counts['pool_word_checks'] += item['checks']['a_words']
            if kind == 'm':
                need(num == 2432 and item['checks']['shapes'] == 64, 'M oracle count')
                if label.startswith('m-w2'):
                    need(measures[0]['invalid_masks'] == measures[0]['duplicate_tags'] == 64, 'A2 atomic rejection coverage')
            if kind == 'control':
                for field in ('clear_all','clear_same','clear_other','start_same','busy_other','tail_garbage','reset_clear'):
                    need(measures[0][field] == 1, 'control case absent')
                    counts['control_categories'][field] = counts['control_categories'].get(field,0)+1
                need(measures[0]['legal_pairs'] == 5, 'control legal-pair count')
            if kind == 'pair':
                need(num == 4864 and item['checks']['scenarios'] == 64 and {m['scenario'] for m in measures} == set(range(64)), 'equal-work shape count')
            if kind in ('baseline','candidate16','candidate32'):
                need(num == 3456 and item['checks']['contexts'] == 288 and refill == 16, 'legacy arithmetic/lifecycle count')
            if kind in ('baseline','candidate16'):
                events = [line for line in text.splitlines() if line.startswith('COMPAT_EVENT ')]
                events.sort(key=lambda line:(int(re.search(r'cycle=(\d+)',line).group(1)),line))
                canonical = ('\n'.join(events)+'\n').encode()
                need(len(events) == item['event_count'] and (results/item['event_log']).read_bytes() == canonical, 'raw cycle events differ from canonical file')
                need(hashlib.sha256(canonical).hexdigest() == item['event_sha256'], 'canonical event SHA differs')
    for suffix in ('s0-rw0','s1-rw0','s0-rw1','s1-rw1'):
        for old,new in zip(r['tests']['baseline-'+suffix]['runs'],r['tests']['candidate16-'+suffix]['runs']):
            need(all(old[k] == new[k] for k in ('seed','reset_mode','checks','measurements','event_count','event_sha256')), 'default16 exact compatibility mismatch')
            need((results/old['event_log']).read_bytes() == (results/new['event_log']).read_bytes(), 'actual event bytes mismatch')
            counts['compat_pairs'] += 1; counts['compared_events'] += old['event_count']
    need(counts['runs'] == 72 and counts['compat_pairs'] == r['exact_16B_compatibility_pairs'] == 12 and counts['compared_events'] == 430008, 'suite count mismatch')
    need(counts['main_numeric'] == 211968 and counts['refill_numeric'] == 576, 'numerical check total mismatch')

    equal = []
    scalar_checksum_checks = 0
    for ctx in (0,8):
        for one,two in zip(r['tests']['pair-w1-c'+str(ctx)]['runs'],r['tests']['pair-w2-c'+str(ctx)]['runs']):
            for before,after in zip(one['measurements'],two['measurements']):
                excluded = {'words','cycles','initialization_cycles','processing_cycles','load_cycles','compute_cycles','feed_span_cycles','a_beats'}
                need({k:v for k,v in before.items() if k not in excluded} == {k:v for k,v in after.items() if k not in excluded}, 'equal-work payload/commands/checksum changed')
                need(before['initialization_cycles'] == after['initialization_cycles'] and before['compute_cycles'] == after['compute_cycles'], 'unrelated stage timing changed')
                # Recompute the logged checksum directly from the documented
                # synthetic A/B payload, independently of the RTL result path.
                for worker in (0,1):
                    wanted = 0
                    for row in range(before['rows']):
                        for column in range(8):
                            for k in range((before['tiles']-1)*8+before['lastk']):
                                av = ((row*7+k*3+before['scenario']*5)%23-11)*(313 if before['Awide'] else 1)
                                bv = ((worker*11+column*5+k*7+before['scenario']*3)%19-9)*(211 if before['Bwide'] else 1)
                                wanted += av*bv
                    need(before['checksum'+str(worker)] == after['checksum'+str(worker)] == wanted, 'independent scalar checksum mismatch')
                    scalar_checksum_checks += 2
            sums = {field:[sum(m[field] for m in run['measurements']) for run in (one,two)] for field in
                    ('cycles','initialization_cycles','processing_cycles','load_cycles','compute_cycles','feed_span_cycles','a_words','a_beats','commands','numeric')}
            equal.append(dict(contexts=ctx,reset_mode=one['reset_mode'],seed=one['seed'],stage_sums=sums,
                              processing_speed_gain_pct=(sums['processing_cycles'][0]/sums['processing_cycles'][1]-1)*100,
                              initialization_plus_processing_gain_pct=(sums['cycles'][0]/sums['cycles'][1]-1)*100,
                              excludes_release=True,no_token_s_projection=True))

    area = r['mapped_area']
    need(area == read(results/'area/result.json') and area['status'] == 'passed', 'area receipt differs')
    need(area['allocated_cpus'] == 4 and area['synthesis_concurrency'] == area['threads_per_tool'] == 1, 'area resource budget drift')
    need(area['standard_liberty']['sha256'] == '8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1', 'standard liberty identity')
    need(area['bank_liberty']['sha256'] == '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189', 'macro liberty identity')
    for cmd in area['commands']:
        if cmd['log'] == 'abc-version.log':
            need(cmd['command'] == [area['tools']['abc']['path'], '-h'] and cmd['exit_code'] == 1 and
                 'UC Berkeley, ABC 1.01' in (results/'area'/cmd['log']).read_text(), 'unexpected ABC help/version query receipt')
        else:
            need(cmd['exit_code'] == 0, 'synthesis/tool command failed')
        need(sha(results/'area'/cmd['log']) == cmd['log_sha256'], 'synthesis command log changed')
    need(len(area['commands']) == 8 and len(area['modules']) == 6, 'area command/module count mismatch')
    area_rows = []; omitted = []
    for name, module in area['modules'].items():
        stat = read(results/'area'/name/'stat.json')
        stats = next(v for k,v in stat['modules'].items() if k.lstrip('\\') == module['top'])
        expected_banks = 8 if name.startswith('pool_') else 0
        need(stats['num_cells_by_type'] == module['cell_types'], 'stat/netlist-receipt cell counts differ '+name)
        need(stats['num_cells_by_type'].get(MACRO,0) == module['physical_4KiB_banks'] == expected_banks, 'macro count mismatch')
        need(stats['num_cells'] == sum(stats['num_cells_by_type'].values()) and stats['num_processes'] == stats['num_memories'] == 0, 'unmapped high-level design state')
        need(not any(k.startswith('$') for k in stats['num_cells_by_type']) and module['no_unmappedcells'] is True and module['unmapped_cell_types'] == [], 'unmapped-cell evidence')
        need(Decimal(str(stats['area'])) == Decimal(str(module['standard_cell_area_um2'])), 'area result/stat differs')
        need(area['bank_liberty']['path'] not in stat['invocation'] and area['standard_liberty']['path'] in stat['invocation'], 'stat includes macro area or wrong library')
        flow = (results/'area'/name/'synth.ys').read_text()
        need('check -assert' in flow and ('chparam -set A_WORDS_PER_BEAT '+str(module['configuration']['A_WORDS_PER_BEAT'])) in flow, 'synthesis check/config missing')
        need(module['source_sha256'] == manifest['code_sha256'][module['source']], 'mapped source differs from RTL manifest')
        for artifact,info in module['artifacts'].items():
            need(all_hash['results/area/'+info['path']] == info['sha256'], 'area output SHA receipt disagreement')
            if artifact.startswith('mapped.'):
                need(not (results/'area'/info['path']).exists(), 'unexpected locally claimed large netlist')
                omitted.append(dict(server_path=col['run_root']+'/results/area/'+info['path'],sha256=info['sha256']))
        area_rows.append(dict(module=name,area_um2=module['standard_cell_area_um2'],macro_count=expected_banks,configuration=module['configuration']))
    areas = {x['module']:Decimal(str(x['area_um2'])) for x in area_rows}
    delta_pool = areas['pool_a2']-areas['pool_a1']
    delta_m = areas['m_a2']-areas['m_a1']
    delta_ctx = areas['m_context8_a2']-areas['m_context8_a1']
    total = delta_pool+2*delta_ctx
    need(total == Decimal(str(area['aggregate']['standard_cell_delta_um2'])) and area['aggregate']['SRAM_macro_delta'] == 0, 'area aggregate double-counted/wrong')
    summary = dict(passed=True,scope='Independent local receipt/data audit, no EDA rerun',run='run34',source_commit=SOURCE,job=102033,node='node1',elapsed=col['elapsed'],
                   result_sha256=EXPECTED_RESULT,receipt_archive_sha256=EXPECTED_ARCHIVE,audit_script_sha256=sha(__file__),
                   integrity=dict(archived_source_files_rehashed=73,extra_input_files=0,returned_result_files_rehashed=151,metadata_archive_members_verified=10,
                                  complete_server_output_index_entries=1790,job_non_object_SHA_records_matched=162,large_netlists_locally_rehashed=False),
                   independent_equal_work_scalar_checksum_checks=scalar_checksum_checks,
                   tools=r['versions'],verilator_sha256=r['verilator_binary_sha256'],
                   area_version_query_note='ABC -h intentionally exits 1 while printing its help/version banner; all six actual synthesis commands exit 0.',
                   counts=counts,numerical_by_suite=prefix_counts,
                   equal_work=equal,area=dict(modules=area_rows,standard_library=area['standard_liberty'],macro_library=area['bank_liberty'],
                   pool_delta_um2=float(delta_pool),single_plain_M_delta_um2=float(delta_m),single_context8_M_delta_um2=float(delta_ctx),
                   one_pool_plus_two_context8_M_delta_um2=float(total),one_pool_plus_two_context8_M_delta_mm2=float(total/Decimal(1000000)),
                   alternate_one_pool_plus_two_plain_M_delta_um2=float(delta_pool+2*delta_m),macro_delta=0,
                   macro_area_in_standard_cell_stat=False,local_stat_and_log_checks_passed=True,
                   mapped_cell_inventory_check='Server checked every mapped cell against locked Liberty; local stat counters and no_unmapped receipt agree. Large netlists not re-opened locally.',
                   server_only_netlists=omitted),
                   limitations=['Counters describe checks across widths/seeds, including old-baseline runs; they are not distinct model outputs.',
                   'Pool lane_matrix dual/single beats are cumulative, while its read/word fields are scenario deltas.',
                   'FIFO full/return/pop is guarded every cycle but the exact count3+pending1+pop1 combination has no separate coverage hit counter.',
                   'Only native S8/S16 and M contexts0/8; no full DDR/DMA bridge, full-model token/s, frequency, placement/routing, power or whole-chip area qualification.',
                   'Area excludes unmeasured P/pair glue; M plain/context8 are alternatives and must not both be added.'])
    output.mkdir(parents=True, exist_ok=True)
    (output/'audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines = ['# run34 原生A16→32B独立审计','',
             'Issue247 / PR243。本次为实际服务器回执的纯数据复核，未重跑EDA。', '',
             f'作业102033 / node1 / 4CPU / {col["elapsed"]}，COMPLETED 0:0。源码 `{SOURCE}`。',
             f'结果SHA-256 `{EXPECTED_RESULT}`；回收归档SHA-256 `{EXPECTED_ARCHIVE}`。','',
             '## 完整性与验证','',
             '- 上传包73份源码逐字节重哈希，与部署manifest及服务器source索引一致；额外输入为0。151份本地结果文件SHA与1790项全输出索引一致，10份元数据与归档逐字节一致。',
             '- 24构建、72运行、2次严格pool lint及2工具查询均成功；逐run原始PASS/MEASURE与result JSON一致。',
             '- 12对默认16B比较：从原始日志重新提取430,008条周期事件，规范排序后与两侧event文件逐字节相等，完整周期/有效载荷不删字段。两侧合计860,016条日志事件，不能称为860,016项独立比较。',
             '- 主数值检查211,968次：M 29,184、三组历史pair 124,416、等工作pair 58,368；另重填576次。包含旧基线与重复种子，属于检查次数。候选32B历史pair为41,472主检查及192重填。本地另从A/B定义独立标量复算等工作bench的1536个已记录结果校验和；M逐元素判定仍依据实际RTL运行断言。',
             '- M非法mask384次、重复tag384次均未部分写；busy bank共60,606阻塞拍。七类控制检查各6次、合法双beat30次。pool共9,954个128bit词核验，全部run达到每P四槽峰值。','',
             '## 等工作速度','',
             '| M配置 | 16B处理周期 | 32B处理周期 | 处理吞吐提升 | 含初始化吞吐提升 |','| --- | ---: | ---: | ---: | ---: |']
    for ctx in (0,8):
        e=next(x for x in equal if x['contexts']==ctx)
        lines.append('| {} | {} | {} | {:.6f}% | {:.6f}% |'.format(ctx,*e['stage_sums']['processing_cycles'],e['processing_speed_gain_pct'],e['initialization_plus_processing_gain_pct']))
    lines += ['', '每组64场景的A词1520、数值检查4864、初始化2416周期均不变；A beat由1520减为840，供数跨度合计1552→904，LOAD合计2468→1898。普通/8context的M计算周期分别8426/13984，宽度变化后均不变。',
              '周期不含测量后的RELEASE；阶段合计是两P工作量，不是墙钟分解。不能把该比值乘旧SystemC token/s。','',
              '## 面积核验','',
              '| 模块 | 标准单元面积 µm² | SRAM宏数量 |','| --- | ---: | ---: |']
    for x in area_rows:lines.append('| {} | {:.3f} | {} |'.format(x['module'],x['area_um2'],x['macro_count']))
    lines += ['',f'同Nangate45库下，pool增量{delta_pool} µm²；每颗普通M增量{delta_m} µm²；每颗8context M增量{delta_ctx} µm²。主配置一pool＋两颗8context M净增 **{total} µm² = {total/Decimal(1000000)} mm²**，共享SRAM仍8宏、无新增容量宏。',
              '6项实际综合命令均exit0，stat面积及cell计数与面积回执一致；综合脚本执行check -assert，stat仅使用标准单元库，SRAM宏面积不混入。ABC的-h版本/帮助查询按工具行为exit1并输出合法banner，不是综合失败。服务器逐cell库映射检查与本地stat/no_unmapped回执一致。12份大mapped.json/mapped.v仅留服务器及SHA索引，本地没有重新打开或逐cell核验，不声称已完成本地网表审查。',
              '上述净增不含P/pair外围及物理布线，也不同时累加普通M和context M两种替代实现。','',
              '## 范围','',
              '实际覆盖原生S8/S16、M_CONTEXTS0/8、同步reset/冷复位、默认兼容与双词数据/控制。没有完整DDR DMA桥、原生完整LLM token/s、STA/P&R/功耗或芯片面积资格。FIFO逐拍信用检查通过，但特定count3+pending1+pop1组合没有单独命中计数。详细逐项SHA、工具身份和服务器大网表位置见audit.json。','']
    (output/'audit.md').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps(dict(passed=True,counts=counts,audit_json_sha256=sha(output/'audit.json'),audit_md_sha256=sha(output/'audit.md'),script_sha256=sha(__file__)),ensure_ascii=False))


if __name__ == '__main__':
    main()
