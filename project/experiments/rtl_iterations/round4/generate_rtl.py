"""Issue247 R4 exact patch: optional four EXP lanes for stateless op12 only."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASELINES={
 'block_v2_n.sv':('project/rtl/block_v2/block_v2_n.sv','6f6531e6da3c987ed5dae4f6fb98fbf69f64edee194649110855c99ef9cfee4d'),
 'pu_u_group.sv':('project/rtl/pu_leaf_base/pu_u_group.sv','d6d2ac3fa23ba6debb179ce1f49580e1ddc04d786d32a18b890e40020f6960cd'),
}
UNCHANGED={
 'project/rtl/pu_leaf_base/pu_nexp_shared.sv':'c0a4c727a128fdb06fb4f90f035a618ba400805d936c5290c0a8215f4a036ed5',
 'project/rtl/pu_leaf_base/nexp_batch_adapter.sv':'a975365f97ac8608760d2922e3843433624bd4db775441a8b48e0b2fb08679ca',
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text,old,new):
 if text.count(old)!=1:raise ValueError('R4 exact source anchor failed '+repr(old))
 return text.replace(old,new,1)


def native(text):
 text=once(text,'// Full reductions/normalizations, with explicit S-backed replay and two lanes.',
  '// Stateful operations retain two lanes; stateless op12 optionally uses four EXP lanes.')
 text=once(text,'module block_v2_n #(parameter integer NEXP_DIRECT=0) (',
  'module block_v2_n #(parameter integer NEXP_DIRECT=0, NEXP_DIRECT_LANES=2) (')
 text=once(text,' reg [31:0] square[0:1];reg [15:0] ex[0:1];',
  ''' reg [31:0] square[0:1];reg [15:0] ex[0:1];
 // Only op12 may select a four-element step. Legacy pair arithmetic is intact.
 localparam integer DIRECT_LANES=NEXP_DIRECT!=0?NEXP_DIRECT_LANES:2;
 wire [3:0] accum_step=operation==12&&DIRECT_LANES==4?4'd4:4'd2;
 wire [15:0] direct_extra_exp[0:1];wire [1:0] direct_extra_enabled;''')
 text=once(text,' reg command_ok;',
  ''' // Extra arithmetic exists only in the selected direct configuration. It
 // neither reads nor writes any statistics, factor, replay or top state.
 generate if(DIRECT_LANES==4)begin: direct_exp4
  reg [15:0] extra_exp[0:1];reg [1:0] extra_enabled;
  wire signed [15:0] extra_fetch[0:1];
  for(genvar lane=0;lane<2;lane=lane+1)begin: extra_lane
   assign extra_fetch[lane]=operation==12?$signed(16'(data>>(16*(position+4'd2+4'(lane))))):16'sd0;
   assign direct_extra_exp[lane]=extra_exp[lane];
  end
  assign direct_extra_enabled=extra_enabled;
  always @(posedge clk)begin
   if(reset)begin extra_exp[0]<=0;extra_exp[1]<=0;extra_enabled<=0;end
   else if(phase==CALC&&operation==12)begin
    for(integer lane=0;lane<2;lane=lane+1)begin
     extra_enabled[lane]<=position+4'd2+4'(lane)<n;
     extra_exp[lane]<=exponential($signed({extra_fetch[lane][15],extra_fetch[lane]}));
    end
   end
  end
 end else begin: direct_exp2
  assign direct_extra_exp[0]=16'd0;assign direct_extra_exp[1]=16'd0;
  assign direct_extra_enabled=2'd0;
 end endgenerate

 reg command_ok;''')
 text=once(text,
  "      for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=ex[l];",
  """      for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=ex[l];
      if(operation==12&&DIRECT_LANES==4)
       for(integer l=0;l<2;l=l+1)if(direct_extra_enabled[l])
        result[16*(position+4'd2+4'(l))+:16]<=direct_extra_exp[l];""")
 text=once(text,'     if(position+2>=n)begin phase<=IDLE;rsp_valid<=1;',
  "     if({1'b0,position}+{1'b0,accum_step}>={1'b0,n})begin phase<=IDLE;rsp_valid<=1;")
 text=once(text,
  "       for(integer l=0;l<2;l=l+1)if(enabled[l])rsp_data[16*(position+4'(l))+:16]<=ex[l];",
  """       for(integer l=0;l<2;l=l+1)if(enabled[l])rsp_data[16*(position+4'(l))+:16]<=ex[l];
       // The current result registers update on this same edge, so also
       // override the final two lanes in rsp_data directly.
       if(operation==12&&DIRECT_LANES==4)
        for(integer l=0;l<2;l=l+1)if(direct_extra_enabled[l])
         rsp_data[16*(position+4'd2+4'(l))+:16]<=direct_extra_exp[l];""")
 text=once(text,'     end else begin position<=position+2;phase<=CALC;end\n    end\n    MEAN_START:',
  '     end else begin position<=position+accum_step;phase<=CALC;end\n    end\n    MEAN_START:')
 return once(text,' // Remainder is an internal diagnostic of the shared exact arithmetic unit.',
  ''' // A static configuration error must fail before any command is accepted.
 initial begin
  if(NEXP_DIRECT_LANES!=2&&NEXP_DIRECT_LANES!=4)
   $fatal(1,"NEXP_DIRECT_LANES must be exactly 2 or 4");
 end
 // Remainder is an internal diagnostic of the shared exact arithmetic unit.''')


def group(text):
 text=once(text,'module pu_u_group #(parameter integer NEXP_BATCH=0, NEXP_DIRECT=0) (',
  'module pu_u_group #(parameter integer NEXP_BATCH=0, NEXP_DIRECT=0, NEXP_DIRECT_LANES=2) (')
 text=once(text,'// Exactly one native N, with the same arithmetic resources.',
  '// Exactly one native N; optional direct EXP widening is explicit below.')
 text=once(text,'block_v2_n #(.NEXP_DIRECT((NEXP_BATCH!=0)&&(NEXP_DIRECT!=0))) normalize(',
  '''block_v2_n #(.NEXP_DIRECT((NEXP_BATCH!=0)&&(NEXP_DIRECT!=0)),
        .NEXP_DIRECT_LANES((NEXP_BATCH!=0&&NEXP_DIRECT!=0)?NEXP_DIRECT_LANES:2)) normalize(''')
 return once(text,'endmodule',
  '''    initial begin
        if(NEXP_DIRECT_LANES!=2&&NEXP_DIRECT_LANES!=4)
            $fatal(1,"NEXP_DIRECT_LANES must be exactly 2 or 4");
    end
endmodule''')


def candidates():
 result={}
 for name,(_,expected) in BASELINES.items():
  path=HERE/'baseline'/name
  if sha(path)!=expected:raise ValueError('frozen R2 source drift '+name)
  result[name]=(native if name=='block_v2_n.sv' else group)(path.read_text(encoding='utf-8'))
 return result


def generate(repo,out,integrated=True):
 repo,out=Path(repo).resolve(),Path(out).resolve();texts=candidates()
 for name,text in texts.items():
  path,baseline_hash=BASELINES[name];current=sha(repo/path);candidate_hash=hashlib.sha256(text.encode()).hexdigest()
  if current not in (baseline_hash,candidate_hash):raise ValueError('formal source neither exact R2 nor R4 '+path)
  if integrated and current!=candidate_hash:raise ValueError('R4 candidate not integrated '+path)
  if (HERE/name).read_bytes()!=text.encode():raise ValueError('flat candidate/source patch differ '+name)
 for path,expected in UNCHANGED.items():
  if sha(repo/path)!=expected:raise ValueError('R4 changed shared/adapter source '+path)
 out.mkdir(parents=True,exist_ok=False)
 for name,text in texts.items():(out/name).write_bytes(text.encode())
 report=dict(schema_version=1,baseline='exact R2, run18/run19; R3 remains separate backup',
  generated_sha256={name:sha(out/name) for name in texts},
  baseline_sha256={path:expected for path,expected in BASELINES.values()},
  source_sha256={path:sha(repo/path) for path,_ in BASELINES.values()},unchanged_sha256=UNCHANGED,
  integrated_production=integrated,default_direct_lanes=2,choices=[2,4],ordinary_lanes=2,
  native_N_instances=1,SRAM_expansion=False,physical_qualified=False,
  scope='Optional extra two EXP lanes only for existing stateless op12; original S32 frame and numerical contract unchanged')
 (out/'generation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());return report


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
 parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
 print(json.dumps(generate(args.repo,args.out,not args.prepare)))
