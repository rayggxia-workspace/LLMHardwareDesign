"""Materialize main64 profiles; namespace generated modules without changing logic."""
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
from pathlib import Path
from contract import ROOT,HERE,common_ports


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def namespace(folder,prefix):
    originals={p.name:p.read_text() for p in folder.glob('*.sv')}
    modules=set()
    for text in originals.values():modules.update(re.findall(r'\bmodule\s+(\w+)',text))
    changes={n:prefix+n for n in modules}
    pattern=re.compile(r'\b('+'|'.join(map(re.escape,sorted(modules,key=len,reverse=True)))+r')\b')
    for name,text in originals.items():
        transformed=pattern.sub(lambda m:changes[m[0]],text)
        # Renaming must be bijective; reversing it must recover every byte.
        reverse=re.compile(r'\b('+'|'.join(map(re.escape,sorted(changes.values(),key=len,reverse=True)))+r')\b')
        assert reverse.sub(lambda m:{v:k for k,v in changes.items()}[m[0]],transformed)==text
        (folder/name).write_text(transformed)
    return {'module_map':changes,'original_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in originals.items()},
            'generated_sha256':{p.name:sha(p) for p in folder.glob('*.sv')}}


def check_interface(path):
    text=path.read_text().split('\n);',1)[0]
    text=text[re.search(r'\b(?:input|output)\s+wire',text).start():]
    actual_ports={};direction=width=None
    for item in text.split(','):
        item=item.strip()
        match=re.fullmatch(r'(input|output)\s+wire\s*(\[\d+:\d+\])?\s*(\w+)',item)
        if match:direction,width,name=match.groups();width=width or ''
        else:
            assert direction and re.fullmatch(r'\w+',item),(path.name,item)
            name=item
        assert name not in actual_ports,(path.name,name)
        actual_ports[name]=[direction,width]
    for name,(direction,width) in common_ports().items():
        actual='clk' if name=='clk_i' and 'pu_' in path.name else name
        assert actual_ports.get(actual)==[direction,width],(path.name,name,width,actual_ports.get(actual))


