"""Analytic state-only floors for single-R, layer-ordered decode.

Not a measured full-model run or a claim of achieved operating frequency.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157'
source=R/'docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md'
rows=[]
for name,shape,layers in [('Qwen3.5',[32,128,128],24),('Falcon-H1',[32,128,256],None)]:
    elements=1
    for v in shape:elements*=v
    one=elements*4;roundtrip=one*2;packets=roundtrip//16
    assert roundtrip%16==0
    rows.append(dict(model=name,state_shape=shape,S32_single_version_bytes=one,
        old_new_reserved_bytes=roundtrip,read_write_state_bytes_per_layer_token=roundtrip,
        native128_payload_packets_per_layer_token=packets,
        DDR_data_cycles_floor_at_16B_per_cycle=packets,
        S_staging_service_cycles_floor=packets*2,
        serial_DDR_plus_S_staging_cycles_floor=packets*3,
        recurrent_layers_in_research_config=layers,
        full_decode_state_roundtrip_bytes=roundtrip*layers if layers else None,
        full_decode_serial_data_staging_cycles_floor=packets*3*layers if layers else None))
assert rows[0]['full_decode_state_roundtrip_bytes']==96*1024*1024
assert rows[0]['full_decode_serial_data_staging_cycles_floor']==18874368
assert rows[1]['read_write_state_bytes_per_layer_token']==8*1024*1024
out=dict(scope='Analytic lower bound, not benchmark extrapolation or implemented throughput',
    conditions=['one R with capacity<=2048 S32 words per bank',
    'single-token layer-ordered decode; no full-layer state retained across tokens',
    'S32 persistent state; each scalar old state read once and new state written once',
    'DDR16B/cycle, S narrow128bit, each DDR payload stages through one S write and one S read',
    'serial model with no DMA/compute overlap, as in current Issue157 experiments'],
    exclusions=['coefficient traffic','other R/S tile swaps','burst latency','arithmetic',
        'commit metadata','network packet overhead','projection/attention/norm',
        'long-prefill strip-major reuse or multiple resident R instances'],
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),models=rows)
(D/'STATE_BANDWIDTH_FLOOR.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS: exact state bytes and serial data/staging lower-bound accounting')
