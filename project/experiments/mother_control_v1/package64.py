"""Package a qualified mother program profile; 128-bit requires prior 64-bit."""
import argparse,hashlib,json,tarfile
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--consistency',type=Path,required=True);p.add_argument('--source-archive',type=Path,action='append',required=True);p.add_argument('--marker-negative',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--instruction-bits',type=int,choices=(64,128),default=64);p.add_argument('--qualified64-manifest',type=Path);p.add_argument('--qualified64-receipt',type=Path);p.add_argument('--rtl',type=Path);a=p.parse_args()
    audit=json.loads(a.audit.read_text());gate=json.loads(a.gate.read_text())
    assert audit['passed'] and audit['full_gds_drc_performed'] and audit['full_gds_drc_items']==0
    assert gate['passed'] and gate['runs']==54 and gate['final_netlist_sha256']==audit['final_sha256']['v']
    assert gate.get('instruction_bits',64)==a.instruction_bits
    prior=prior_local=None
    if a.instruction_bits==128:
        assert a.qualified64_manifest and a.qualified64_receipt and a.rtl
        prior=json.loads(a.qualified64_manifest.read_text());prior_local=json.loads(a.qualified64_receipt.read_text())
        assert prior['passed'] and prior['instruction_bits']==64 and sum(x['runs'] for x in prior['consistency'].values())==69
        assert prior_local['passed'] and prior_local['schema']=='mother64-local-package-verification/1'
        assert prior['final_sha256']==prior_local['final_sha256']==audit['final_sha256']
        assert gate['prior64_manifest_sha256']==sha(a.qualified64_manifest)
    negative=json.loads((a.marker_negative/'result.json').read_text())
    assert negative['passed'] and negative['gds_sha256']==audit['final_sha256']['gds']
    candidate=Path(audit['candidate'])/'flow/results/nangate45/mother_control_64/base'
    entries={};reports={}
    def add(path,name):
        assert name not in entries and Path(path).is_file()
        entries[name]=Path(path)
    for kind in ('P','U','C','F','J','C-roundtrip','CF-duplex','U-duplex','U-fma-duplex'):
        directory=a.consistency/kind;receipt=directory/'result.json';report=json.loads(receipt.read_text())
        assert report['passed'] and report['instruction_bits']==a.instruction_bits and report['kind']==kind
        assert len(report['results'])==(15 if kind in ('U','C-roundtrip') else 3 if kind in ('P','C','F','J') else 9)
        assert report['mother_final_netlist_sha256']==audit['final_sha256']['v']
        assert report['actual_local_rtl'] and report['actual_block_rtl'] and report['actual_private_s_sram']
        reports[kind]=dict(runs=len(report['results']),receipt_sha256=sha(receipt))
        for f in directory.rglob('*'):
            if f.is_file() and 'obj' not in f.relative_to(directory).parts:
                add(f,'consistency/'+kind+'/'+f.relative_to(directory).as_posix())
    for suffix,digest in audit['final_sha256'].items():
        f=candidate/('6_final.'+suffix);assert sha(f)==digest;add(f,'physical/'+f.name)
    for filename,digest in audit['views_sha256'].items():
        f=a.audit.parent/filename;assert sha(f)==digest
    for directory,prefix in ((a.audit.parent,'native-audit'),(a.gate.parent,'gate')):
        for f in directory.rglob('*'):
            if f.is_file() and 'obj' not in f.relative_to(directory).parts:
                add(f,prefix+'/'+f.relative_to(directory).as_posix())
    if a.rtl:
        rtl=json.loads((a.rtl/'result.json').read_text())
        assert rtl['passed'] and not rtl['physical_netlist'] and rtl['actual_sram'] and rtl['instruction_bits']==a.instruction_bits and len(rtl['results'])==54
        for f in a.rtl.rglob('*'):
            if f.is_file() and 'obj' not in f.relative_to(a.rtl).parts:add(f,'rtl/'+f.relative_to(a.rtl).as_posix())
    work=Path(audit['candidate']);inputs=json.loads((work/'inputs.json').read_text())
    for f in work.iterdir():
        if f.is_file():add(f,'physical-execution/'+f.name)
    bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank')
    for extension,digest in inputs['bank_sha256'].items():
        files=[f for f in bank.glob('*.'+extension) if sha(f)==digest];assert len(files)==1
        add(files[0],'bank-dependency/'+files[0].name)
    for f in a.source_archive:add(f,'execution-source/'+f.name)
    selection=a.consistency/'selection.json'
    if selection.exists():add(selection,'consistency-selection.json')
    add(Path(__file__),'execution-source/package64.py')
    if prior:
        add(a.qualified64_manifest,'execution-source/qualified64-manifest.json')
        add(a.qualified64_receipt,'execution-source/qualified64-local-verification.json')
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    assert sha(deck)==audit['full_deck_sha256']
    add(deck,'native-audit/original-FreePDK45.lydrc')
    for f in a.marker_negative.iterdir():
        if f.is_file():add(f,'marker-negative/'+f.name)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=dict(schema=f'mother{a.instruction_bits}-accepted-package/1',passed=True,instruction_bits=a.instruction_bits,
        physical_cell='mother_control_64',instruction_version=2 if a.instruction_bits==64 else 1,
        shares_qualified64_physical_implementation=bool(prior),
        qualified64_manifest_sha256=sha(a.qualified64_manifest) if prior else None,
        qualified64_archive_sha256=prior_local['archive_sha256'] if prior_local else None,
        native_abi='0x01930001',resident_targets=2,global_tokens=8,program_sram_bytes=16384,
        native_audit_sha256=sha(a.audit),gate_receipt_sha256=sha(a.gate),consistency=reports,
        final_sha256=audit['final_sha256'],source_archives_sha256={f.name:sha(f) for f in a.source_archive},
        files_sha256={name:sha(path) for name,path in sorted(entries.items())},
        scope='Independent TT 1.1V 25C 300MHz mother physical implementation; functional final mother netlist with Block/LC RTL and actual private SRAM. LC PM behavioral, no SDF, no joint top-level physical or nine-target qualification.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=out/f'mother{a.instruction_bits}-accepted.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        tar.add(out/'manifest.json',arcname='manifest.json')
        for name,path in sorted(entries.items()):tar.add(path,arcname=name,recursive=False)
    assert manifest['files_sha256']=={name:sha(path) for name,path in sorted(entries.items())}
    (out/'archive.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print(json.dumps(dict(archive=str(archive),sha256=sha(archive),files=len(entries),consistency_runs=sum(x['runs'] for x in reports.values()))))

if __name__=='__main__':main()
