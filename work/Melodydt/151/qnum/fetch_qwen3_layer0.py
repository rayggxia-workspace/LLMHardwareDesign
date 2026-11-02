#!/usr/bin/env python3
"""Credential-free, pinned public HF Range extraction. Python >=3.7, no numpy.

Only official metadata, selected layer0 tensors and explicitly legal embedding
rows. HTTP200 for any weight Range is rejected before reading a body. Signed
redirect URLs and unsanitized network exceptions are never printed or saved.
Output directory must not exist. Full model SHA is EXPECTED, never verified by
this partial extractor. Token cases are exact vocabulary pieces, not BPE.
"""
import argparse
import array
import hashlib
import io
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = 'Qwen/Qwen3-0.6B'
REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
MODEL_BYTES = 1503300328
MODEL_SHA256_EXPECTED = 'f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b'
BASE = 'https://huggingface.co'
PREFIX = 'model.layers.0.'
TENSORS = [
    (PREFIX+'input_layernorm.weight', [1024]),
    (PREFIX+'self_attn.q_proj.weight', [2048,1024]),
    (PREFIX+'self_attn.k_proj.weight', [1024,1024]),
    (PREFIX+'self_attn.v_proj.weight', [1024,1024]),
    (PREFIX+'self_attn.o_proj.weight', [1024,2048]),
    (PREFIX+'self_attn.q_norm.weight', [128]),
    (PREFIX+'self_attn.k_norm.weight', [128]),
    (PREFIX+'post_attention_layernorm.weight', [1024]),
    (PREFIX+'mlp.gate_proj.weight', [3072,1024]),
    (PREFIX+'mlp.up_proj.weight', [3072,1024]),
    (PREFIX+'mlp.down_proj.weight', [1024,3072]),
]
EMBED = 'model.embed_tokens.weight'
ASSETS = ['config.json','vocab.json','tokenizer_config.json']
DTYPE_BYTES = {'BOOL':1,'U8':1,'I8':1,'I16':2,'U16':2,'F16':2,'BF16':2,
               'I32':4,'U32':4,'F32':4,'I64':8,'U64':8,'F64':8}


class DataError(Exception):
    pass


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise DataError('duplicate JSON key')
        result[key] = value
    return result


def decode_json(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)


def write_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_range(status, headers, start, end, total, body):
    if status != 206:
        raise DataError('Range requires HTTP206; full-file HTTP200 refused')
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', headers.get('Content-Range','').strip())
    if not match or tuple(map(int, match.groups())) != (start,end,total):
        raise DataError('Content-Range does not match exact requested interval/total')
    length = end-start+1
    if headers.get('Content-Length') != str(length):
        raise DataError('Range Content-Length mismatch or missing')
    if headers.get('Content-Encoding','identity').lower() not in ('identity',''):
        raise DataError('compressed Range body refused')
    raw = body.read(length+1)
    if len(raw) != length:
        raise DataError('Range actual byte length mismatch')
    return raw


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        host = (target.hostname or '').lower()
        if target.scheme != 'https' or not (host == 'huggingface.co' or host.endswith('.huggingface.co') or host.endswith('.hf.co')):
            raise DataError('nonofficial/nonHTTPS redirect refused')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class Client:
    def __init__(self, timeout, retries):
        self.timeout,self.retries = timeout,retries
        self.opener = urllib.request.build_opener(PublicRedirect())
        self.events = []
        self.stage = 'initialization'

    def get(self, public_url, label, limit, byte_range=None):
        self.stage = label
        for attempt in range(self.retries+1):
            headers = {'Accept-Encoding':'identity','User-Agent':'LLMHardwareDesign-Issue151-QwenRange/1'}
            if byte_range:
                headers['Range'] = 'bytes=%d-%d' % byte_range
            try:
                req = urllib.request.Request(public_url,headers=headers)
                with self.opener.open(req,timeout=self.timeout) as response:
                    status = response.getcode()
                    if byte_range:
                        raw = validate_range(status,response.headers,byte_range[0],byte_range[1],MODEL_BYTES,response)
                    else:
                        if status != 200:
                            raise DataError('metadata/asset requires HTTP200')
                        raw = response.read(limit+1)
                        if len(raw)>limit:
                            raise DataError('metadata/asset exceeds declared bounded size')
                    self.events.append({'label':label,'status':status,'bytes':len(raw),
                                        'range':list(byte_range) if byte_range else None,'attempt':attempt})
                    return raw
            except (urllib.error.URLError, OSError) as error:
                self.events.append({'label':label,'attempt':attempt,'error_type':type(error).__name__,
                                    'http_status':getattr(error,'code',None)})
                if attempt == self.retries:
                    raise
                time.sleep(min(2,0.5*(attempt+1)))

    def model_range(self, start, end):
        if not 0<=start<=end<MODEL_BYTES:
            raise DataError('requested model interval outside pinned file')
        # Distinct public cache key; never reuse or log signed CDN URLs.
        query = '?download=true&issue151_range=%d-%d' % (start,end)
        url = BASE+'/'+REPO+'/resolve/'+REVISION+'/model.safetensors'+query
        return self.get(url,'model.safetensors:%d-%d'%(start,end),end-start+1,(start,end))


