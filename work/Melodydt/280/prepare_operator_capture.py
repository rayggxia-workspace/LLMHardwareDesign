"""Extend verified frozen-run copies with public/special arithmetic observation."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from prepare_arithmetic_capture import prepare, replace

source, bundle, out = map(Path, sys.argv[1:])
prepare(source, bundle, out)
runner = out/'runner'
shutil.copy2(str(bundle/'operator_observation.py'), str(runner/'operator_observation.py'))
replace(runner/'run_frozen_model_energy.py',
        'from arithmetic_observation import ArithmeticObservation as ModelObservation',
        'from operator_observation import OperatorObservation as ModelObservation')
qwen = runner/'qwen3_short.py'
replace(qwen, '                    def product(g, u):\n',
        '                    def product(g, u):\n                        capture_g = tuple(g)\n')
replace(qwen, '                        arith.leaf("g_packet", 40 if gelu else 22, lambda: arith.write(\n',
        '                        self.energy_observation.op_record(\n'
        '                            "gelu" if gelu else "sigmoid" if sigmoid else "scaled_silu" if scaled else "silu",\n'
        '                            site, {"elements":len(g), "gain":gain},\n'
        '                            {"gate":capture_g, "up":u}, {"result":values})\n'
        '                        arith.leaf("g_packet", 40 if gelu else 22, lambda: arith.write(\n')
replace(qwen, '                    lane.edge(lambda: lane.write_span(sram, dest,\n',
        '                    self.energy_observation.op_record("rope", P, {"width":64,"dimension":64},\n'
        '                        {"value":a,"cos":b,"sin":d},{"result":rotated})\n'
        '                    lane.edge(lambda: lane.write_span(sram, dest,\n')
replace(qwen, '                    proj.edge(lambda: proj.write_span(sram, dest,\n',
        '                    self.energy_observation.op_record("rope", P, {"width":width,"dimension":dimension},\n'
        '                        {"value":a,"cos":b,"sin":d},{"result":out+list(a[width:])})\n'
        '                    proj.edge(lambda: proj.write_span(sram, dest,\n')
replace(qwen, 'lambda: unit.write(start+i, [rne(x*gain, 16) for x in values], lambda: step(i+1))',
        'lambda: unit.write(start+i, self.energy_observation.op_output("scale", site, {"elements":4,"gain":gain}, '
        '{"value":values}, [rne(x*gain, 16) for x in values]), lambda: step(i+1))')

router = runner/'granite_short.py'
replace(router, '        p = np.rint(coeff/coeff.sum()*65536).astype(np.int64)\n',
        '        p = np.rint(coeff/coeff.sum()*65536).astype(np.int64)\n'
        '        self.execution.energy_observation.op_record("router", P, {"experts":experts,"top":top},\n'
        '            {"scores_q16":np.frombuffer(raw,dtype="<i4")},{"selected":chosen,"probability_q16":p})\n')
replace(router, '                            unit.edge(lambda: unit.write_span(target, at, data, lambda: tile(index+1)), 96)',
        '                            self.execution.energy_observation.op_record("expert_sum", U, {"elements":128},\n'
        '                                {"old":unpack("<128i",old),"expert":new,"probability_q16":probability},\n'
        '                                {"result":unpack("<128i",data)})\n'
        '                            unit.edge(lambda: unit.write_span(target, at, data, lambda: tile(index+1)), 96)')

hybrid = runner/'hybrid_short.py'
replace(hybrid, '                decay = np.exp(-np.exp(a_log)*delta)\n',
        '                decay = np.exp(-np.exp(a_log)*delta)\n'
        '                self.execution.energy_observation.op_record("recurrent_factors", P, {"gdn":gdn},\n'
        '                    {"a_log":a_log,"delta":delta,"a":a,"dt_bias":dt_bias,"b":b if gdn else None,\n'
        '                     "a_scale":1 if gdn else dp*multiplier}, {"decay":decay,"beta":beta})\n')
replace(hybrid, '                        mixed[first:first+count] = np.sum(window*conv[first:first+count], axis=-1)\n',
        '                        mixed[first:first+count] = np.sum(window*conv[first:first+count], axis=-1)\n'
        '                        self.execution.energy_observation.op_record("conv4", P, {"gdn":gdn,"channels":count},\n'
        '                            {"window":window,"taps":conv[first:first+count]}, {"result":mixed[first:first+count]})\n')
replace(hybrid, '                            block *= decay[head]\n',
        '                            captured_state = block.copy()\n'
        '                            block *= decay[head]\n')
replace(hybrid, '                            # One 32-lane state engine plus local RAM issue slots.\n',
        '                            self.execution.energy_observation.op_record("gdn_state" if gdn else "mamba_state",\n'
        '                                P, {"count":count,"depth":depth},\n'
        '                                {"state":captured_state,"key":k if gdn else key,"query":q if gdn else query,\n'
        '                                 "value":value[idx],"decay":decay[head],"beta":beta[head] if gdn else None,\n'
        '                                 "delta":delta[head],"skip":None if gdn else skip[head]},\n'
        '                                {"state":block,"state_q16":np.frombuffer(q16(block),dtype="<i4").reshape(count,depth),"output":out[idx]})\n'
        '                            # One 32-lane state engine plus local RAM issue slots.\n')
replace(hybrid, '                    def finish():\n',
        '                    def finish():\n                        captured_out = out.copy()\n')
replace(hybrid, '                        self.unit.edge(lambda: self.unit.write_span(self.context, 0, q16(out), done), 4096)',
        '                        self.execution.energy_observation.op_record("recurrent_norm_gate", P, {"gdn":gdn},\n'
        '                            {"value":captured_out,"gamma":gamma,"gate":z,"epsilon":eps}, {"result":out})\n'
        '                        self.unit.edge(lambda: self.unit.write_span(self.context, 0, q16(out), done), 4096)')

# Preserve the native 128-dimensional RoPE imported from the archived provider.
import native_tlm_u
native = Path(native_tlm_u.__file__)
shutil.copy2(str(native), str(runner/'native_tlm_u.py'))
replace(runner/'native_tlm_u.py', '                    operations = [("e_product_packets", 9)]\n',
        '                    self.op_observer.op_record("rope_native", self.op_site,\n'
        '                        {"elements":4,"negative":index<16,"shifts":[cos,neg,neg_align,sin,sin_align,out]},\n'
        '                        {"value":x,"pair":pair,"cos":c,"sin":s},{"result":result})\n'
        '                    operations = [("e_product_packets", 9)]\n')
hashes = {p.name:sha256(p.read_bytes()).hexdigest() for p in runner.iterdir() if p.is_file()}
(out/'instrumented-source.json').write_text(json.dumps(hashes,indent=2)+'\n')
(out/'operator-provenance.json').write_text(json.dumps(dict(
    source=str(source), native_u_source=str(native), native_u_sha256=sha256(native.read_bytes()).hexdigest(),
    note='RMS and native U 128-d RoPE included; observation only, no arithmetic or clock event changes',
    files=hashes),indent=2)+'\n')
print('OPERATOR_CAPTURE_PREPARED', source.name, flush=True)
