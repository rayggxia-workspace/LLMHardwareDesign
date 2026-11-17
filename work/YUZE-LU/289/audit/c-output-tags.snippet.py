def tag_outputs(m):
 body=group(group(text,'cell','XOR2_X1'),'pin','Z')
 fn=re.search(r'function\s*:\s*"([^"]+)"',body)[1]
 assert re.sub(r'[\s()]','',fn)=='A^B'
 nxt=max(b for w in m['netnames'].values() for b in w['bits'] if isinstance(b,int))+1
 outputs=[(n,list(v['bits'])) for n,v in sorted(m['ports'].items()) if v['direction']=='output']
 for idx,(name,bits) in enumerate(outputs):
  observed=[]
  for k,bit in enumerate(bits):
   tag=f'__proof_tag_{idx}_{k}';cell=tag+'_xor'
   assert tag not in m['ports'] and tag not in m['netnames'] and cell not in m['cells']
   t,z=nxt,nxt+1;nxt+=2
   m['ports'][tag]={'direction':'input','bits':[t]};m['netnames'][tag]={'hide_name':0,'bits':[t],'attributes':{}}
   m['netnames'][cell]={'hide_name':0,'bits':[z],'attributes':{}}
   m['cells'][cell]={'hide_name':0,'type':'XOR2_X1','parameters':{},'attributes':{},'port_directions':{'A':'input','B':'input','Z':'output'},'connections':{'A':[bit],'B':[t],'Z':[z]}}
   observed.append(z)
  m['ports'][name]['bits']=observed;m['netnames'][name]={'hide_name':0,'bits':observed,'attributes':{}}
