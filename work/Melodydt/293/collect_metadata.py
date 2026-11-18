"""Read frozen plan and page timing metadata, without running simulations."""
from pathlib import Path
from hashlib import sha256
import json
from struct import unpack_from

root=Path.home()/'LLMHardware/zenanyan/issue-280-bscc-t6-01'
old=root.parent/'issue-291-prefill-01'
dest=root.parent/'issue-293-200mhz-01'
shared=root/'component-observation/replay-38782605'
def mapped(p,model):
    text=str(p)
    prefix='/public/home/yuzelu/'
    if not text.startswith(prefix):return Path(p)
    relative=text[len(prefix):]
    if model!='qwen3' and relative.startswith('Melodydt/runs/issue-274/'):
        return root/'six-model-energy-01/sourcefs'/relative
    return root/'replay/sourcefs'/relative
def load(p):return json.loads(p.read_bytes())
data={}
for model in ('qwen3','llama','phi','gemma','granite','qwen35','falcon'):
    transfer=load(old/(model+'-transfer.json')) if model!='qwen3' else None
    data[model]={}
    for phase in ('prefill','decode'):
        baseline=Path(transfer['baseline'][phase]) if transfer else shared/('prefill-w4-tile128-pr272-combined' if phase=='prefill' else 'decode-live-w4-tile128-pr272-combined')
        actual=mapped(baseline,model)
        assets=actual/'assets'
        plan=load(assets/'plan.json')
        progress=load(actual/'progress.json')
        pages=progress['pages']
        # Segments include PM installation, absent from the first page start.
        bypage={row['page']:(i,row) for i,row in enumerate(pages)}
        timings=[]
        signatures=[]
        for step,p in enumerate(plan['phases']):
            for layer,lp in enumerate(p['layers']):
                idx,first=bypage[lp[0]['path']]
                _,last=bypage[lp[-1]['path']]
                before=pages[idx-1]['complete_ps']
                timings.append({'step':step,'layer':layer,'elapsed_ps':last['complete_ps']-before})
                signatures.append({'step':step,'layer':layer,'signature':[[x['count'],x['image_bytes']] for x in lp]})
        data[model][phase]={'baseline':str(baseline),'plan_sha256':sha256((assets/'plan.json').read_bytes()).hexdigest(),
            'progress_sha256':sha256((actual/'progress.json').read_bytes()).hexdigest(),
            'layers':plan['layers'],'phases':plan['phases'],'timings':timings,'signatures':signatures,
            'frozen':load(actual/'result.json')}
(dest/'baseline-metadata.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
print('BASELINE_METADATA',list(data))
