"""Static source and interface checks, not RTL simulation."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 c=json.loads((pathlib.Path(__file__).with_name('contract.json')).read_text(encoding='utf-8'))
 checks=[]
 for rel,proof in c['sources'].items():
  b=(ROOT/rel).read_bytes(); assert hashlib.sha256(b).hexdigest()==proof['sha256'],rel
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==proof['git_blob'],rel
  checks.append('unchanged source '+rel)
 tests={'project/rtl/block_local_s/block_local_s_macro.sv':['CLIENTS*10-1:0','CLIENTS*128-1:0','block_local_s_arbiter','block_feed_s16k'],
 'project/rtl/block_local_s/block_local_s_arbiter.sv':['state==RETURN','rsp_valid[owner]=mem_valid','saved_write<=req_write[selected]'],
 'project/rtl/block_feed_v1/block_feed_s16k.sv':['if(wr)dout<=din','bank0[0:255]','bank3[0:255]'],
 'project/rtl/hbm_feed/hbm_group_dma.sv':['NS*16-1:0','NS*40-1:0','NS*11-1:0','protocol_error<=1','port_phase[s]==2&&s_valid[s]','response_data[k][145:144]!=0']}
 for rel,tokens in tests.items():
  s=(ROOT/rel).read_text(encoding='utf-8'); assert all(t in s for t in tokens),rel
  checks.append('native port and retirement '+rel)
 assert c['profile']['S_bytes']//16==2**c['profile']['address_bits']; checks.append('byte/word capacity')
 assert c['DMA']['tag_bits']==16 and len(c['DMA']['identity'])==7; checks.append('full identity retained separately')
 assert len(c['reset']['members'])==8; checks.append('reset cohort includes external queues')
 assert c['clients']['P']['RX']==2 and c['clients']['N5']['RX']==3; checks.append('profile client ownership')
 print(json.dumps(dict(static_checks=len(checks),passed=len(checks),RTL_simulation=False,checks=checks),ensure_ascii=False))
if __name__=='__main__': main()
