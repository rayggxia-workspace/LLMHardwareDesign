"""Exact activation-supply endpoints for a selected U/P pair."""
import json
from pathlib import Path

RENAMES={
 'copy_generation':'copy_progress_generation',
 'copy_k':'copy_progress_k_elements',
 'copy_session':'copy_progress_session',
 'copy_ticket':'copy_progress_ticket',
 'proof_valid':'a_load_proof_valid',
 'proof_ready':'a_load_proof_ready',
 'proof_shift':'a_load_proof_shift',
 'source_reads_drained':'a_source_reads_drained',
}

def binding(source, target, hardware):
    """Return the selected pair only; this does not choose a pair for Algo1."""
    inventory=hardware['leaf_inventory']
    if 'N' not in inventory[source]['macros'] or 'M' not in inventory[target]['macros']:
        raise ValueError('projection supply needs a U source and P destination')
    ports=json.loads(Path(__file__).with_name('projection_feed_ports.json').read_text())
    signals=[];ties=[]
    for direction,shape,name in ports:
        src=source+'.feed_'+name
        if name=='cp_ack_error':
            ties.append({'sink':src,'value':0,'reason':'selected P COPY SRAM response has no error sideband'})
            continue
        dst=target+'.'+RENAMES.get(name,name)
        width=1 if not shape else int(shape[1:].split(':')[0])+1
        driver,sink=(src,dst) if direction=='output' else (dst,src)
        signals.append({'driver':driver,'sink':sink,'width_bits':width})
    return {'schema':'blockv2-mod-projection-feed-link/1','source':source,'target':target,
            'signals':signals,'constant_inputs':ties,
            'claims':[source+'.LC.service',source+'.S.IO',target+'.LC.service',target+'.S.IO'],
            'completion':'feed finished after all P input-window releases; mother must also wait for P scope completion'}
