"""Only declared code-domain synthetic inputs, no expected R state/output production."""
import struct
from pathlib import Path

def descriptor(unit=0,epoch=0,position=0,owner=0,profile=1):
 return 0x52393901|(position<<32)|(epoch<<64)|((unit&65535)<<96)|(1<<118)|(profile<<119)|(owner<<123)
def fixtures(out):
 names=['alpha_one','alpha_half_ties','alpha_zero','negative_shift','whole_head_range','dtb_retry_limit','unit_limit','epoch_limit','left_retry_limit','readout_guard','output_guard','invalid_alpha','position_full','position_overflow','invalid_owner','invalid_profile','invalid_unit','invalid_header','signed_min_range']
 meta=[];tsv=[]
 for name in names:
  old=[0]*32768;x=[0]*128;b=[0]*256;c=[0]*256;unit=0;epoch=0;position=0;dt=0;alpha=1<<31;skip=0;owner=0;profile=1;res=0
  if name in ['alpha_one','alpha_half_ties','alpha_zero']:
   pattern=[1,3,-3,-1,-2147483648,2147483647];old=[pattern[i%6]for i in range(32768)];alpha={'alpha_one':1<<31,'alpha_half_ties':1<<30,'alpha_zero':0}[name]
  if name in ['negative_shift','whole_head_range','epoch_limit','left_retry_limit','signed_min_range']:
   x=[1]*128;b=[1]*256;dt=4096;unit=-32
   if name=='negative_shift':unit=-33;alpha=0
   if name in ['whole_head_range','epoch_limit']:old=[3]*32768;old[-1]=2147483647
   if name=='epoch_limit':epoch=0xffffffff
   if name=='left_retry_limit':unit=-127;alpha=0
   if name=='signed_min_range':unit=-34;alpha=0;x=[-2147483648]*128
  if name in ['dtb_retry_limit','unit_limit']:dt=2147483647;b=[2147483647]*256;x=[1]*128;unit=127 if name=='unit_limit'else 0
  if name=='readout_guard':old=[2147483647]*32768;c=[2147483647]*256
  if name=='output_guard':x=[2147483647]*128;skip=2147483647;alpha=0
  if name=='invalid_alpha':alpha=0x80000001
  if name=='position_full':position=72
  if name=='position_overflow':position=0xffffffff
  if name=='invalid_owner':owner=1
  if name=='invalid_profile':profile=2
  if name=='invalid_unit':unit=128
  if name=='invalid_header':res=1
  image=bytearray(1<<20);image[:131072]=struct.pack('<32768i',*old);image[0xa0400:0xa0410]=descriptor(unit,epoch,position,owner,profile).to_bytes(16,'little')
  coeff=struct.pack('<IIIIiIiI',0x52393943,position,0,res,dt,alpha,skip,0)+struct.pack('<640i',*(x+b+c));image[0xb0000:0xb0000+2592]=coeff
  (out/(name+'.bin')).write_bytes(image);run_step=name not in ['position_overflow','invalid_owner','invalid_profile','invalid_unit'];tsv.append(name+' '+str(int(run_step)))
  meta.append({'name':name,'path':name+'.bin','run_step':run_step,'initial_unit':unit,'initial_epoch':epoch,'initial_position':position,'domain':'declared synthetic integer codes, not model quality'})
 (out/'fixtures.tsv').write_text('\n'.join(tsv)+'\n',newline='\n');return meta
