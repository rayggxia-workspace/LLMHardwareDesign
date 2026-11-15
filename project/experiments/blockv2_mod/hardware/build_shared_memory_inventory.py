"""New RTL base revision; product-specific wires are not part of its fixed base."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'hardware/blockv2-mod-macros.json').read_text())
receipt=json.loads((ROOT/'evidence/architecture-revision-185/selected-nine-assembly-114900/receipt.json').read_text())
deps={}
for name,h in receipt['source_sha256'].items():
 p=Path(name)
 if p.name in ('native_selected_nine_assembly.sv','native_nine_control_plane.sv'):continue
 if '/opt/eda/verilator-' in name:continue
 if sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('stale assembly source '+name)
 deps[name]=h
memory=json.loads((ROOT/'hardware/shared-memory-plane.json').read_text())
transport=json.loads((ROOT/'hardware/shared-memory-dma-revision.json').read_text())
contract={'contract_revision':d['contract_revision'],'functional_masters':{k:m['master'] for k,m in d['macro_instances'].items()},
 'RTL_sources':deps,'memory_clients':transport['clients'],'transport':transport['transport'],
 'write_payload_bytes':576,'write_slots_per_owner':1,'read_slots_per_owner':1,
 'MC_program_bytes':16384,'LC_program_bytes_each':1024,'MC_service_stall_limit':100000000,
 'control_switch':{'module':'mc_lc_packet128_switch','ENDPOINTS':9},
 'fixed_product_data_edges':[]}
base_hash=sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()
d['base_id']='blockv2-mod-pr185-memory-'+base_hash[:16]
d['base_rtl_contract_sha256']=base_hash;d['base_rtl_contract']=contract
d['mod_revision']='macro-services-shared-memory-v1'
d['system_resources']['shared_memory']={'implementation':'native_shared_memory_plane','hard_boundary':False,
 'source_sha256':memory['sources'],'clients':transport['clients'],'transport':transport['transport'],
 'native64_serial_clients':18,'write_payload_bytes':576,'response_data_bytes':384,
 'nominal_clock_hz':300000000,'aggregate_issue_bytes_per_second':51200000000,
 'source_adapters_outstanding_per_owner':{'read':1,'write':1},
 'global_fault_requires_run_failure':True,'physical_acceptance':False}
for name in ('mother_controller','control_switch'):
 row=d['system_resources'][name]
 if 'odb_sha256' in row:row['reference_odb_sha256']=row.pop('odb_sha256')
 row['physical_acceptance']=False
d['system_resources']['control_switch'].update(master='mc_lc_packet128_switch',parameters={'ENDPOINTS':9},
 implementation='parent_standard_cells')
d['mod_elaboration_accepted']=True
d['mod_elaboration_scope']='same resources instantiated in selected two-phase RTL assembly; not numerical or physical acceptance'
d['assembly_evidence']='evidence/architecture-revision-185/selected-nine-assembly-114900/receipt.json'
d['numeric_acceptance']=False;d['physical_acceptance']=False
d['connection_registration_status']='base capacities registered; product endpoints emitted from selected plan'
d['fixed_connections']=[]
d['scope']='PR185 RTL base revision. No product data path is implied by control ownership; selected product assembly is separate.'
target=ROOT/'hardware/blockv2-mod-shared-memory.json';target.write_text(json.dumps(d,indent=2)+'\n')
print(d['base_id'])
