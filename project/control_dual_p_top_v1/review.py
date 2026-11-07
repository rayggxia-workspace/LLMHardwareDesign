"""Verify the seven RTL candidate bindings; physical qualification is separate."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
GATES={'integrated_top','fixed_control','private_s','intra_block_data','cross_block_data','cross_block_ack','images_and_data'}
def check(d):
    if d['schema']!='dual-p-rtl-bindings/1' or set(d['bindings'])!=GATES:raise ValueError('binding schema/inventory')
    if [x['block_id'] for x in d['instances']]!=[0,1]:raise ValueError('instances require distinct ordered IDs 0/1')
    if (d['abi'],d['topology'],d['capacity'])!=('0x01790160','0x01790161','0x17630001'):raise ValueError('image profile differs')
    if d['private_s_bytes_each']!=16384 or d['data_bits']!=128 or d['word_address_bits']!=10:raise ValueError('SRAM address contract')
    for name,expected in d['source_sha256'].items():
        p=(ROOT/name).resolve()
        if not p.is_relative_to(ROOT.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            raise ValueError('source drift: '+name)
    top=(HERE/'dual_p_control_top.sv').read_text()
    for i in (0,1):
        if f"p_control_endpoint #(.BLOCK(8'd{i})) p{i}(" not in top:raise ValueError('RTL identity differs')
    if not d['verification']['top_cases']==5 or not d['verification']['control_structure']:raise ValueError('missing candidate verification')
    if d['production_ready'] or not d['remaining_physical_inputs']:raise ValueError('unreviewed production claim')
    return {'candidate_bindings_verified':len(GATES),'ids':[0,1],'candidate_ready':True,'production_ready':False,
            'pending':d['remaining_physical_inputs']}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=HERE/'bindings.json')
    p.add_argument('--require-production',action='store_true');a=p.parse_args()
    try:result=check(json.loads(a.manifest.read_text()))
    except (ValueError,KeyError,OSError) as e:p.exit(1,str(e)+'\n')
    print(json.dumps(result,indent=2))
    return 2 if a.require_production else 0
if __name__=='__main__':raise SystemExit(main())
