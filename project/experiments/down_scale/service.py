"""Finite 1RW bank/packet DAG, including S32 source quantization and scale work.

All arithmetic durations are explicit uncalibrated assumptions. One identical
8-lane wide engine is placed at M or V, never duplicated for the near policy.
The timed boundary includes external source32 DMA, not initial packed W8 load.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import math
from pathlib import Path
import sys
from common import HERE, config, save, provenance, manifest
from numeric import profiles
sys.path.insert(0, str(HERE.parent/'rq_ports'))
from model import Graph, audit_schedule


def packet_bytes(n):
    return sum(64+64*math.ceil(min(1984,n-start)/64) for start in range(0,n,1984))


def build(pr, rows, placement, limb_cycles, batch):
    if rows not in (1,4) or placement not in ('near','shared') or limb_cycles not in (1,2,4) or batch not in (1,4):
        raise ValueError('unsupported service fixture')
    g = Graph(); g.sizes['EXT'] = rows*32768
    ag, wg = pr['ag'], pr['wg']; group = min(ag, wg); ng = 8192//group; elements = rows*16
    if ag not in (128,512,2048,8192) or wg not in (128,8192):raise ValueError('group/tail unsupported')
    a_meta = (8192//ag) * (rows if pr['mode']=='dynamic' else 1)
    w_meta = 16*(8192//wg); meta_bytes = a_meta+w_meta+16+2*elements
    if meta_bytes > 2048: raise ValueError('metadata budget')
    # S0..3 W8=128KiB; S4 raw source32 single-row ring=32KiB;
    # S5 encoded A8 max4 rows=32KiB; S6 metadata; S7 output.
    # M MA(2*4K)+MW(2*8K)+MC6K+PE2K=32K, V VC16K.
    # Endpoints have serialized one-packet TX/RX, 2KiB each; a common bus.
    fixed = g.add('static metadata ready', 0)
    vmeta = g.transfer('S6','V1',w_meta+16+(a_meta if pr['mode']=='static' else 0),'S6','VC',(fixed,),
                       destination_offset=11264,kind='META_STATIC')
    previous = vmeta[-1]; online_meta = []
    for row in range(rows):
        raw = g.transfer('EXT','S4',32768,'EXT','S4',(previous,),source_offset=row*32768,kind='SOURCE32_DMA')
        before = raw[-1]
        # Full-row dynamic cannot retain 32KiB in V16KiB: explicit source reread.
        if pr['mode']=='dynamic' and ag==8192:
            for start in range(0,8192,2048):
                arrive = g.transfer('S4','V0',8192,'S4','VC',(before,),source_offset=start*4,kind='A32_SCAN')
                rd = g.memory('VC',8192,0,arrive,label='online max source read')
                before = g.add('max32 streaming reduction',257,('vector',),(rd,))
            before = g.add('integer CLZ compare scale32',3,('vector',),(before,))
            online_meta.append(g.memory('VC',1,11264+w_meta+16+row,(before,),True,'A exponent store'))
            before = online_meta[-1]
        step = min(ag,2048)
        for start in range(0,8192,step):
            arrive = g.transfer('S4','V0',step*4,'S4','VC',(before,),source_offset=start*4,kind='A32_QUANT_INPUT')
            dep = arrive[-1]
            if pr['mode']=='dynamic' and ag!=8192:
                rd = g.memory('VC',step*4,0,(dep,),label='online group max read')
                mx = g.add('max32 group reduction',math.ceil(step/8)+1,('vector',),(rd,))
                scale = g.add('integer CLZ compare scale32',3,('vector',),(mx,))
                mo = 11264+w_meta+16+row*(8192//ag)+start//ag
                dep = g.memory('VC',1,mo,(scale,),True,'A exponent store'); online_meta.append(dep)
            mr = g.memory('VC',1,11264+w_meta+16+(row*(8192//ag)+start//ag if pr['mode']=='dynamic' else start//ag),
                          (dep,),label='quantizer A exponent read')
            qr = g.memory('VC',step*4,0,(mr,),label='RNE32 source reread')
            quant = g.add('shift32 RNE sat symmetric i8',math.ceil(step/8),('vector',),(qr,))
            store = g.memory('VC',step,8192,(quant,),True,'A8 encoded store')
            export = g.transfer('V0','S5',step,'VC','S5',(store,),source_offset=8192,destination_offset=row*8192+start,kind='A8_PUBLISH')
            before = export[-1]
        previous = before
    if online_meta:
        published = g.transfer('V1','S6',a_meta,'VC','S6',(previous,*online_meta),source_offset=11264+w_meta+16,
                               destination_offset=w_meta+16,kind='META_DYNAMIC')
        previous = published[-1]
    port = 'MC' if placement=='near' else 'VC'; ep = 'M1' if placement=='near' else 'V1'
    moff = 3072 if placement=='near' else 11264
    # Combined ea+ew and min per output: no FP compiler, no free complete table.
    meta = g.transfer('S6',ep,a_meta+w_meta+16,'S6',port,(previous,),destination_offset=moff,kind='META_RQ')
    mr = g.memory(port,a_meta+w_meta+16,moff,meta,label='scale compiler metadata read')
    compile_node = g.add('product exponents and minimum unit',math.ceil(elements*ng/8),('wide',),(mr,))
    e0store = g.memory(port,2*elements,moff+a_meta+w_meta+16,(compile_node,),True,'aligned e0 store')
    ao = 2048 if placement=='near' else 10240
    zero = g.memory(port,elements*8,ao,(e0store,),True,'aligned INT64 zero')
    previous = zero; last_a = [None,None]; last_w = [None,None]; accumulated = zero
    total_wide_updates = 0
    for begin_group in range(0,ng,batch):
        count = min(batch,ng-begin_group)
        group_done = []
        for local_group in range(count):
            gi = begin_group+local_group; matrix = previous
            for start in range(gi*group,(gi+1)*group,128):
                slot = (start//128)%2; wo=start*16
                wd = g.transfer('S'+str(wo//32768),'M0',2048,'S'+str(wo//32768),'MW'+str(slot),
                                (matrix,last_w[slot]),source_offset=wo%32768,kind='W8')
                # A is K-tile packed by row: each row transfer is explicit.
                ad = []
                for row in range(rows):
                    ad += g.transfer('S5','M0',128,'S5','MA'+str(slot),(matrix,last_a[slot]),
                                      source_offset=row*8192+start,destination_offset=row*128,kind='A8')
                matrix = g.add('matrix INT8 K128',128+rows+14,('matrix','MW'+str(slot),'MA'+str(slot)),
                               (matrix,*wd,*ad))
                last_a[slot]=matrix; last_w[slot]=matrix
            write = g.memory('MC',elements*4,local_group*elements*4,(matrix,),True,'INT32 group partial store')
            group_done.append(write); previous = write
        if placement=='shared':
            arrival = g.transfer('M0','V0',count*elements*4,'MC','VC',(*group_done,accumulated),
                                 destination_offset=8192,kind='PARTIAL32')
            po = 8192
        else: arrival = group_done; po = 0
        for local_group in range(count):
            partial = g.memory(port,elements*4,po+local_group*elements*4,(*arrival,accumulated),label='partial read')
            sm = g.memory(port,2*elements,moff+a_meta+w_meta+16,(partial,),label='aligned e0 read')
            # Fetch ea and ew for this group's output coordinates, reusing scale values across lanes.
            operand_meta = g.memory(port,rows+16,moff,(sm,),label='group exponent read')
            old = g.memory(port,elements*8,ao,(operand_meta,),label='wide accumulator read')
            # 32-bit limb implementation: left shift/carry plus 64-bit add;
            # 4 limb slots per lane, varied sensitivity for 1/2/4 cycles each.
            update = g.add('align partial32 and accumulate64',4*limb_cycles*math.ceil(elements/8),('wide',),(old,))
            accumulated = g.memory(port,elements*8,ao,(update,),True,'wide accumulator store')
            total_wide_updates += elements
        previous = accumulated  # one bounded partial batch reused after consumption
    rd = g.memory(port,elements*8,ao,(accumulated,),label='final wide RQ read')
    sm = g.memory(port,2*elements+16,moff+a_meta+w_meta,(rd,),label='final scale read')
    rq = g.add('wide dyadic RNE sat i8',4*limb_cycles*math.ceil(elements/8),('wide',),(sm,))
    oo = 5120 if placement=='near' else 14336
    out = g.memory(port,elements,oo,(rq,),True,'final output8 store')
    if placement=='near':
        result = g.transfer('M0','V0',elements,'MC','VC',(out,),source_offset=oo,destination_offset=14336,kind='ACT8')
    else: result = [out]
    final = g.transfer('V0','S7',elements,'VC','S7',result,source_offset=14336,kind='RESULT8')
    spec = {'profile':pr['name'],'rows':rows,'placement':placement,'limb_cycles':limb_cycles,'batch':batch,
        'effective_group':group,'groups':ng,'A_metadata_bytes':a_meta,'W_metadata_bytes':w_meta,'Y_metadata_bytes':16,
        'aligned_unit_metadata_bytes':2*elements,'metadata_buffer_bytes':meta_bytes,
        'partial_staging_bytes':min(batch,ng)*elements*4,'wide_accumulator_bytes':elements*8,
        'wide_updates':total_wide_updates,'wide_native_multiply':0,
        'source32_bytes':rows*32768,'quantized_A8_bytes':rows*8192,'packed_W8_bytes':131072,
        'source_S32_external_staging_bytes':32768,'M_total_bytes':32768,'V_total_bytes':16384,
        'fifo_bytes_per_endpoint_direction':2048,'boundary':'source32 DMA through RESULT8; packed W8 and static metadata resident before timer',
        'unvalidated':'CLZ/RNE/vector/wide arithmetic and matrix service durations; no RTL or PPA claim',
        'final_node':final[-1]}
    return g, spec


def task(args):
    pr, rows, placement, limb, batch = args; g, spec = build(pr,rows,placement,limb,batch); results=[]
    witness=None
    for policy in config()['service']['policies']:
        scheduled = g.schedule(policy); audit = audit_schedule(g,scheduled)
        results.append({**spec,'policy':policy,'cycles':scheduled['cycles'],'busy':scheduled['busy'],'bytes':dict(g.bytes),'audit':audit})
        if pr['name'] in ('dynamic_none_max_128_8192','dynamic_none_max_8192_8192') and rows==4 and limb==2 and batch==4 and policy=='critical':
            witness={'spec':spec,'nodes':g.nodes,'packets':g.packets,'sizes':g.sizes,'scheduled':scheduled}
    return results,witness


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--workers',type=int,default=2)
    p.add_argument('--development',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    prod=provenance(a.development);cfg=config()['service']; jobs=list(itertools.product(profiles(),cfg['rows'],cfg['placements'],cfg['wide_limb_cycles'],cfg['group_packet_batch']))
    rows=[];witnesses=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for records,witness in pool.map(task,jobs):
            rows.extend(records)
            if witness:witnesses.append(witness)
    a.output.mkdir(parents=True);save(a.output/'service.json',rows)
    for i,w in enumerate(witnesses):save(a.output/f'witness-{i}.json',w)
    pairs=[]
    for pr in profiles():
        for n in cfg['rows']:
            for limb in cfg['wide_limb_cycles']:
                subset=[r for r in rows if r['profile']==pr['name'] and r['rows']==n and r['limb_cycles']==limb]
                best={place:min([r for r in subset if r['placement']==place],key=lambda r:(r['cycles'],r['batch'],r['policy'])) for place in cfg['placements']}
                near,shared=best['near'],best['shared']
                pairs.append({'profile':pr['name'],'rows':n,'limb_cycles':limb,
                    'near_cycles':near['cycles'],'shared_cycles':shared['cycles'],
                    'near_best_batch_policy':[near['batch'],near['policy']],'shared_best_batch_policy':[shared['batch'],shared['policy']],
                    'cycle_reduction_fraction':(shared['cycles']-near['cycles'])/shared['cycles'],
                    'near_wire_bytes':near['bytes']['wire'],'shared_wire_bytes':shared['bytes']['wire']})
    save(a.output/'pairs.json',pairs)
    manifest(a.output,prod,status='PASS',cases=len(rows),paired_envelopes=len(pairs),
             scope='same resources and precision within profile, uncalibrated service cycles; numerical quality screened separately')
    print(json.dumps({'cases':len(rows),'pairs':len(pairs),'witnesses':len(witnesses)}))


if __name__=='__main__':main()
