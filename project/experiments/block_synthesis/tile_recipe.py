"""Measured native tile/scatter recipe, explicitly including memory copies.

This common backend is not a search algorithm or a system calibration. It
uses P/E service acceptance-to-first-completion boundaries, not direct M-only
timings. Whole-service reservation remains conservative; no overlap is free.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from memory import descriptor_ticks


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_qualification(column_directory, row_directory=None):
    """Read frozen evidence; reject changed files, variable/missing profiles.

    The caller supplies accepted source provenance as part of the hardware
    input. This function never silently applies the profile to different RTL.
    """
    result = {'kind':'native-p-e-tile-services-v1','shapes':[], 'P':{},
              'feeder':{},'e_shift_store':None,'provenance':[],'rtl_sha256':{}}
    shapes = set()
    for directory, is_column in ((column_directory,True),(row_directory,False)):
        if directory is None:
            continue
        directory = Path(directory)
        manifest = json.loads((directory/'manifest.json').read_text())
        report = json.loads((directory/'summary.json').read_text())
        kinds = ('native-column-tile-scatter-probe-v2',) if is_column else ('native-row-tile-probe-v2',)
        if manifest['kind'] not in kinds:
            raise ValueError('passive-profile probe required')
        if is_column:
            from column_tile_probe import analyse
        else:
            from row_tile_probe import analyse
        if analyse(directory,directory/'simulate.log',emit=False)!=report:
            raise ValueError('tile report does not reconstruct from raw evidence')
        for name, expected in manifest['sha256'].items():
            if _sha(directory/name)!=expected:
                raise ValueError('tile qualification input changed: '+name)
            if name.startswith('rtl/'):
                old = result['rtl_sha256'].setdefault(name,expected)
                if old!=expected:
                    raise ValueError('tile probes use different RTL')
        if (report['manifest_sha256']!=_sha(directory/'manifest.json') or
            report['log_sha256']!=_sha(directory/'simulate.log') or
            report['passed_cases']!=len(manifest['cases'])):
            raise ValueError('tile qualification receipt differs')
        text = (directory/'simulate.log').read_text()
        marker = 'PASS native column tile and scalar scatter probe' if is_column else 'PASS native row tile probe'
        if text.count(marker)!=1 or 'FATAL' in text:
            raise ValueError('native tile probe did not complete')
        for case in manifest['cases']:
            shapes.add((case['rows'],case.get('columns',1)))
        seen = set()
        for p in report['passive_profiles']:
            if p['min']!=p['max'] or p['min']<1 or p['samples']<1:
                raise ValueError('constant native tile profile required')
            # Inclusive serialized service slots are compatible with the old
            # direct-M driver convention (R1 Execute: 21+1=22). P service
            # already includes its adapter and optional local write/ACK.
            ticks = p['max']+1
            if p['boundary']=='p-command':
                key = {(4,0):'scale',(10,0):'execute',(5,1):'final_store'}.get((p['op'],p['store']))
                if key is None:
                    continue  # Raw accumulator reads are diagnostic only.
                target = result['P'].setdefault(str(p['rows']),{})
            elif p['boundary']=='feeder':
                key = 'reuse_b' if p['reuse_b'] else 'cold'
                target = result['feeder'].setdefault(str(p['rows']),{})
            elif p['boundary']=='e-service':
                if p.get('op')!=8 or p.get('shift')!=15:
                    raise ValueError('unqualified scatter sign operation')
                key = 'e_shift_store';target = result
            else:
                continue
            identity = (p['boundary'],p.get('rows'),key)
            if identity in seen:
                raise ValueError('duplicate native tile profile')
            seen.add(identity)
            if key in target and target[key] is not None and target[key]!=ticks:
                raise ValueError('inconsistent native tile boundary')
            target[key] = ticks
        result['provenance'].append({'manifest_sha256':_sha(directory/'manifest.json'),
                                    'report_sha256':_sha(directory/'summary.json'),
                                    'log_sha256':_sha(directory/'simulate.log')})
    for r,n in shapes:
        if not 1<=r<=8 or not 1<=n<=8:
            raise ValueError('shape outside native ABI')
        if set(result['P'].get(str(r),{}))!={'scale','execute','final_store'} or set(result['feeder'].get(str(r),{}))!={'cold','reuse_b'}:
            raise ValueError('missing measured row service')
    if not shapes or result['e_shift_store'] is None or not (1,1) in shapes:
        raise ValueError('incomplete tile/scatter qualification')
    result['shapes'] = [list(x) for x in sorted(shapes)]
    result['scope'] = 'Exact measured shape points and native P/E/S services; explicit virtual-memory descriptors; no LC/DMA/system calibration.'
    return result


def parts(total, limit):
    if type(total)!=int or type(limit)!=int or total<1 or limit<1:
        raise ValueError('positive integer tile extents required')
    q,r = divmod(total,limit)
    return ([(limit,q)] if q else [])+([(r,1)] if r else [])


def cost(rows,columns,k,row_tile,column_tile,qualification,memory,p_meta,e_meta=None):
    """Finite full-K grid; prepared S32 A and row-shared static S16 B only.

    No macro/S/LC/memory overlap. Intermediate packed/flag records are really
    stored externally and reloaded; no host/local-copy or unbounded register
    cache is assumed. A one-column tail writes canonical S32 directly.
    Caller must separately prove shared B, quantized format, final shift,
    address allocation, hardware binding, static nets and cache eviction.
    """
    if qualification.get('kind')!='native-p-e-tile-services-v1':
        raise ValueError('native tile qualification required')
    # Include transient high/low/sign decomposition terms before correction,
    # rather than bounding only the final mathematical S32 product.
    if type(k)!=int or not 1<=k<=(2**63-1)//((2**31+131072)*2**15):
        raise ValueError('full-K worst-case S64 bound exceeded')
    if not 1<=row_tile<=8 or not 1<=column_tile<=8:
        raise ValueError('native tile dimensions outside ABI')
    shape_set = {tuple(x) for x in qualification['shapes']}
    p_load = descriptor_ticks(memory,1,'load',p_meta['io_write_ticks'])
    p_store = descriptor_ticks(memory,1,'store',p_meta['io_read_ticks'])
    uses_e = min(column_tile,columns)>1
    if uses_e and e_meta is None:
        raise ValueError('multi-column scalar ABI needs actual E service')
    e_load = descriptor_ticks(memory,1,'load',e_meta['io_write_ticks']) if uses_e else 0
    e_store = descriptor_ticks(memory,1,'store',e_meta['io_read_ticks']) if uses_e else 0
    q1 = qualification['P']['1'];f1 = qualification['feeder']['1']
    total = Counter({'ticks':16*p_load,'external_read_words':16,
                     'initial_zero_loads':16})
    p_extent = 0
    for r,rcount in parts(rows,row_tile):
        q = qualification['P'][str(r)];feed = qualification['feeder'][str(r)]
        for n,ncount in parts(columns,column_tile):
            if (r,n) not in shape_set:
                raise ValueError('tile/tail lacks a measured shape point')
            count = rcount*ncount
            loads = k*(3*r+n)
            ticks = loads*p_load+k*(feed['cold']+2*feed['reuse_b']+3*(q['scale']+q['execute']))
            metrics = Counter({'ticks':ticks,'external_read_words':loads,
                'dot_A_loads':3*r*k,'dot_B_loads':n*k,'dot_executes':3*k,
                'dot_scales':3*k,'dot_feeds':3*k,'grid_tiles':1})
            if n==1:
                metrics.update(ticks=r*(q['final_store']+p_store),
                               external_write_words=r,canonical_outputs=r,final_reads=r)
            else:
                packed = r*((n+3)//4);outputs = r*n
                metrics.update(ticks=packed*(q['final_store']+p_store+e_load+
                    qualification['e_shift_store']+e_store)+outputs*(
                    3*(2*p_load+f1['cold']+q1['scale']+q1['execute'])+q1['final_store']+p_store),
                    external_read_words=packed+6*outputs,
                    external_write_words=2*packed+outputs,
                    scatter_input_loads=3*outputs,scatter_basis_loads=3*outputs,
                    scatter_executes=3*outputs,scatter_scales=3*outputs,scatter_feeds=3*outputs,
                    packed_outputs=packed,flag_outputs=packed,e_sign_services=packed,
                    canonical_outputs=outputs,final_reads=packed+outputs)
            total.update({key:value*count for key,value in metrics.items()})
            # Keep the actually exercised native destination addresses. Do not
            # shrink the allocation by inventing a relocation/copy service.
            p_extent = max(p_extent,512+(r-1)*8+n)
    result = dict(total)
    result.update(P_words=p_extent,E_words=2 if uses_e else 0,
                  external_words=total['external_read_words']+total['external_write_words'],
                  temporary_external_words=(2*min(rows,row_tile)*((min(columns,column_tile)+3)//4)) if uses_e else 0,
                  context='full K until all native final writes/ACKs; scatter reuses M only afterwards',
                  reservation='all declared M/E/S/LC/channel resources through final external STORE ACK',
                  cost_model='native-p-e-tile-stream-v1')
    return result
