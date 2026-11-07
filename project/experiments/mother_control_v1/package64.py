"""Package only a fully qualified 64-bit mother and actual Block consistency."""
import argparse,hashlib,json,tarfile
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--consistency',type=Path,required=True);p.add_argument('--source-archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    audit=json.loads(a.audit.read_text());gate=json.loads(a.gate.read_text())
    assert audit['passed'] and audit['full_gds_drc_performed'] and audit['full_gds_drc_items']==0
    assert gate['passed'] and gate['runs']==54 and gate['final_netlist_sha256']==audit['final_sha256']['v']
    candidate=Path(audit['candidate'])/'flow/results/nangate45/mother_control_64/base'
    entries={};reports={}
    def add(path,name):
        assert name not in entries and Path(path).is_file()
        entries[name]=Path(path)
    for kind in ('P','U','C','F','J','CF-duplex','U-duplex','U-fma-duplex'):
        directory=a.consistency/kind;receipt=directory/'result.json';report=json.loads(receipt.read_text())
        assert report['passed'] and report['instruction_bits']==64 and report['kind']==kind
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
    work=Path(audit['candidate']);inputs=json.loads((work/'inputs.json').read_text())
    for f in work.iterdir():
        if f.is_file():add(f,'physical-execution/'+f.name)
    bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank')
    for extension,digest in inputs['bank_sha256'].items():
        files=[f for f in bank.glob('*.'+extension) if sha(f)==digest];assert len(files)==1
        add(files[0],'bank-dependency/'+files[0].name)
    add(a.source_archive,'execution-source/'+a.source_archive.name)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=dict(schema='mother64-accepted-package/1',passed=True,instruction_bits=64,
        native_abi='0x01930001',resident_targets=2,global_tokens=8,program_sram_bytes=16384,
        native_audit_sha256=sha(a.audit),gate_receipt_sha256=sha(a.gate),consistency=reports,
        final_sha256=audit['final_sha256'],source_archive_sha256=sha(a.source_archive),
        files_sha256={name:sha(path) for name,path in sorted(entries.items())},
        scope='Independent TT 1.1V 25C 300MHz mother physical implementation; functional final mother netlist with Block/LC RTL and actual private SRAM. LC PM behavioral, no SDF, no joint top-level physical or nine-target qualification.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=out/'mother64-accepted.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        tar.add(out/'manifest.json',arcname='manifest.json')
        for name,path in sorted(entries.items()):tar.add(path,arcname=name,recursive=False)
    assert manifest['files_sha256']=={name:sha(path) for name,path in sorted(entries.items())}
    (out/'archive.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print(json.dumps(dict(archive=str(archive),sha256=sha(archive),files=len(entries),consistency_runs=sum(x['runs'] for x in reports.values()))))

if __name__=='__main__':main()
