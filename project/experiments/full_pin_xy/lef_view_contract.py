"""Validate detailed OBS export against the same clean ODB's default abstract.

Reuse Issue7/H1 detailed bloat=0 policy. All pin lines, including PG, and SIZE
must be identical. Every previously occupied layer remains present. This gate
alone is not a complete conductor-coverage, spacing, access or DRC proof.
"""
from collections import Counter
from pathlib import Path
import hashlib,re

def parse(path):
    pins={};obs=Counter();pin=None;inside=False;layer=None;size=None
    for raw in Path(path).read_text().splitlines():
        line=' '.join(raw.split())
        if line.startswith('SIZE '):size=line
        if line.startswith('PIN '):pin=line.split()[1];pins[pin]=[]
        elif pin is not None:
            if line=='END '+pin:pin=None
            else:pins[pin].append(line)
        if line=='OBS':inside=True
        elif inside and line.startswith('LAYER '):layer=line.split()[1]
        elif inside and line.startswith(('RECT ','POLYGON ')):obs[layer]+=1
        elif inside and line=='END':inside=False
    assert size and pins and obs
    return size,pins,dict(obs)

def verify(original,detailed):
    old=parse(original);new=parse(detailed)
    assert old[0]==new[0],'Physical macro size changed'
    assert old[1]==new[1],'Pin geometry/direction/use changed (including PDN)'
    assert set(old[2])<=set(new[2]) and all(new[2][l]>0 for l in old[2]),'An occupied obstruction layer disappeared'
    return {'all_pin_lines_geometry_direction_use_including_PG_identical':True,'size_identical':True,
      'occupied_layers_retained':True,'old_OBS_count_by_layer':old[2],'new_OBS_count_by_layer':new[2],
      'default_bloat_factor':10,'new_bloat_factor':0,'policy_source':'Existing project Issue7 export_detail.py and H1 detailed view workflow; current tool Tcl default verified as 10',
      'scope':'Abstraction granularity gate only; does not prove all conductor coverage, spacing, actual via access or DRC. Native independent DRC and geometry checks are still mandatory.'}
