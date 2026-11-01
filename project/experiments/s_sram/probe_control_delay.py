"""Diagnostic SPICE-only control-delay candidates; never physical qualification.

Reuses an immutable failed transistor case. Only the delay-chain subcircuit
changes. A candidate requires fresh physical generation, DRC/LVS and complete
characterization before integration. No stimulus or original measure is waived.
"""
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path

NAME = 's_sram_256x128_freepdk45'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--stages', type=int, required=True)
    a = ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    assert a.stages in (31, 49)
    src = a.source.resolve(); out = a.out.resolve(); out.mkdir(exist_ok=False)
    record = dict(qualified=False, passed=False, scope='SPICE-only control-delay diagnosis; no matching candidate GDS', stages=a.stages, inputs={})
    def save():
        (out/'receipt.json').write_text(json.dumps(record, indent=2)+'\n')
    for name in ('delay_stim.sp', 'delay_meas.sp', 'sram.sp', 'trimmed.sp'):
        p = src/name; digest = sha(p); record['inputs'][str(p)] = digest
        text = p.read_text(); new = text.replace(str(src), str(out))
        assert new.replace(str(out), str(src)) == text
        (out/name).write_text(new); assert sha(p) == digest
    p = out/'trimmed.sp'; text = p.read_text(); mod = NAME+'_delay_chain'
    pattern = r'(?ms)^\.SUBCKT '+re.escape(mod)+r'\n.*?^\.ENDS '+re.escape(mod)+r'\n'
    matches = list(re.finditer(pattern, text)); assert len(matches) == 1
    before = matches[0].group(); assert before.count('Xdinv') == 9
    inverter = NAME+'_pinv_22'
    assert set(re.findall(r'^\+ ('+NAME+r'_pinv_\d+)\s*$', before, re.M)) == {inverter}
    lines = ['.SUBCKT '+mod, '+ in out vdd gnd', '* Diagnostic stages: '+str(a.stages)]
    for i in range(a.stages):
        inp = 'in' if i == 0 else 'dout_'+str(i)
        dest = 'out' if i == a.stages-1 else 'dout_'+str(i+1)
        lines += ['Xdinv'+str(i), '+ '+inp+' '+dest+' vdd gnd', '+ '+inverter]
        for j in range(4):
            lines += [f'Xdload_{i}_{j}', f'+ {dest} n_{i}_{j} vdd gnd', '+ '+inverter]
    lines += ['.ENDS '+mod]
    after = '\n'.join(lines)+'\n'; altered = text[:matches[0].start()]+after+text[matches[0].end():]
    assert altered.replace(after, before, 1) == text
    assert len(re.findall(r'(?mi)^\.subckt\b', altered)) == len(re.findall(r'(?mi)^\.ends\b', altered))
    p.write_text(altered)
    record['only_changed_subcircuit'] = mod
    record['baseline_chain_sha256'] = hashlib.sha256(before.encode()).hexdigest()
    record['candidate_chain_sha256'] = hashlib.sha256(after.encode()).hexdigest()
    p = out/'delay_stim.sp'; text = p.read_text(); assert text.lower().count('.end') == 1
    prefix = 'x'+NAME
    assert re.search(r'(?mi)^'+re.escape(prefix)+r'\s', text)
    extra = ''
    for label, node, edge in [('wen_start','w_en0','RISE'),('wen_end','w_en0','FALL'),('wl_start','xbank0.wl_0_63','RISE')]:
        extra += f'.meas tran {label} WHEN v({prefix}.{node})=0.55 {edge}=1 TD=42.5n\n'
    p.write_text(text.replace('.end', extra+'.end'))
    (out/'.spiceinit').write_text('set ngbehavior=hsa\noption klu\nset num_threads=8\n')
    record['outputs_before_simulation'] = {p.name:sha(p) for p in out.iterdir() if p.is_file()}; save()
    cmd = ['/public/home/yuzelu/opt/eda/issue155-sram/bin/ngspice','-b','-o',str(out/'timing.lis'),str(p)]
    start = time.monotonic()
    with (out/'stdout.log').open('w') as f:
        result = subprocess.run(cmd, cwd=out, stdout=f, stderr=subprocess.STDOUT)
    log = (out/'timing.lis').read_text(); values = {}
    for m in re.finditer(r'(?mi)^([a-z0-9_]+)\s*=\s*([-+\d.e]+)', log):
        values[m.group(1)] = float(m.group(2))
    checks = {}
    for key,value in values.items():
        if key.startswith(('v_q_', 'v_qbar_')) and any(x in key for x in ('read_zero','read_one','write_zero','write_one')):
            high = ('_one' in key) != key.startswith('v_qbar_')
            checks[key] = value > 0.99 if high else value < 0.11
    record.update(command=cmd,returncode=result.returncode,seconds=time.monotonic()-start,log_sha256=sha(out/'timing.lis'),measurements=values,bit_checks=checks)
    checks['output_read_one'] = values.get('v_delay_lh0', -1) > 0.99
    checks['output_read_zero'] = 0 <= values.get('v_delay_hl0', 2) < 0.11
    record['passed'] = result.returncode in (0,1) and len(checks)==10 and all(checks.values())
    save(); print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
