"""Network relay only for the two missing representative GQA captures."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import relay
relay.RECEIVER='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/phase6/receive_qwen.py'
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path);p.add_argument('--model',required=True,choices=['qwen25','qwen35']);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 records=[r for r in json.loads(a.plan.read_text())['files']if r['model']==a.model]
 small=[r for r in records if not r['name'].endswith('.safetensors')];large=[r for r in records if r['name'].endswith('.safetensors')]
 results=[relay.one(r)for r in small]
 with ThreadPoolExecutor(max_workers=2)as pool:results.extend(pool.map(relay.one,large))
 a.out.write_text(json.dumps({'status':'PASS','model':a.model,'files':results,'local_weight_files':False},indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
