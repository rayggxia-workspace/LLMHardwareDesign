"""Qwen3.5 K32 refinement; fresh validation windows exclude all K128 validation rows."""
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('group32_shared',HERE.parent/'gpu_grouped_repair/run.py')
grouped=importlib.util.module_from_spec(spec);spec.loader.exec_module(grouped)
common=grouped.common
original_tokens=common.dataset_tokens


def tokens(tokenizer,data,cfg):
    inputs=original_tokens(tokenizer,data,cfg)
    previous=inputs['splits']['test']
    rows=common.pq.read_table(data/'test.parquet').column('text').to_pylist()
    excluded=[(s['start_row'],s['end_row_exclusive']) for s in previous]
    eligible=[i for i,t in enumerate(rows) if t.strip() and not any(a<=i<b for a,b in excluded)]
    samples=[]
    for index in common.np.linspace(0,len(eligible)-1,cfg['samples_per_split']+2,dtype=int)[1:-1]:
        for next_index in range(index,len(eligible)):
            start=eligible[next_index];end=start;text='';ids=[]
            while len(ids)<cfg['prediction_tokens']+1 and end<len(rows):
                text+=rows[end]+'\n';end+=1;ids=tokenizer(text,add_special_tokens=False)['input_ids']
            if len(ids)<cfg['prediction_tokens']+1:continue
            if any(start<b and end>a for a,b in excluded):continue
            samples.append({'start_row':start,'end_row_exclusive':end,'token_ids':ids[:cfg['prediction_tokens']+1]})
            excluded.append((start,end));break
        else:raise ValueError('not enough disjoint validation windows')
    assert len(samples)==16
    inputs['splits']['test']=samples
    inputs['excluded_previous_validation_windows']=[{k:s[k] for k in ('start_row','end_row_exclusive')} for s in previous]
    inputs['sampling']=cfg['selection'];return inputs


if __name__=='__main__':
    common.HERE=HERE;common.dataset_tokens=tokens;common.calibrate=grouped.calibration
    common.install=lambda model,mode,factors:grouped.install(model,mode,factors,group_k=32)
    common.main()
