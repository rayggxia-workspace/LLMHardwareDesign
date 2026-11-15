"""Verify macro pins and elaborated arithmetic sharing, and index unit evidence."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'

def structural(path,engine):
    root=ET.parse(path).getroot()
    modules={m.get('name'):m.get('origName') for m in root.findall('./netlist/module')}
    types={t.get('id'):t for t in root.findall('./netlist/typetable/*')}
    instances=Counter(modules[c.get('submodname')] for c in root.findall('./cells//cell'))
    mod=next(m for m in root.findall('./netlist/module') if m.get('origName')==engine)
    products=Counter()
    for expr in mod.iter():
        if expr.tag not in ('mul','muls') or any(c.tag=='const' for c in expr):continue
        dtype=types[expr.get('dtype_id')]
        products[str(abs(int(dtype.get('left','0'))-int(dtype.get('right','0')))+1)]+=1
    return {'instances':dict(instances),'nonconstant_multiply_expression_widths':dict(products)}

def check():
    baseline=read((ROOT/'rtl/p_services/n_s32_softmax_s128.sv').read_text())
    current=read((ROOT/'rtl/macros/n_s32_mod.sv').read_text())
    assert set(current)-set(baseline)=={'cmd_mode'}
    assert all(current[n]==spec for n,spec in baseline.items())
    assert current['cmd_mode']=={'direction':'input','shape':'[1:0] ','signed':''}
    before=structural(OUT/'n32-original.xml','n_s32_softmax_s128')
    after=structural(OUT/'n32-mod-selected.xml','n_s32_reduction_engine')
    assert before['instances']['block_v2_n_group']==after['instances']['block_v2_n_group']==1
    assert before['nonconstant_multiply_expression_widths']==after['nonconstant_multiply_expression_widths']=={'50':2,'26':2}
    assert 'block_v2_n' not in after['instances']
    assert after['instances']['n_s32_mod']==1
    log=(OUT/'n32-service-114532/run.log').read_text()
    assert 'N32_SERVICE_PASS descriptors=56' in log and 'softmax_macro_cycle_equivalence=14' in log
    files=['rtl/macros/n_s32_mod.sv','rtl/macros/n_s32_reduction_engine.sv',
           'rtl/u0/block_v2_n_group.sv','rtl/p_services/n_s32_softmax_s128.sv',
           'rtl/services/n32_service_controller.sv','compiler/n32_service_descriptor.py',
           'hardware/build_n32_mod.py','hardware/build_n32_service_fixture.py','hardware/rtl_ports.py',
           'evidence/architecture-revision-185/tb_n32_service.sv',
           'evidence/architecture-revision-185/n32_softmax_equivalence.svh',
           'evidence/architecture-revision-185/n32_selected_service_fixture.sv',
           'evidence/architecture-revision-185/make_n32_vectors.py',
           'evidence/architecture-revision-185/n32-service.sbatch']
    snapshots=OUT/'n32-service-114532/validated-source'
    hashes={}
    for file in files:
        source=ROOT/file;dest=snapshots/file;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==source.read_bytes(),'validated source changed'
        else:shutil.copyfile(source,dest)
        hashes[file]=sha256(source.read_bytes()).hexdigest()
    receipt={'schema':'n32-mod-unit-evidence/1','functional_job':114532,'structural_job':114533,
        'source_sha256':hashes,'extra_macro_input_bits':2,'extra_macro_output_bits':0,
        'baseline_arithmetic':before,'mod_arithmetic':after,
        'rms_cases':28,'argmax_cases':14,'softmax_cycle_equivalence_cases':14,
        'descriptor_abort_cases':3,'rejected_descriptors':4,'max_elements':4096,
        'scope':'one macro and its parent service, compiled NSV1 descriptors; not full Qwen or physical/timing acceptance',
        'multiplication_scope':'elaborated expressions; synthesis gate count and area are not measured',
        'full_graph_accepted':False}
    (OUT/'n32-mod-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    p=ROOT/'hardware/n32-mod-revision.json';revision=json.loads(p.read_text())
    revision['status']='RTL unit verified; whole-base integration and graph evaluation pending'
    revision['unit_evidence']={'path':str((OUT/'n32-mod-receipt.json').relative_to(ROOT)),
                              'sha256':sha256((OUT/'n32-mod-receipt.json').read_bytes()).hexdigest()}
    p.write_text(json.dumps(revision,indent=2)+'\n')
    print('N32 mod verified: +2 input bits, +0 output bits; one shared divider; numerical/ABI unit evidence indexed')

if __name__=='__main__':check()
