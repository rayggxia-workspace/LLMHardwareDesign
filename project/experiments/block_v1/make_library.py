"""Expose existing physical resource boundaries without changing arithmetic.

The reconstructed top is a functional comparison harness, not a manufactured
multi-instance product. M8 remains combinational; all accumulation stays in VS.
"""
import argparse
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[3]


def generated(root):
    original = (root/'project/rtl/shared_gdn/shared109.sv').read_text(encoding='utf-8')
    end = original.index(');')
    header, body = original[:end], original[end:]
    external = ''',
 output wire lib_s_req,lib_s_wr,output wire [9:0] lib_s_addr,
 output wire [127:0] lib_s_din,input wire lib_s_ready,lib_s_valid,
 output wire lib_s_take,input wire [127:0] lib_s_dout,
 output wire [63:0] lib_byte_a,lib_byte_b,input wire [127:0] lib_byte_p'''
    storage = 'store82 shared_store(clk,reset,s_request,s_write,s_address,s_input,sr,sv,s_take,so);'
    routed = '''assign lib_s_req=s_request;assign lib_s_wr=s_write;assign lib_s_addr=s_address;
 assign lib_s_din=s_input;assign lib_s_take=s_take;
 assign sr=lib_s_ready;assign sv=lib_s_valid;assign so=lib_s_dout;'''
    multipliers = '''genvar j;generate for(j=0;j<8;j=j+1)begin:SHARED_BYTE
 assign bp[16*j+:16]=$signed(byte_a[8*j+:8])*$signed(byte_b[8*j+:8]);
 end endgenerate'''
    products = 'assign lib_byte_a=byte_a;assign lib_byte_b=byte_b;assign bp=lib_byte_p;'
    assert body.count(storage) == body.count(multipliers) == 1
    body = body.replace(storage, routed).replace(multipliers, products)
    compute = header.replace('module shared109(', 'module block_v1_vs(', 1)+external+body
    # Byte-exact inverse proves the copied controller/arithmetic body has no
    # incidental edits. It does not replace behavioral or physical reception.
    inverse = compute.replace('module block_v1_vs(', 'module shared109(', 1)
    inverse = inverse.replace(external+');', ');', 1).replace(routed, storage).replace(products, multipliers)
    assert inverse == original
    byte = '''// Eight independent signed8 products; no accumulator or hidden state.
module block_v1_m8(input wire [63:0] a,b,output wire [127:0] product);
 genvar i;generate for(i=0;i<8;i=i+1)begin:LANE
 assign product[16*i+:16]=$signed(a[8*i+:8])*$signed(b[8*i+:8]);
 end endgenerate
endmodule
'''
    store = '''// Exactly one existing 1024x128 single-1RW synchronous store.
module block_v1_s16k(input wire clk,reset,req,wr,input wire [9:0] addr,
 input wire [127:0] din,output wire ready,valid,input wire take,output wire [127:0] dout);
 store82 memory(clk,reset,req,wr,addr,din,ready,valid,take,dout);
endmodule
'''
    reassembled = header.replace('module shared109(', 'module block_v1_reassembled(', 1)+''');
 wire lib_s_req,lib_s_wr,lib_s_ready,lib_s_valid,lib_s_take;
 wire [9:0] lib_s_addr;wire [127:0] lib_s_din,lib_s_dout,lib_byte_p;
 wire [63:0] lib_byte_a,lib_byte_b;
 block_v1_vs compute(.*);
 block_v1_m8 multipliers(lib_byte_a,lib_byte_b,lib_byte_p);
 block_v1_s16k storage(clk,reset,lib_s_req,lib_s_wr,lib_s_addr,lib_s_din,
                      lib_s_ready,lib_s_valid,lib_s_take,lib_s_dout);
endmodule
'''
    return {'block_v1_vs.sv': compute, 'block_v1_m8.sv': byte,
            'block_v1_s16k.sv': store, 'block_v1_reassembled.sv': reassembled}, original


def generate(root=BASE, check=False):
    files, original = generated(root); folder = root/'project/rtl/block_library_v1'
    if not check: folder.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, text in files.items():
        path = folder/name
        if check: assert path.read_text(encoding='utf-8') == text, name
        else:
            with path.open('w', encoding='utf-8', newline='\n') as stream: stream.write(text)
        records[name] = hashlib.sha256(text.encode()).hexdigest()
    return dict(passed=True, inverse_shared109_source_exact=True,
        original_sha256=hashlib.sha256(original.encode()).hexdigest(), generated_sha256=records,
        physical_types=['block_v1_m8', 'block_v1_vs', 'block_v1_s16k', 'transaction6k'],
        unchanged_existing_types=['transaction6k'],
        scope='Exact source detachment/reconstruction only; no new independent block simulation, P&R or system qualification')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--check', action='store_true')
    args = parser.parse_args(); print(json.dumps(generate(check=args.check), indent=2))
