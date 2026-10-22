"""Closed-form checks derived independently from the declared schedules.

Imports only the implementation under review to compare its returned counters.
These checks establish its accounting, not physical SRAM access or latency.
"""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path


def ffn_expected(t, h, f, tile, schedule, b=4):
    n = (f + tile - 1) // tile
    w = min(f, tile)
    counts = {"macs": 3*t*h*f, "external_bytes": (2*t*h+3*h*f)*b,
              "engine_transfer_bytes": 3*t*f*b,
              "sram_access_bytes": (6*h*f+14*t*f+(3+4*n)*t*h)*b}
    if schedule == "materialized":
        peaks = {"matrix": (t*h+2*t*f+h*w)*b, "vector": 2*t*f*b}
        peak_total = max(t*h+2*t*f+h*w, 3*t*f)*b
        burst = t*f*b
    else:
        peaks = {"matrix": (2*t*h+2*t*w+h*w)*b, "vector": 2*t*w*b}
        peak_total = (2*t*h+max(2*t*w+h*w, 3*t*w))*b
        burst = t*w*b
    return counts, peaks, peak_total, burst


def attention_expected(q, k, nh, nk, d, qt, kt, schedule, b=4):
    nq, nt = (q+qt-1)//qt, (k+kt-1)//kt
    a, s, c, r = nh*q*d, nh*q*k, nk*nq*k*d, nh*q
    g = nh//nk
    counts = {"macs": 2*nh*q*k*d, "external_bytes": (2*a+2*c)*b}
    if schedule == "materialized":
        counts["engine_transfer_bytes"] = 2*s*b
        counts["sram_access_bytes"] = (4*c+11*s+(3+3*nt)*a+4*r)*b
        extra = g*min(q, qt)*d+min(k, kt)*d
        peaks = {"matrix": (s+extra)*b, "vector": (s+2*r)*b}
        peak_total = max(s+extra, 2*s, s+2*r)*b
        burst = s*b
    else:
        counts["engine_transfer_bytes"] = (2*s+nt*a)*b
        counts["sram_access_bytes"] = (4*c+10*s+(5+7*nt)*a+(3+6*nt)*r)*b
        rr = g*min(q, qt)
        ss, oo, kk = rr*min(k, kt), rr*d, min(k, kt)*d
        peaks = {"matrix": (2*oo+ss+kk)*b,
                 "vector": max(oo+ss+3*rr, 2*oo+3*rr)*b}
        peak_total = max(2*oo+ss+kk+2*rr, 2*oo+2*ss+3*rr,
                         3*oo+ss+kk+3*rr, 4*oo+3*rr)*b
        burst = max(ss, oo)*b
    return counts, peaks, peak_total, burst


def run_checks(ledger_path):
    source = Path(ledger_path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("reviewed_partition_ledger", source)
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    checked = 0

    def compare(actual, expected):
        nonlocal checked
        counts, peaks, total, burst = expected
        for name, value in counts.items():
            assert actual["counts"][name] == value, (name, actual["counts"][name], value)
        assert actual["peak_bank_bytes"] == peaks, (actual["peak_bank_bytes"], peaks)
        assert actual["peak_total_bytes"] == total, (actual["peak_total_bytes"], total)
        assert actual["max_copy_burst_bytes"] == burst
        checked += 1

    for t,h,f,tile,schedule in itertools.product([1,3,8],[5,12],[7,11],[3,6],["materialized","streaming"]):
        compare(ledger.ffn(t,h,f,tile,schedule), ffn_expected(t,h,f,tile,schedule))
    for q,k,qt,kt,schedule in itertools.product([1,3,7],[11,13],[1,4],[2,6],["materialized","streaming"]):
        compare(ledger.attention(q,k,6,2,5,qt,kt,schedule), attention_expected(q,k,6,2,5,qt,kt,schedule))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, "ledger changed during review"
    return {"status":"PASS", "configurations":checked, "ledger_sha256":digest,
            "scope":"Independent formulas versus declared counters/liveness, not physical action counts or PPA."}


if __name__ == "__main__":
    import sys
    print(json.dumps(run_checks(sys.argv[1]), indent=2))
