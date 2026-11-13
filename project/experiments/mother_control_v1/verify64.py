"""Read-only streaming verification of retrieved 64/128-bit program profiles."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as ET

def digest(stream):
    h=hashlib.sha256()
    while block:=stream.read(1024*1024):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('expected_sha256');p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    with a.archive.open('rb') as stream:archive_sha=digest(stream)
    assert archive_sha==a.expected_sha256
    with tarfile.open(a.archive) as tar:
        members={}
        for m in tar:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
            assert m.name not in members;members[m.name]=m
        def raw(name):return tar.extractfile(members[name]).read()
        def document(name):return json.loads(raw(name))
        manifest=document('manifest.json');assert manifest['passed'] and manifest['instruction_bits'] in (64,128)
        bits=manifest['instruction_bits'];version=2 if bits==64 else 1
        expected=manifest['files_sha256'];assert set(members)=={'manifest.json',*expected}
        hashes={}
        for name in sorted(expected):
            hashes[name]=digest(tar.extractfile(members[name]));assert hashes[name]==expected[name],name
        audit=document('native-audit/audit.json');gate=document('gate/result.json')
        assert audit['passed'] and all(audit['checks'].values()) and audit['full_gds_drc_performed'] and audit['full_gds_drc_items']==0
        assert audit['full_deck_sha256']==hashes['native-audit/original-FreePDK45.lydrc']=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
        assert len(ET.fromstring(raw('native-audit/full-drc.lyrdb')).findall('.//items/item'))==0
        assert gate['passed'] and gate['runs']==54 and gate['final_netlist_sha256']==audit['final_sha256']['v']
        assert gate.get('instruction_bits',64)==bits
        if bits==128:
            prior=document('execution-source/qualified64-manifest.json');prior_local=document('execution-source/qualified64-local-verification.json')
            assert prior['passed'] and prior['instruction_bits']==64 and prior_local['passed']
            assert prior['final_sha256']==prior_local['final_sha256']==audit['final_sha256']
            assert hashes['execution-source/qualified64-manifest.json']==gate['prior64_manifest_sha256']==manifest['qualified64_manifest_sha256']
            assert prior_local['archive_sha256']==manifest['qualified64_archive_sha256']
            rtl=document('rtl/result.json');assert rtl['passed'] and not rtl['physical_netlist'] and rtl['instruction_bits']==128 and len(rtl['results'])==54
        assert gate['regression_sha256']==hashes['gate/replay/result.json']
        for extension,sha in audit['final_sha256'].items():assert hashes['physical/6_final.'+extension]==sha
        for name,sha in audit['views_sha256'].items():assert hashes['native-audit/'+name]==sha
        proof=audit['filled_marker_proof']
        if audit['native_route_raw_markers']:
            assert proof['passed'] and len(proof['results'])==audit['native_route_raw_markers']
            assert all(x['same_net_odb_route_fills_entire_marker'] and x['actual_gds_fills_entire_marker'] and x['passed'] for x in proof['results'])
        negative=document('marker-negative/result.json');assert negative['passed'] and negative['gds_sha256']==audit['final_sha256']['gds']
        replay=document('gate/replay/result.json');assert replay['passed'] and replay['physical_netlist'] and replay['instruction_bits']==bits and len(replay['results'])==54
        for row in replay['results']:
            name=f"gate/replay/{row['case']}-{row['reset_mode']}-{row['seed']}.log"
            assert hashes[name]==row['log_sha256'] and b'PASS mother' in raw(name)
        counts={}
        for kind in ('P','U','C','F','J','C-roundtrip','CF-duplex','U-duplex','U-fma-duplex'):
            base='consistency/'+kind+'/';r=document(base+'result.json')
            assert r['passed'] and r['kind']==kind and r['instruction_bits']==bits
            assert r['mother_final_netlist_sha256']==audit['final_sha256']['v']
            assert hashes[base+'result.json']==manifest['consistency'][kind]['receipt_sha256']
            assert r['actual_block_rtl'] and r['actual_local_rtl'] and r['actual_private_s_sram']
            for row in r['results']:
                log=base+f"{row['case']}-{row['reset_mode']}-{row['seed']}.log"
                assert hashes[log]==row['log_sha256'] and b'PASS native' in raw(log)
                for image in ('mother','local0','local1'):
                    word=int(raw(base+row['case']+'/'+image+'.mem').splitlines()[0],16)
                    assert (word>>64)&65535==version
            counts[kind]=len(r['results'])
    receipt=dict(schema=f'mother{bits}-local-package-verification/1',passed=True,instruction_bits=bits,archive=str(a.archive.resolve()),
        archive_sha256=archive_sha,files=len(expected),native_gate_runs=54,consistency_runs=counts,
        final_sha256=audit['final_sha256'],raw_native_route_markers=audit['native_route_raw_markers'],
        full_original_gds_drc_items=0,extracted=False,executed_archive_content=False)
    a.receipt.write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
