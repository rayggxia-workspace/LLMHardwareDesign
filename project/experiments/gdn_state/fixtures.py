"""Server-only synthetic full-head boundaries; no producer-derived expected arithmetic."""
import argparse,json
from pathlib import Path
import numpy as np
from inputs import image,sha,put
from contracts import CONTRACT

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--only',nargs='+');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 names=['wide34_both_rescale','format_retry','unit_i8_min','state_upper_gap','state_upper_max','bad_q_min','bad_beta','bad_decay','format_shift_high','retry_limit','unit_terminal','epoch_terminal','position_terminal','version_terminal','mixed_shift_high_low','mixed_shift_low_high'];cases=[]
 if a.only:
  assert len(a.only)==len(set(a.only))and set(a.only)<=set(names),'known unique fixture names'
  names=a.only
 for name in names:
  z={'q':np.ones((1,2,128),dtype=np.int16),'k':np.zeros((1,2,128),dtype=np.int16),'v':np.zeros((1,2,128),dtype=np.int16),'decay':np.full((1,2),1<<31,dtype=np.uint32),'beta':np.full((1,2),32768,dtype=np.uint16),'state_initial':np.zeros((2,128,128),dtype=np.int32),'state_units':np.array([-28,-28],dtype=np.int8),'value_units':np.array([-10,-10],dtype=np.int8)}
  ep=0;pos=10;ver=3;status=0
  if name=='wide34_both_rescale':z['k'][:]=16384;z['v'][:]=32767
  if name=='format_retry':z['state_units'][:]=-43
  if name=='unit_i8_min':z['state_units'][:]=-128;z['value_units'][:]=-128
  if name=='state_upper_gap':z['state_initial'][0,0,0]=0x7fff0001;status=11
  if name=='state_upper_max':z['state_initial'][0,-1,-1]=0x7fffffff;status=11
  if name=='bad_q_min':z['q'][0,1,127]=-32768;status=10
  if name=='bad_beta':z['beta'][0,1]=32769;status=10
  if name=='bad_decay':z['decay'][0,1]=(1<<31)+1;status=10
  if name in('mixed_shift_high_low','mixed_shift_low_high'):
   z['state_units'][:]=[53,-43]if name=='mixed_shift_high_low'else[-43,53]
   z['state_initial'][:]=(np.arange(32768,dtype=np.int32).reshape(2,128,128)-16384)
   z['initial_output']=np.arange(256,dtype=np.int64).reshape(2,128)-128;status=12
  if name=='format_shift_high':z['state_units'][:]=53;status=12
  if name=='retry_limit':z['state_units'][:]=-51;status=6
  if name=='unit_terminal':z['state_initial'][:]=0x7fff0000;z['k'][:]=32767;z['state_units'][:]=127;z['value_units'][:]=127;status=7
  if name=='epoch_terminal':z['state_units'][:]=-43;ep=(1<<32)-1;status=8
  if name=='position_terminal':pos=(1<<64)-1;status=4
  if name=='version_terminal':ver=(1<<64)-1;status=4
  folder=a.out/name;folder.mkdir();encoded=image(z['state_initial'],z['state_units'],z['value_units'],ep,pos,ver,z)
  if'initial_output'in z:encoded[0xa0000:0xa0800]=np.asarray(z['initial_output'],dtype='<i8').tobytes()
  (folder/'image.bin').write_bytes(encoded);np.savez_compressed(folder/'coefficients.npz',**z)
  m={'schema':'gdn104-input-v1','contract':CONTRACT,'status':'VERIFIED_COEFFICIENTS_NOT_RTL','profile':'synthetic-'+name,'position':pos,'version':ver,'epoch':ep,'units':z['state_units'].tolist(),'value_units':z['value_units'].tolist(),'steps':1,'expected_status':status,'source':{'generator_sha256':sha(__file__),'meaning':'full twohead synthetic boundary; not model quality'},'initial_output':'nonzero synthetic checkpoint'if'initial_output'in z else'zero imported','artifacts':[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in folder.iterdir()]};put(folder/'manifest.json',m);cases.append({'name':name,'input_path':str(folder),'manifest_sha256':sha(folder/'manifest.json'),'expected_status':status})
 put(a.out/'fixtures.json',cases);print('PREPARED',len(cases))
if __name__=='__main__':main()