def stage(out):
    sys.path.insert(0,str(ROOT/'project/control_main64_v1'))
    from check import check,frozen_control
    check();out.mkdir(parents=True,exist_ok=False)
    frozen=frozen_control(out/'frozen-control')
    archive=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02/bundle.tar.gz')
    env=dict(os.environ,CFJ_CONTROL64_SOURCE=str(frozen),PU_INSTRUCTION_BITS='64')
    bundle=out/'native'
    subprocess.run([sys.executable,'-B',str(ROOT/'project/experiments/cfj_leaf_base/stage_regression.py'),str(archive),str(bundle),'controller64'],env=env,check=True)
    generated=out/'generated';generated.mkdir()
    reports={}
    sys.path.insert(0,str(ROOT/'project/experiments/pu_leaf_base'))
    controlled=load('r82_main_pu_controlled',ROOT/'project/experiments/pu_leaf_base/controlled.py')
    oldbits=os.environ.get('PU_INSTRUCTION_BITS');os.environ['PU_INSTRUCTION_BITS']='64'
    for letter in ('p','u'):
        target=generated/letter;target.mkdir()
        folder,top=controlled.stage(target,letter.upper())
        # Only module identifiers change; includes remain relative to this type.
        check_interface(folder/(top+'.sv'))
        reports[letter]=namespace(folder,'r82_'+letter+'_')
    if oldbits is None:os.environ.pop('PU_INSTRUCTION_BITS',None)
    else:os.environ['PU_INSTRUCTION_BITS']=oldbits
    ctrl=bundle/'staged/project/control_rtl_min_v0_1'
    explicit_outputs={}
    for letter in ('c','f','j'):
        folder=generated/letter;folder.mkdir()
        for name in ('lc_min_controller.sv',):shutil.copyfile(ctrl/name,folder/name)
        for p in ctrl.glob('*.svh'):shutil.copyfile(p,folder/p.name)
        for name in ('cfj_group_'+letter+'.sv','pj_native_service.sv','ucf_native_service.sv','stored_link.sv'):
            shutil.copyfile(bundle/'design'/name,folder/name)
        if letter=='j':
            # main's JOIN-only adapter omits ten unused output connections.
            # Make them explicit opens; no input, signal or behavior changes.
            path=folder/'cfj_group_j.sv';before=path.read_text()
            anchor="    pj_native_service #(.JOIN_BLOCK(1'b1)) dispatch(\n"
            unused=('load_valid','load_take','load_fields','cmd_valid','cmd_take','cmd_fields','cmd_data','gate_valid','gate_take','gate_fields')
            assert before.count(anchor)==1
            opening=''.join('        .'+name+'(),\n' for name in unused)
            after=before.replace(anchor,anchor+opening)
            assert after.replace(anchor+opening,anchor)==before
            path.write_text(after)
            explicit_outputs={'module':'pj_native_service','instance':'dispatch','pins':list(unused),
                'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':sha(path),'reverse_verified':True}
        check_interface(folder/('cfj_group_'+letter+'.sv'))
        reports[letter]=namespace(folder,'r82_'+letter+'_')
    sources=[]
    for letter in ('p','u'):sources+=sorted((generated/letter/'lc').glob('*.sv'))
    for letter in ('c','f','j'):sources+=sorted((generated/letter).glob('*.sv'))
    # No legacy reference controller, fixture module or fixture PM enters the DUT.
    native=bundle/'staged/native';pj=bundle/'staged/pj/project/rtl'
    sources+=[p for p in sorted(native.glob('*.sv')) if not p.name.startswith('tb_')]
    sources+=sorted((pj/'block_pj_v1').glob('*.sv'))+[pj/'block_v2/block_v2_m.sv',pj/'block_v1/transaction6k.sv']
    # Prefer the main originals for the complete P/U and C/F/J data groups.
    for family in ('pu_leaf_base','block_cfj_v1','s_sram'):
        for p in sorted((ROOT/'project/rtl'/family).glob('*.sv')):
            sources=[s for s in sources if s.name!=p.name];sources.append(p)
    sources+=[ROOT/'project/control_rtl_min_v0_1/two_local_link.sv',ROOT/'project/control_boot_v1/control_boot_manager.sv',ROOT/'project/control_five_boot_v1/native_result_fifo.sv']
    sources+=[ROOT/'project/rtl/mother_control_v1'/n for n in ('mc_min_controller.sv','control_pm.sv','mother_control_64.sv')]
    sources+=[HERE/(n+'.sv') for n in ('main64_endpoint','main64_control_top','main64_host_front','main64_boot_top')]
    # pj_mem_port and ucf_s_compute_client appear in more than one main family;
    # these common source files must be byte-identical before deduplicating.
    by_name={}
    for p in sources:
        if p.is_relative_to(generated):continue
        if p.name in by_name:assert p.read_bytes()==by_name[p.name].read_bytes(),p.name
        by_name[p.name]=p
    # Generated per-type files intentionally share filenames but not modules.
    sources=list(dict.fromkeys(sources))
    bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    assert sha(bank)=='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    sources.append(bank)
    def label(p):
        if p.is_relative_to(out):return 'stage/'+p.relative_to(out).as_posix()
        if p.is_relative_to(ROOT):return p.relative_to(ROOT).as_posix()
        return 'qualified-bank.v'
    include=[ROOT/'project/rtl/mother_control_v1',native,*[generated/l/'lc' for l in ('p','u')]]
    for l in ('c','f','j'):include.append(generated/l)
    (out/'sources.json').write_text(json.dumps({'sources':list(map(str,sources)),'include_dirs':list(map(str,include)),'waiver':str(native/'native_r.vlt')},indent=2)+'\n')
    result={'schema':'main64-boot-staging/1','passed':True,'type_interfaces':5,'common_ports':common_ports(),'profiles':reports,
            'main_raw_sources_unchanged':True,'namespace_reversal_checked':True,'explicit_unused_j_outputs':explicit_outputs,
            'sources_sha256':{label(p):sha(p) for p in sources}}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS R8.1 five actual generated interfaces; R8.2 production source staging',len(sources))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();stage(a.out.resolve())
