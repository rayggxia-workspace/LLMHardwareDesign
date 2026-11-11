"""Issue247 R2: exact-source patch for optional stateless relative EXP.

Only generation runs locally. Server integrated mode requires actual production
files to equal these four candidates; no RTL timing is asserted here.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINES = {
    'block_v2_n.sv': ('project/rtl/block_v2/block_v2_n.sv',
                      '0ddd23ec62631f64d689678b026a508944928fdb1cedf26ef73900f5e58fd861'),
    'pu_u_group.sv': ('project/rtl/pu_leaf_base/pu_u_group.sv',
                      '9180587e04c7159b45d284715d514e58379b272a760c3ad57b01c7aeff8ee22b'),
    'pu_nexp_shared.sv': ('project/rtl/pu_leaf_base/pu_nexp_shared.sv',
                         '36fb329538243884843817af53d21b5dd38da67cb6d0804b6fbdaf232d04a913'),
    'nexp_batch_adapter.sv': ('project/rtl/pu_leaf_base/nexp_batch_adapter.sv',
                             '600746dc8a0ae59493c1fabe6404cb09bffb926977add091f385d1010f3fc29a'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('unique R2 source anchor failed: ' + repr(old))
    return text.replace(old, new, 1)


def native(text):
    text = once(text, 'module block_v2_n(',
                'module block_v2_n #(parameter integer NEXP_DIRECT=0) (')
    text = once(text, '  else if(cmd_op==11)command_ok=factor_valid;\n  else command_ok=0;',
        '''  else if(cmd_op==11)command_ok=factor_valid;
  // Optional stateless relative EXP. No context is required or modified.
  // Used operands are signed S16; unused complete lanes and aux must be zero.
  else if(cmd_op==12)begin
   command_ok=NEXP_DIRECT!=0&&cmd_param==0&&cmd_aux==0&&cmd_count>0&&cmd_count<=8;
   for(integer i=0;i<8;i=i+1)
    if(i>=cmd_count&&cmd_data[16*i+:16]!=0)command_ok=0;
  end
  else command_ok=0;''')
    text = once(text, '      1,3,5,6:begin', '      1,3,5,6,12:begin')
    text = once(text,
        '      ex[l]<=exponential($signed({fetch[l][15],fetch[l]})-$signed({maximum[15],maximum}));',
        '''      // The existing exponential returns32768 for every nonnegative
      // difference, exactly exp(min(x,0)); op12 never reads maximum.
      ex[l]<=exponential(operation==12?$signed({fetch[l][15],fetch[l]}):
       $signed({fetch[l][15],fetch[l]})-$signed({maximum[15],maximum}));''')
    text = once(text, '''     end else begin
      exp_sum<=exp_sum+{15'd0,pair_exp};exp_count<=exp_count+{15'd0,enabled[0]}+{15'd0,enabled[1]};
      for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=ex[l];
     end''', '''     end else begin
      // Only the legacy exp-accumulate command owns persistent statistics.
      // op12 shares the result lanes without changing exp_count or exp_sum.
      if(operation==3)begin
       exp_sum<=exp_sum+{15'd0,pair_exp};exp_count<=exp_count+{15'd0,enabled[0]}+{15'd0,enabled[1]};
      end
      for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=ex[l];
     end''')
    return once(text, '      if(operation==3)begin\n       rsp_data<=result;',
                '      if(operation==3||operation==12)begin\n       rsp_data<=result;')


def adapter(text):
    text = once(text,
        '''// Candidate local U adapter; native N source is instantiated unchanged.
// f(x)=exp(x-max(x,0)) = exp(min(x,0)-0), for every signed S16 x.
// A transaction owns N until all four responses arrive. The caller must
// arbitrate this adapter with other N services before bottom-base freeze.
module nexp_batch_adapter(''',
        '''// Issue247 R2. Default keeps R1's four-command destructive sequence.
// Optional direct mode issues one stateless native op12 with identical values.
// Both modes own the same single N until the final response is retired.
module nexp_batch_adapter #(parameter integer NEXP_DIRECT=0) (''')
    text = once(text, '''  case(step)
   0:op=0;
   1:begin op=1;ncount=count;end // n explicit zero operands establish max=0/count=n
   2:op=2;
   3:begin op=3;ncount=count;operand=clamped;end
  endcase''', '''  if(NEXP_DIRECT!=0)begin op=12;ncount=count;operand=clamped;end
  else begin
   case(step)
    0:op=0;
    1:begin op=1;ncount=count;end // n explicit zeros establish max=0/count=n
    2:op=2;
    3:begin op=3;ncount=count;operand=clamped;end
   endcase
  end''')
    return once(text, '    if(n_error||step==3)begin',
                '    if(n_error||NEXP_DIRECT!=0||step==3)begin')


def shared(text):
    text = once(text, '''// Issue247 round1. One unchanged native N is shared with ordinary commands.
// op15 is an explicit destructive/clobber ABI. It starts a fresh N context;
// normal multi-command statistics must not be resumed without a new op0.
// No second N, EXP table, reduction lane or private S is instantiated here.
module pu_nexp_shared (''', '''// Issue247 R2. One native N is shared with ordinary commands.
// NEXP_DIRECT=0 preserves R1's destructive/clobber op15 ABI. When enabled,
// op15 uses stateless native op12 and preserves all native session state.
// No second N, EXP table, reduction lane or private S is instantiated here.
module pu_nexp_shared #(parameter integer NEXP_DIRECT=0) (''')
    return once(text, ' nexp_batch_adapter batch(',
                ' nexp_batch_adapter #(.NEXP_DIRECT(NEXP_DIRECT)) batch(')


def group(text):
    text = once(text, 'module pu_u_group #(parameter integer NEXP_BATCH=0) (',
                'module pu_u_group #(parameter integer NEXP_BATCH=0, NEXP_DIRECT=0) (')
    text = once(text, '        pu_nexp_shared dispatch(',
                '        pu_nexp_shared #(.NEXP_DIRECT(NEXP_DIRECT)) dispatch(')
    text = once(text, '// Exactly one native N, unchanged source and arithmetic resources.',
                '// Exactly one native N, with the same arithmetic resources.')
    return once(text, '    block_v2_n normalize(',
        '''    // DIRECT without BATCH does not expose a new ordinary native ABI.
    block_v2_n #(.NEXP_DIRECT((NEXP_BATCH!=0)&&(NEXP_DIRECT!=0))) normalize(''')


def candidates():
    out = {}
    transforms = {'block_v2_n.sv': native, 'pu_u_group.sv': group,
                  'pu_nexp_shared.sv': shared, 'nexp_batch_adapter.sv': adapter}
    for name, (_, expected) in BASELINES.items():
        source = HERE/'baseline'/name
        if sha(source) != expected:
            raise ValueError('frozen R1 baseline drift: ' + name)
        out[name] = transforms[name](source.read_text(encoding='utf-8'))
    return out


def generate(repo, out, integrated=True):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    text = candidates()
    for name, data in text.items():
        path, baseline_hash = BASELINES[name]
        candidate_hash = hashlib.sha256(data.encode()).hexdigest()
        actual_hash = sha(repo/path)
        if actual_hash not in (baseline_hash, candidate_hash):
            raise ValueError('production source is neither exact R1 nor R2: '+path)
        if integrated and actual_hash != candidate_hash:
            raise ValueError('R2 production source is not integrated: '+path)
        if (HERE/name).read_bytes() != data.encode():
            raise ValueError('flat candidate differs from source patch: '+name)
    out.mkdir(parents=True, exist_ok=False)
    for name, data in text.items():
        (out/name).write_bytes(data.encode())
    result = dict(schema_version=1, native_N_instances=1, SRAM_expansion=False,
        integrated_production=integrated, physical_qualified=False,
        baseline_sha256={path: value for _, (path, value) in BASELINES.items()},
        source_sha256={path: sha(repo/path) for _, (path, _) in BASELINES.items()},
        generated_sha256={name: sha(out/name) for name in text},
        scope='Optional single-command stateless relative EXP, same two lanes and LUT')
    (out/'generation.json').write_bytes((json.dumps(result, indent=2)+'\n').encode())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    print(json.dumps(generate(args.repo, args.out, not args.prepare)))