def parse_header(raw):
    header = decode_json(raw)
    if not isinstance(header,dict):
        raise DataError('safetensors header must be object')
    capacity = MODEL_BYTES-8-len(raw)
    intervals=[]
    for name, item in header.items():
        if name=='__metadata__':
            continue
        if not isinstance(item,dict) or item.get('dtype') not in DTYPE_BYTES:
            raise DataError('unsupported safetensors descriptor')
        shape,offsets = item.get('shape'),item.get('data_offsets')
        if not isinstance(shape,list) or any(type(x) is not int or x<0 for x in shape):
            raise DataError('invalid tensor shape')
        if not isinstance(offsets,list) or len(offsets)!=2 or any(type(x) is not int for x in offsets):
            raise DataError('invalid tensor offsets')
        count=1
        for x in shape:
            count*=x
        begin,end=offsets
        if not 0<=begin<=end<=capacity or end-begin!=count*DTYPE_BYTES[item['dtype']]:
            raise DataError('tensor byte extent/shape outside pinned file')
        intervals.append((begin,end))
    position=0
    for begin,end in sorted(intervals):
        if begin!=position:
            raise DataError('safetensors data gap or overlapping tensors')
        position=end
    if position!=capacity:
        raise DataError('safetensors header does not cover exact pinned data length')
    for name,shape in TENSORS+[(EMBED,[151936,1024])]:
        if name not in header or header[name]['dtype']!='BF16' or header[name]['shape']!=shape:
            raise DataError('required tensor name/dtype/shape mismatch: '+name)
    return header


def bf16_to_f32le(raw):
    if len(raw)%2:
        raise DataError('odd BF16 byte length')
    values=array.array('H')
    if values.itemsize!=2 or array.array('I').itemsize!=4:
        raise DataError('unsupported native array item size')
    values.frombytes(raw)
    if sys.byteorder!='little':
        values.byteswap()
    if any((x&0x7f80)==0x7f80 for x in values):
        raise DataError('nonfinite BF16 training parameter or embedding refused')
    output=array.array('I',(x<<16 for x in values))
    if sys.byteorder!='little':
        output.byteswap()
    return output.tobytes()


def resolve_cases(raw, vocab, tokenizer, vocabulary_rows):
    cases=decode_json(raw)
    cases=cases['token_sequences']
    lookup=dict(vocab)
    for key,token in tokenizer.get('added_tokens_decoder',{}).items():
        number=int(key)
        piece=token['content']
        if piece in lookup and lookup[piece]!=number:
            raise DataError('added token conflicts with vocab mapping')
        lookup[piece]=number
    if any(type(n) is not int or not 0<=n<vocabulary_rows for n in lookup.values()):
        raise DataError('vocabulary ID outside actual embedding rows')
    result=[];identities=set();splits=set()
    for case in cases:
        if case['id'] in identities or case['split'] not in ('cal','eval') or not 1<=len(case['pieces'])<=32:
            raise DataError('duplicate case ID or invalid bounded prefix/split')
        identities.add(case['id']);splits.add(case['split'])
        if any(piece not in lookup for piece in case['pieces']):
            raise DataError('exact vocabulary piece absent; no automatic BPE fallback')
        result.append({'id':case['id'],'split':case['split'],'pieces':case['pieces'],
                       'token_ids':[lookup[p] for p in case['pieces']]})
    if splits!={'cal','eval'} or len({tuple(x['token_ids']) for x in result})!=len(result):
        raise DataError('distinct cal/eval prefixes required')
    return result


