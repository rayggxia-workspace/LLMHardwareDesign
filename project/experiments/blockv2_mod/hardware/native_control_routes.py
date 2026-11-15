"""Descriptor routes implemented by current parent service assemblies.

A control-owner instance is not a hard macro or a product data connection.
"""
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
def profile(inventory,topology,controller_ids):
 if set(controller_ids)!=set(inventory['control_groups']):raise ValueError('nine controller IDs required')
 if len(set(controller_ids.values()))!=len(controller_ids) or any(type(i) is not int or not 0<=i<256 for i in controller_ids.values()):
  raise ValueError('unique native controller identity')
 targets=[]
 for owner,identity in controller_ids.items():
  masters={inventory['macro_instances'][i]['master'] for i in inventory['control_groups'][owner]['macros']}
  if 'm_native_leaf_s32' in masters:
   module='projection_service_cluster'
   signatures=[(0x3152504d,0x02504d03,2,'scope_committed'),(0x314d5347,0x02500002,1,'service_done')]
  elif 'n_s32_mod' in masters:
   module='n32_service_cluster';signatures=[(0x3156534e,0x02504e03,op,'service_done') for op in (1,2,3)]+[(0x32485447,0x02504402,1,'service_done')]
  elif 'e_s32_mac_ap64' in masters:
   module='e32_service_cluster';signatures=[(0x31444d45,0x02504503,1,'service_done'),(3,7,2,'service_done'),(0x31455052,0x02500002,1,'service_done'),(0x31414d52,0x02504504,1,'service_done')]
  else:raise ValueError('no current native service assembly for '+owner)
  signatures.extend([(0x314c5244,0x02500002,1,'destination_commit_ack'),(0x31535744,0x02500002,1,'destination_commit_ack')])
  path=ROOT/'rtl/control'/(module+'.sv')
  targets.append({'group':owner,'id':identity,'rtl_module':module,'hard_boundary':False,
   'rtl_sha256':sha256(path.read_bytes()).hexdigest(),
   'routes':[{'schema':s,'abi':a,'opcode':o,'completions':[c]} for s,a,o,c in signatures]})
 return {'topology_id':topology,'targets':targets,'complete_base_admitted':False,
         'scope':'implemented service assembly routes; missing operator routes are not admitted'}
