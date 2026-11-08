"""Read back the complete nine-pair R8.2 campaign and verify raw evidence."""
from pathlib import Path
import argparse,hashlib,json,re,tarfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--guards-root',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
    expected={(m,r,s) for m in range(7) for r,s in ((1,143),(2,143),(2,144))}
    inputs=json.loads((root/'inputs.json').read_text())
    for name,digest in inputs.items():assert sha(root/'source'/name)==digest,name
    profiles={};artifacts={};raw=[];guard_files=[];guards={}
    for i in range(9):
        result=root/f'results-{i}'/'result.json';data=json.loads(result.read_text())
        assert data['passed'] and len(data['results'])==21
        assert {(x['mode'],x['reset_mode'],x['seed']) for x in data['results']}==expected
        assert data['real_pm_count']==3 and not data['local_pm_behavioral_fixture']
        for row in data['results']:
            log=result.parent/f"mode-{row['mode']}-init-{row['reset_mode']}-{row['seed']}.log"
            assert sha(log)==row['log_sha256'],log
            assert len(re.findall(r'^PASS main64-boot ',log.read_text(),re.M))==1,log
            raw.append(log)
        for name,digest in data['image_sha256'].items():assert sha(result.parent/'images'/name)==digest
        for name,digest in data['source_sha256'].items():assert sha(Path(name))==digest,name
        structure=root/f'structure-{i}'/'result.json';st=json.loads(structure.read_text())
        assert st['passed'] and [st[x] for x in ('mother','locals','pm','program_banks')]==[1,2,3,12]
        assert st['forbidden_control_warnings']==[]
        for name,digest in st['artifacts_sha256'].items():assert sha(structure.parent/name)==digest
        design=json.loads((structure.parent/'control.json').read_text());modules=design['modules']
        def groups(name):
            h=modules.get(name,{}).get('attributes',{}).get('hdlname',name)
            if h in ('pu_p_group','pu_u_group','block_cfj_cf','block_cfj_j'):return 1
            return sum(groups(c['type']) for c in modules.get(name,{}).get('cells',{}).values() if c['type'] in modules)
        assert groups('main64_boot_top')==2
        manifest=root/f'stage-{i}'/'manifest.json';stage=json.loads(manifest.read_text())
        assert stage['passed'] and stage['type_interfaces']==5 and stage['namespace_reversal_checked']
        assert stage['explicit_unused_j_outputs']['reverse_verified']
        for name,digest in stage['sources_sha256'].items():
            if name.startswith('stage/'):path=root/f'stage-{i}'/name[6:]
            elif name=='qualified-bank.v':path=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
            else:path=root/'source'/name
            assert sha(path)==digest,name
        profiles[str(i)]={'pair':data['pair'],'rtl_passed':21,'structure':{k:st[k] for k in ('passed','mother','locals','pm','program_banks','warnings')},
            'native_groups':2,'raw_result_sha256':sha(result),'raw_structure_sha256':sha(structure),'stage_manifest_sha256':sha(manifest),'results':data['results']}
        if a.guards_root:
            gr=a.guards_root.resolve();guard=gr/f'guards-{i}'/'result.json';gd=json.loads(guard.read_text())
            assert gd['passed'] and len(gd['results'])==3 and gd['pair']==data['pair']
            assert {(x['reset_mode'],x['seed']) for x in gd['results']}=={(1,143),(2,143),(2,144)}
            dut={k:v for k,v in data['source_sha256'].items() if not k.endswith('/tb_main64_boot.sv')}
            assert gd['source_sha256']==dut,'supplemental DUT differs'
            for row in gd['results']:
                log=guard.parent/f"guards-init-{row['reset_mode']}-{row['seed']}.log"
                assert sha(log)==row['log_sha256'] and len(re.findall(r'^PASS main64-guards ',log.read_text(),re.M))==1
                guard_files.append((log,'supplement/'+log.relative_to(gr).as_posix()))
            bench=guard.parent/'tb_main64_guards.sv';assert sha(bench)==gd['bench_sha256']
            guard_files += [(guard,'supplement/'+guard.relative_to(gr).as_posix()),(bench,'supplement/'+bench.relative_to(gr).as_posix())]
            guards[str(i)]={'passed':3,'pair':gd['pair'],'same_dut_sha_verified':True,'results':gd['results'],'receipt_sha256':sha(guard)}
        for path in (result,structure,manifest):raw.append(path)
    for path in raw:artifacts[path.relative_to(root).as_posix()]=sha(path)
    for path,name in guard_files:artifacts[name]=sha(path)
    record=dict(schema='main64-r81-r82-validation/1',source_snapshot_commit=(root/'source-commit.txt').read_text().strip(),source_tar_sha256=sha(root/'source.tar'),
        input_files=len(inputs),source_input_sha256=inputs,rtl_passed=189,rtl_total=189,structure_passed=9,structure_total=9,profiles=profiles,
        collector_sha256=sha(Path(__file__)),raw_artifacts_sha256=artifacts,
        tools={'python':'3.12.7','verilator':'5.042 repro02','yosys':'0.63 git70a11c6bf','container_sha256':sha(Path('/public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif'))},
        scope='main64 controllers and actual Block/private S; three real program SRAM wrappers; unified host load/readback CRC/deploy/start; no fixture PM; hand-authored programs; candidate control/glue structural synthesis',
        pending=['R8.3 compiler/audit alignment','R8.4 full identity/transport/cancel/recovery, including J-to-P','R8.5 coverage closure','R8.6 source/macro/SDC refreeze','combined mapped timing and physical signoff'])
    if a.guards_root:
        gr=a.guards_root.resolve();gi=json.loads((gr/'inputs.json').read_text())
        for name,digest in gi.items():assert sha(gr/'source'/name)==digest,name
        record.update(guard_profiles=guards,guard_passed=27,guard_total=27,total_rtl_executions=216,
            guard_snapshot_commit=(gr/'source-commit.txt').read_text().strip(),guard_source_tar_sha256=sha(gr/'source.tar'),
            primary_and_supplemental_dut_identical=True,execution_count_note='189 primary plus 27 overlapping-path deployment guard executions; not 216 independent functional coverage bins')
    a.out.write_text(json.dumps(record,indent=2)+'\n')
    with tarfile.open(root/'receipts.tar.gz','w:gz') as tar:
        for path in raw+[a.out,root/'inputs.json',root/'source-commit.txt',root/'source.tar.sha256']:
            tar.add(path,arcname=path.relative_to(root).as_posix())
        for path,name in guard_files:tar.add(path,arcname=name)
    print(json.dumps({'rtl':record.get('total_rtl_executions',189),'structure':9,'input_files':len(inputs),'collected_sha256':sha(a.out),'receipts_sha256':sha(root/'receipts.tar.gz')}))


if __name__=='__main__':main()
