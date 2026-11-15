"""New RTL base revision; product-specific wires are not part of its fixed base."""
from pathlib import Path
from hashlib import sha256
import json,argparse
from check_pr185_control_admission import validate
from command_pipeline_contract import SERVICE_PIPELINE
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--seed',type=Path,required=True)
parser.add_argument('--assembly-receipt',type=Path,required=True)
parser.add_argument('--control-receipt',type=Path,required=True)
parser.add_argument('--control-xml-directory',type=Path,required=True)
parser.add_argument('--capacity-evidence',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
d=json.loads(args.seed.read_text())
receipt=json.loads(args.assembly_receipt.read_text())
if not receipt.get('elaboration_accepted') or not receipt.get('hidden_macro_negative_case'):
 raise ValueError('full selected assembly/negative-boundary evidence required')
if receipt['functional_instances']!={k:v['master'] for k,v in d['macro_instances'].items()}:
 raise ValueError('assembly functional resource inventory differs')
validate(d,receipt_path=args.control_receipt,xml_directory=args.control_xml_directory)
capacity=json.loads(args.capacity_evidence.read_text())
if capacity.get('schema')!='command-pipeline-capacity/1' or capacity.get('passed') is not True:
 raise ValueError('validated transport capacity evidence required')
for name,h in capacity['source_sha256'].items():
 if sha256(Path(name).read_bytes()).hexdigest()!=h or receipt['source_sha256'].get(name)!=h:
  raise ValueError('capacity evidence is not this elaborated RTL: '+name)
expected_pipeline=SERVICE_PIPELINE
if capacity.get('service_pipeline')!=expected_pipeline or capacity.get('assembly_receipt_sha256')!=sha256(args.assembly_receipt.read_bytes()).hexdigest():
 raise ValueError('pipeline contract not certified for this exact assembly')
for proof in capacity['proofs']:
 if sha256(Path(proof['path']).read_bytes()).hexdigest()!=proof['sha256']:raise ValueError('modified pipeline evidence')
d['service_pipeline']={**expected_pipeline,'capacity_evidence':str(args.capacity_evidence.resolve()),'capacity_evidence_sha256':sha256(args.capacity_evidence.read_bytes()).hexdigest()}
read_slots=capacity['read_slots_per_owner'];write_slots=capacity['write_slots_per_owner']
if type(read_slots) is not int or type(write_slots) is not int or min(read_slots,write_slots)<1:
 raise ValueError('invalid validated capacity')
d['control_admission_evidence']={'receipt':str(args.control_receipt.resolve()),
 'receipt_sha256':sha256(args.control_receipt.read_bytes()).hexdigest(),
 'xml_directory':str(args.control_xml_directory.resolve())}

deps={}
for name,h in receipt['source_sha256'].items():
 p=Path(name)
 if p.name in ('native_selected_nine_assembly.sv','native_nine_control_plane.sv'):continue
 if '/opt/eda/verilator-' in name:continue
 if sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('stale assembly source '+name)
 deps[name]=h
memory=json.loads((ROOT/'hardware/shared-memory-plane.json').read_text())
transport=json.loads((ROOT/'hardware/shared-memory-dma-revision.json').read_text())
for name,h in memory['sources'].items():
 p=Path(name);p=p if p.is_absolute() else ROOT/p
 if sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('stale memory metadata: '+str(p))
transport_source=ROOT/transport['source']
if sha256(transport_source.read_bytes()).hexdigest()!=transport['sha256']:
 raise ValueError('stale DMA metadata')
contract={'contract_revision':d['contract_revision'],'functional_masters':{k:m['master'] for k,m in d['macro_instances'].items()},
 'RTL_sources':deps,'memory_clients':transport['clients'],'transport':transport['transport'],
 'write_payload_bytes':576,'write_slots_per_owner':write_slots,'read_slots_per_owner':read_slots,
 'service_pipeline':expected_pipeline,
 'MC_program_bytes':16384,'LC_program_bytes_each':1024,'MC_service_stall_limit':100000000,
 'control_switch':{'module':'mc_lc_packet128_switch','ENDPOINTS':9},
 'fixed_product_data_edges':[]}
base_hash=sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()
d['base_id']='blockv2-mod-pr185-memory-'+base_hash[:16]
d['base_rtl_contract_sha256']=base_hash;d['base_rtl_contract']=contract
d['mod_revision']='macro-services-command-pipeline-v2'
d['system_resources']['shared_memory']={'implementation':'native_shared_memory_plane','hard_boundary':False,
 'source_sha256':memory['sources'],'clients':transport['clients'],'transport':transport['transport'],
 'native64_source_clients':18,'write_payload_bytes':576,'response_data_bytes':384,
 'nominal_clock_hz':300000000,'aggregate_issue_bytes_per_second':51200000000,
 'source_adapters_outstanding_per_owner':{'read':read_slots,'write':write_slots},
 'global_fault_requires_run_failure':True,'physical_acceptance':False}
for name in ('mother_controller','control_switch'):
 row=d['system_resources'][name]
 if 'odb_sha256' in row:row['reference_odb_sha256']=row.pop('odb_sha256')
 row['physical_acceptance']=False
d['system_resources']['control_switch'].update(master='mc_lc_packet128_switch',parameters={'ENDPOINTS':9},
 implementation='parent_standard_cells')
d['mod_elaboration_accepted']=True
d['mod_elaboration_scope']='same resources instantiated in selected two-phase RTL assembly; not numerical or physical acceptance'
d['assembly_evidence']=str(args.assembly_receipt.resolve())
d['numeric_acceptance']=False;d['physical_acceptance']=False
d['connection_registration_status']='base capacities registered; product endpoints emitted from selected plan'
d['fixed_connections']=[]
d['scope']='PR185 RTL base revision. No product data path is implied by control ownership; selected product assembly is separate.'
target=args.output;target.write_text(json.dumps(d,indent=2)+'\n')
print(d['base_id'])
