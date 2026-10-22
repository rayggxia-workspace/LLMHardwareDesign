import json,urllib.request,pathlib,hashlib,datetime
root=pathlib.Path(__file__).resolve().parent
names=['DeepSeek-V2','DeepSeek-V3','DeepSeek-R1','DeepSeek-R1-Distill-Qwen-7B','DeepSeek-V3.2','DeepSeek-V4-Flash','DeepSeek-V4.1-Flash']
def get(url):
 with urllib.request.urlopen(url,timeout=30) as f:
  d=f.read(2000001)
  if len(d)>2000000:raise ValueError('metadata exceeds 2MB bound')
  return d
records=[]
for name in names:
 try:
  meta=json.loads(get('https://huggingface.co/api/models/deepseek-ai/'+name))
  rev=meta['sha'];url='https://huggingface.co/deepseek-ai/'+name+'/resolve/'+rev+'/config.json'
  data=get(url); path=root/'upstream'/(name+'-config.json');path.write_bytes(data)
  records.append({'model':'deepseek-ai/'+name,'revision':rev,'url':url,'file':'upstream/'+path.name,
    'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'last_modified':meta.get('lastModified')})
  print(name,rev,len(data))
 except Exception as e:records.append({'model':name,'error':str(e)});print(name,type(e).__name__,str(e))
(root/'hf-config-manifest.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'weight_files_downloaded':False,'sources':records},indent=2)+'\n',encoding='utf-8')
