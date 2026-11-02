"""Bind new precision weights to the unchanged earlier short-prompt references."""
import argparse,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('weights',type=Path);ap.add_argument('reference',type=Path);ap.add_argument('output',type=Path)
    a=ap.parse_args();ex=json.loads((a.weights/'export_receipt.json').read_text());old=json.loads((a.reference/'export_receipt.json').read_text())
    assert ex['config']==old['config'] and ex['model_path']==old['model_path']
    assert ex['source_files']==old['source_files']
    md=dict(line.split()for line in (a.weights/'metadata.txt').read_text().splitlines())
    md['new_tokens']='3';a.output.mkdir(exist_ok=False)
    for name in ('weights.bin','weights.index','weights.scales'):
        if (a.weights/name).exists():(a.output/name).symlink_to((a.weights/name).resolve())
    for name in ('prompt.txt','reference_hidden.bin','reference_logits.bin'):
        (a.output/name).symlink_to((a.reference/name).resolve())
    (a.output/'metadata.txt').write_text('\n'.join(k+' '+v for k,v in md.items())+'\n')
    for key in ('prompt','prompt_ids','reference_inputs','reference_next_ids','reference_generated','reference_text','reference_seconds'):
        ex[key]=old[key]
    for key in list(ex):
        if key.startswith('sequence_'):ex.pop(key)
    ex.update(reference_reused_from=str(a.reference.resolve()),
              reference_receipt_sha256=sha(a.reference/'export_receipt.json'),
              recheck_weight_parent=str(a.weights.resolve()),recheck_weight_receipt_sha256=sha(a.weights/'export_receipt.json'),
              recheck_tool_sha256=sha(Path(__file__)))
    (a.output/'export_receipt.json').write_text(json.dumps(ex,indent=2,ensure_ascii=False)+'\n')
    print('SHORT_RECHECK_READY',a.output,flush=True)

if __name__=='__main__':main()
