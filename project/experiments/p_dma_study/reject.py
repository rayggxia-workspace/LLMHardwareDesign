"""Refuse plausible but invalid receipts and source identity drift."""
from copy import deepcopy
from pathlib import Path
import tempfile

from audit import check
import instrument


def rejections(row,trace):
    check(row,trace)
    def change_payload(x):
        # Keep flow/channel/legacy totals self-consistent. Only an independent
        # reconstruction from trace dimensions can reject this false payload.
        x['detail']['channels'][0]['flows']['weight']['logical_read']+=64
        x['detail']['channels'][0]['traffic']['logical_read']+=64
        x['logical_read_bytes']+=64
    mutations={
        'independent_weight_payload':change_payload,
        'legacy_bus_total':lambda x:x.__setitem__('read_bus_bytes',x['read_bus_bytes']+64),
        'private_S_overflow':lambda x:x.__setitem__('P_scratch_peak_bytes',16385),
        'beat_credit_overflow':lambda x:x.__setitem__('max_outstanding_beats',33),
        'consumer_phase_total':lambda x:x['detail']['P'][0].__setitem__('service_subcycles',x['detail']['P'][0]['service_subcycles']+1),
        'shape_flow_total':lambda x:x['detail']['matrix_shapes'][0]['flows']['A'].__setitem__('logical_read',x['detail']['matrix_shapes'][0]['flows']['A']['logical_read']+64),
    }
    passed=[]
    for name,mutation in mutations.items():
        bad=deepcopy(row);mutation(bad)
        try:check(bad,trace)
        except AssertionError:passed.append(name)
        else:raise ValueError('corrupt receipt accepted '+name)
    original=instrument.HERE
    with tempfile.TemporaryDirectory(prefix='pdma-source-negative-') as tmp:
        root=Path(tmp);(root/'upstream').mkdir()
        (root/'upstream/model.cpp').write_bytes((original/'upstream/model.cpp').read_bytes()+b'\n// identity drift\n')
        try:
            instrument.HERE=root
            try:instrument.generate()
            except ValueError as error:
                if str(error)!='frozen model drift':raise
                passed.append('frozen_source_SHA')
            else:raise ValueError('source identity drift accepted')
        finally:instrument.HERE=original
    return dict(passed=True,rejected=passed,scope='source identity and independent receipt checks; not RTL fault injection')