def extract_tensor(client,out,name,shape,start,length,chunk_bytes,stem,token_id=None):
    bf=stem+'.bf16le';fp=stem+'.f32le';hbf=hashlib.sha256();hfp=hashlib.sha256()
    with (out/bf).open('xb') as fbf,(out/fp).open('xb') as ffp:
        for offset in range(0,length,chunk_bytes):
            count=min(chunk_bytes,length-offset)
            raw=client.model_range(start+offset,start+offset+count-1)
            converted=bf16_to_f32le(raw)
            fbf.write(raw);ffp.write(converted);hbf.update(raw);hfp.update(converted)
    entry={'name':name,'shape':shape,'source_dtype':'BF16','layout':'native PyTorch contiguous row-major; no transpose',
           'source_range':[start,start+length-1],'bf16le_file':bf,'bf16le_bytes':length,'bf16le_sha256':hbf.hexdigest(),
           'f32le_file':fp,'f32le_bytes':2*length,'f32le_sha256':hfp.hexdigest()}
    if token_id is not None:
        entry['token_id']=token_id
    return entry


def self_check():
    expected=struct.pack('<5f',1.,-1.,0.,-0.,1.5)
    assert bf16_to_f32le(struct.pack('<5H',0x3f80,0xbf80,0,0x8000,0x3fc0))==expected
    okay={'Content-Range':'bytes 10-13/100','Content-Length':'4'}
    assert validate_range(206,okay,10,13,100,io.BytesIO(b'abcd'))==b'abcd'
    bad=[(200,okay,b'abcd'),(206,dict(okay,**{'Content-Range':'bytes 0-3/100'}),b'abcd'),
         (206,dict(okay,**{'Content-Range':'bytes 10-13/101'}),b'abcd'),
         (206,dict(okay,**{'Content-Length':'3'}),b'abcd'),(206,okay,b'abc'),(206,okay,b'abcde'),
         (206,dict(okay,**{'Content-Encoding':'gzip'}),b'abcd')]
    for status,headers,body in bad:
        try:
            validate_range(status,headers,10,13,100,io.BytesIO(body))
        except DataError:
            continue
        raise AssertionError('bad Range fixture accepted')
    for raw in [b'x',struct.pack('<H',0x7f80),struct.pack('<H',0x7fc1)]:
        try:
            bf16_to_f32le(raw)
        except DataError:
            continue
        raise AssertionError('bad BF16 fixture accepted')
    print('PASS_QWEN_RANGE_SELF_CHECK no_network=1 range_negative=7 bf16_negative=3')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--token-cases',type=Path)
    p.add_argument('--source-commit')
    p.add_argument('--timeout',type=float,default=30)
    p.add_argument('--retries',type=int,default=2)
    p.add_argument('--chunk-bytes',type=int,default=1048576)
    p.add_argument('--preflight-only',action='store_true')
    p.add_argument('--self-check',action='store_true')
    a=p.parse_args()
    if a.self_check:
        self_check();return 0
    if not a.output_dir or not re.fullmatch('[0-9a-f]{40}',a.source_commit or ''):
        p.error('fetch requires --output-dir NEW and --source-commit actual40hex')
    if not 0<a.timeout<=120 or not 0<=a.retries<=3 or not 2<=a.chunk_bytes<=4194304 or a.chunk_bytes%2:
        p.error('invalid bounded timeout/retry/even chunk size')
    if not a.preflight_only and not a.token_cases:
        p.error('--token-cases required for actual extraction')
    a.output_dir.mkdir(parents=True,exist_ok=False)
    out=a.output_dir
    client=Client(a.timeout,a.retries)
    receipt={'status':'started','repo':REPO,'revision':REVISION,'source_commit':a.source_commit,
             'source_commit_provenance':'operator supplied actual acquisition-code commit; not automatically Git-verified',
             'extractor_sha256':sha(Path(__file__).read_bytes()),'python':sys.version.split()[0],
             'full_file_sha256_expected':MODEL_SHA256_EXPECTED,'full_file_bytes_expected':MODEL_BYTES,
             'full_file_downloaded':False,'full_file_sha256_verified':False,'credentials_used':False,
             'tensors':[],'embedding_rows':[],'network_events':client.events}
    try:
        api=client.get(BASE+'/api/models/'+REPO+'/revision/'+REVISION+'?blobs=true','official_model_metadata',1048576)
        metadata=decode_json(api)
        if metadata.get('sha')!=REVISION:
            raise DataError('official metadata revision mismatch')
        files={x['rfilename']:x for x in metadata['siblings']}
        model=files['model.safetensors']
        if model['size']!=MODEL_BYTES or model['lfs']['sha256']!=MODEL_SHA256_EXPECTED:
            raise DataError('pinned official file size/LFS identity mismatch')
        (out/'official-api.json').write_bytes(api)
        header8=client.model_range(0,7)
        size=struct.unpack('<Q',header8)[0]
        if not 2<=size<=8388608 or 8+size>=MODEL_BYTES:
            raise DataError('safetensors header size outside bounded limit')
        header_raw=client.model_range(8,7+size)
        header=parse_header(header_raw);data_base=8+size
        (out/'safetensors-header.json').write_bytes(header_raw)
        receipt.update(safetensors_header_bytes=size,safetensors_header_sha256=sha(header_raw),
                       selected_BF16_tensor_bytes=sum(header[n]['data_offsets'][1]-header[n]['data_offsets'][0] for n,_ in TENSORS))
        if a.preflight_only:
            receipt['status']='PREFLIGHT_ONLY_NO_TENSORS'
            return 0
        for filename in ASSETS:
            item=files[filename]
            if item['size']>4194304:
                raise DataError('small official asset exceeds4MiB contract')
            raw=client.get(BASE+'/'+REPO+'/resolve/'+REVISION+'/'+filename,'asset:'+filename,item['size'])
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
            if len(raw)!=item['size'] or blob!=item['blobId']:
                raise DataError('official asset size/Git-blob mismatch: '+filename)
            (out/filename).write_bytes(raw)
            receipt.setdefault('assets',[]).append({'file':filename,'bytes':len(raw),'sha256':sha(raw),'official_git_blob_sha1':blob,'complete_asset_verified':True})
        config=decode_json((out/'config.json').read_bytes())
        if config.get('hidden_size')!=1024 or config.get('intermediate_size')!=3072 or config.get('rms_norm_eps')!=1e-6 or config.get('vocab_size')!=151936:
            raise DataError('official architecture/epsilon/vocab contract changed')
        case_raw=a.token_cases.read_bytes()
        sequences=resolve_cases(case_raw,decode_json((out/'vocab.json').read_bytes()),decode_json((out/'tokenizer_config.json').read_bytes()),151936)
        write_json(out/'token-sequences.json',{'kind':'exact_vocab_pieces_diagnostic_not_BPE_or_representative_calibration','token_sequences':sequences})
        receipt['token_cases_sha256']=sha(case_raw)
        (out/'tensors').mkdir();(out/'embedding_rows').mkdir()
        for name,shape in TENSORS:
            begin,end=header[name]['data_offsets']
            entry=extract_tensor(client,out,name,shape,data_base+begin,end-begin,a.chunk_bytes,'tensors/'+name)
            receipt['tensors'].append(entry)
            print('TENSOR_COMPLETE '+name+' bytes='+str(entry['bf16le_bytes']),flush=True)
        embed_begin=header[EMBED]['data_offsets'][0]
        for token_id in sorted({n for case in sequences for n in case['token_ids']}):
            entry=extract_tensor(client,out,EMBED,[1024],data_base+embed_begin+token_id*2048,2048,a.chunk_bytes,'embedding_rows/token_'+str(token_id),token_id)
            receipt['embedding_rows'].append(entry)
        manifest=dict(receipt)
        manifest.update(status='COMPLETE_SELECTED_TENSORS_AND_ROWS',config_file='config.json',vocab_file='vocab.json',
                        tokenizer_config_file='tokenizer_config.json',token_sequences_file='token-sequences.json',
                        checksum_scope='actual selected raw and converted files; not complete model SHA verification',
                        model_quality_accepted=False,FP32_attention_or_F_input_generated=False)
        write_json(out/'manifest.json',manifest)
        receipt['status']='COMPLETE_SELECTED_TENSORS_AND_ROWS'
        print('PASS_QWEN_RANGE_EXTRACT tensors=11 embedding_rows='+str(len(receipt['embedding_rows']))+' full_file_sha_verified=0')
        return 0
    except Exception as error:
        receipt.update(status='FAILED_CLOSED_PARTIAL_NOT_ADMITTED',failed_stage=client.stage,
                       error_type=type(error).__name__,http_status=getattr(error,'code',None))
        if isinstance(error,DataError):
            receipt['safe_detail']=str(error)
        print('FAIL_QWEN_RANGE_EXTRACT stage='+client.stage+' error_type='+type(error).__name__,file=sys.stderr)
        return 1
    finally:
        write_json(out/'fetch-receipt.json',receipt)


if __name__=='__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError,DataError) as error:
        # No tracebacks/URLError repr: they can contain a signed redirect URL.
        print('FAIL_QWEN_RANGE_SETUP error_type='+type(error).__name__,file=sys.stderr)
        sys.exit(1)
