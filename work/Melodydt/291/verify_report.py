"""Verify reporting, transfer integrity and component traffic, not long-prefill accuracy."""
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path

root = Path(__file__).resolve().parent
data = json.loads((root/'seven-model-speed-results.json').read_text(encoding='utf-8'))
manifest = {}
for line in (root/'results/server-results.sha256').read_text().splitlines():
    value, name = line.split(None, 1)
    manifest[name.strip().removeprefix('./') if hasattr(str, 'removeprefix') else name.strip()[2:]] = value
beats = {'qwen3':16, 'llama':8, 'phi':24, 'gemma':32, 'granite':8, 'qwen35':32, 'falcon':24}
checks = []
for model, r in data['models'].items():
    p = root/'results'/model/'samples.json'
    assert sha256(p.read_bytes()).hexdigest() == manifest[model+'/samples.json']
    samples = json.loads(p.read_text())
    for row in samples['attention']:
        assert row['ddr']['reads'] == beats[model]*row['context']
        assert row['ddr'].get('writes', 0) == 0
        assert row['ddr']['callbacks'] == row['ddr']['reads']
    for row in samples['recurrent']:
        expected = 34816 if model=='qwen35' else 66688
        assert row['recurrent_write_beats'] == row['ddr']['writes'] == expected
        assert row['ddr']['reads'] + expected == row['ddr']['callbacks']
    pf = json.loads((root/'inputs'/(model+'-prefill.json')).read_text())
    dc = json.loads((root/'inputs'/(model+'-decode.json')).read_text())
    first = Decimal(pf['boundary'][0]['complete_ps'])
    lo = Decimal(pf['boundary'][1]['complete_ps'])-first
    hi = Decimal(dc['boundary'][1]['complete_ps']-dc['retirements'][0]['time_ps'])
    # Direct weighted interpolation and explicit sum, independent of the closed form.
    total = first
    for c in range(2, 513):
        total += (Decimal(514-c)*lo + Decimal(c-2)*hi)/Decimal(512)
    assert abs(total/Decimal(10**12)-Decimal(str(r['estimated_prefill_body_s']))) < Decimal('0.000000001')
    assert r['decode_tok_s']==dc['tok_s'] and r['short_prefill_input_tok_s']==pf['tok_s']
    for name, value in r['verified_input_sha256'].items():
        assert sha256((root/name).read_bytes()).hexdigest()==value
    if r['nonlinear_screen_exceeded']:
        assert r['component_max_deviation_percent'] > 5
    checks.append(dict(model=model, sample_sha_verified=True, traffic_geometry_verified=True,
                       explicit_512_term_sum_verified=True, original_speed_unchanged=True))
assert len(checks)==7
raw=(root/'seven-model-speed-report.html').read_text(encoding='utf-8')
HTMLParser().feed(raw)
assert '已完成模型 7/7' in raw and '16/32-token独立序列验证按用户要求暂缓' in raw
for r in data['models'].values():
    assert r['name'] in raw
    assert format(r['estimated_prefill_to_logits_s'],'.3f') in raw
    assert format(r['decode_tok_s'],'.6f') in raw
assert 'FAILED' in (root/'results/jobs-final.txt').read_text()
assert '38826721|mdt-291ctx|COMPLETED|0:0' in (root/'results/jobs-final.txt').read_text()
result=dict(passed=True, models=checks, attention_samples=330, recurrent_samples=8,
            scope='artifact, arithmetic, immutable baseline, DMA geometry and transfer integrity',
            independent_long_prefill_validation='NOT EXECUTED: deferred by user')
(root/'report-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
