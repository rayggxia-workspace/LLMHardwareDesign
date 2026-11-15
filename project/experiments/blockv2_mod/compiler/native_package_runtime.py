"""Load generated binary packages; execute with caller-supplied hardware providers.

This adapter does not map operators, synthesize completions, or create resources.
The same scheduler and provider instances are retained across every mother page.
"""
import json, struct
from hashlib import sha256
from pathlib import Path

def load(directory):
    root=Path(directory)
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest['schema']!='native-whole-graph-machine-package/1':
        raise ValueError('unsupported native package')
    payloads={}
    for name,seal in manifest['payloads'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('payload escapes package')
        raw=path.read_bytes()
        if len(raw)!=seal['bytes'] or sha256(raw).hexdigest()!=seal['sha256']:
            raise ValueError('payload seal mismatch: '+name)
        payloads[name]=raw
    from native_local_kernel import validate as validate_local_kernel
    deployment=json.loads(payloads['deployment.json'])
    if deployment['topology']!=manifest['topology']:
        raise ValueError('local deployment topology mismatch')
    validate_local_kernel(payloads['local-kernel.bin'],topology=manifest['topology'],
                          image_id=deployment['local_program_image_id'])
    calls=json.loads(payloads['calls.json'])
    descriptors=payloads['descriptors.bin']
    if len(calls)!=manifest['native_calls'] or len(descriptors)!=128*len(calls):
        raise ValueError('incomplete descriptors')
    from native_tlm_local import descriptor_key
    for i,c in enumerate(calls):
        raw=descriptors[i*128:(i+1)*128]
        if c['index']!=i or c['address']!=manifest['descriptor_base']+128*i:
            raise ValueError('descriptor address sequence')
        if sha256(raw).hexdigest()!=c['sha256']:raise ValueError('call descriptor identity')
        descriptor_key(raw,manifest['topology'])
    pages=[];first=0
    for meta in manifest['mother_pages']:
        raw=payloads[meta['file']]
        u32=lambda offset:struct.unpack_from('<I',raw,offset)[0]
        if (len(raw)<128 or len(raw)>16384 or raw[:8]!=bytes.fromhex('4c42434953413031')
            or struct.unpack_from('<H',raw,8)[0]!=3 or raw[11]!=8
            or u32(12)!=len(raw) or u32(24)!=128
            or u32(64)!=manifest['topology'] or u32(68)!=0x02500002):
            raise ValueError('unsupported mother binary header')
        count=u32(20);entry=u32(16);budget=u32(52)
        if not 0<=entry<count or 128+8*count>len(raw) or budget!=meta['steps']+1:
            raise ValueError('mother binary extent/budget')
        if meta['first_call']!=first or meta['descriptor_base']!=manifest['descriptor_base']+128*first:
            raise ValueError('page descriptor discontinuity')
        extent=calls[first:first+meta['call_count']]
        if len(extent)!=meta['call_count']:raise ValueError('page exceeds descriptor extent')
        pages.append({'instructions':[{'pc':i,'opcode':raw[128+8*i+7],
                       'encoding':raw[128+8*i:136+8*i].hex()} for i in range(count)],
                      'entry_pc':entry,'max_steps':budget,
                      'targets':sum(1<<t for t in {c['target'] for c in extent}),
                      'descriptor_base':meta['descriptor_base'],
                      'descriptor_bytes':128*len(extent)})
        first+=len(extent)
    if first!=len(calls):raise ValueError('pages do not cover package')
    wiring=json.loads(payloads['candidate-wiring.json'])
    if manifest.get('rtl_wiring_complete'):
        from native_product_binding import validate
        validate(wiring,manifest['plan_sha256'],json.loads(payloads['hardware.json']))
    return manifest,payloads,pages

def execute(directory,*,scheduler,providers,timing=None,instruction=None,after_wait=None):
    """Scheduler must read the package's descriptor bytes at descriptor_base."""
    from native_tlm_local import run_page,descriptor_key
    manifest,payloads,pages=load(directory)
    if json.loads(payloads['hardware.json']).get('base_id') and not manifest.get('rtl_wiring_complete'):
        raise ValueError('new-base runtime requires complete same-plan RTL wiring')
    calls=json.loads(payloads['calls.json']);raw=payloads['descriptors.bin']
    needed={(c['target'],*descriptor_key(raw[128*i:128*(i+1)],manifest['topology']))
            for i,c in enumerate(calls)}
    missing=needed-set(providers)
    if missing:raise ValueError('missing hardware-backed TLM providers: '+repr(sorted(missing)))
    for page in pages:
        run_page(page,topology=manifest['topology'],descriptor_base=page['descriptor_base'],
                 descriptor_bytes=page['descriptor_bytes'],scheduler=scheduler,providers=providers,
                 timing=timing,instruction=instruction,after_wait=after_wait)
    return {'pages_executed':len(pages),'native_calls':len(calls),'plan_sha256':manifest['plan_sha256']}
