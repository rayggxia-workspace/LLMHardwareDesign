"""Check an explicit read-hold wrapper against the real synthetic RAM model.

This is behavioral-module equivalence, not equivalence of generated physical
cells, timing qualification, macro compatibility or a replacement in any leaf.
"""
from pathlib import Path
import datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha

DRIVER=Path(__file__).resolve().parent
YOSYS='/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys'
REFERENCE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/mxu-cap20/memory-model/macros/fakeram45_1r1w_64x64.v')


def run(revision):
    generated=ROOT/'native_ram_physical_trial/r01/64x64-1r1w-mask1/generated_behavioral.v'
    assert sha(generated)=='b9803c8c0ffb60a47ff1a0e2623bf7273a99ffd68dceabf5cf1ddce757026176'
    reference=REFERENCE.read_text();assert reference.count('module fakeram45_1r1w_64x64 (')==1
    out=ROOT/'native_ram_sync_wrapper'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [REFERENCE,generated]}
    rec={'scope':'SOURCE_BOUND_BEHAVIORAL_SYNC_WRAPPER_EQUIVALENCE_NOT_PHYSICAL_CORE_OR_COMPLETE_DESIGN',
         'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'full_qualification':False,'original_leaf_or_fake_macro_replaced':False,
         'physical_core_equivalence':'NOT_EXECUTED','GDS_RC_STA_and_original_outline_pin_layer_compatibility':'NOT_VERIFIED',
         'assumptions':['Yosys RTL equivalence semantics; undefined initial memory/output and same-address-write X retained as model dont-care','Binary clock/control/address/data; not exhaustive four-state simulator equivalence','Internal memory word correspondence is explicitly named for inductive state matching'],
         'wrapper_cost_request':'64 registered read-output bits with enable plus per-bit write-enable qualification and collision-X logic; actual mapped area/STA not measured',
         'architecture_contract':'Externally preserves original existing registered read latency/read-enable/hold, ports, capacity and bit mask. No original design altered.'}
    try:
        (out/'gold.v').write_text(reference.replace('module fakeram45_1r1w_64x64 (','module gold ('))
        (out/'actual_generated_behavioral.v').write_bytes(generated.read_bytes())
        wrapper='''module gate (
 input clk, input re_in, input [5:0] r_addr_in,
 input we_in, input [5:0] w_addr_in,
 input [63:0] wd_in, input [63:0] w_mask_in,
 output reg [63:0] rd_out
);
 wire [63:0] asynchronous_q;
 wire [63:0] qualified_write_mask = {64{we_in}} & w_mask_in;
 RAM64x64 core (.clk(clk), .D(wd_in), .Q(asynchronous_q),
 .addr_w(w_addr_in), .addr_r0(r_addr_in), .we(qualified_write_mask));
 always @(posedge clk) begin
  if (re_in) rd_out <= (we_in && r_addr_in == w_addr_in) ? {64{1'bx}} : asynchronous_q;
 end
endmodule
'''
        (out/'proposed_explicit_sync_wrapper.v').write_text(wrapper)
        script=['read_verilog gold.v','hierarchy -check -top gold','proc','memory','opt','design -stash gold',
                'read_verilog actual_generated_behavioral.v proposed_explicit_sync_wrapper.v',
                'hierarchy -check -top gate','proc','flatten','memory','opt']
        script+=['rename \\core.mem['+str(i)+'] \\mem['+str(i)+']' for i in range(64)]
        script+=['design -stash gate','design -copy-from gold -as gold gold','design -copy-from gate -as gate gate',
                 'equiv_make gold gate equiv','hierarchy -check -top equiv','equiv_simple -seq 4','equiv_induct -seq 4','equiv_status -assert']
        (out/'equivalence.ys').write_text('\n'.join(script)+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),IMAGE]
        rec['actual_Yosys_version']=subprocess.check_output(common+[YOSYS,'-V']).decode().strip()
        rec['actual_Yosys_binary_SHA256']=subprocess.check_output(common+['sha256sum',YOSYS]).decode().split()[0]
        with (out/'equivalence.log').open('x') as f:
            rec['native_behavioral_equivalence_returncode']=subprocess.run(common+[YOSYS,'-s','equivalence.ys'],stdout=f,stderr=subprocess.STDOUT).returncode
        log=(out/'equivalence.log').read_text()
        rec['behavioral_wrapper_equivalence_proven_in_stated_scope']=rec['native_behavioral_equivalence_returncode']==0 and 'Equivalence successfully proven!' in log
        if not rec['behavioral_wrapper_equivalence_proven_in_stated_scope']:raise RuntimeError('Behavioral wrapper equivalence not proven; retain native log and script')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec['all_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
