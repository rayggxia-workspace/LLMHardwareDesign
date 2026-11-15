"""Validate the executable package/product/base join without claiming physical timing."""
def validate(wiring,plan_sha256,hardware):
 if wiring.get('schema')!='native-product-wiring/1' or wiring.get('rtl_binding_complete') is not True:
  raise ValueError('complete selected RTL product wiring is required')
 if plan_sha256 not in wiring.get('plan_sha256',[]):
  raise ValueError('product wiring targets a different Algo1 plan')
 if wiring.get('base_id')!=hardware.get('base_id') or wiring.get('base_rtl_contract_sha256')!=hardware.get('base_rtl_contract_sha256'):
  raise ValueError('product wiring targets a different base')
 actual={k:m['master'] for k,m in hardware['macro_instances'].items()}
 if wiring.get('functional_instances')!=actual:raise ValueError('product functional macro inventory mismatch')
 sources=wiring.get('RTL_sources',{})
 for name,h in hardware['base_rtl_contract']['RTL_sources'].items():
  if sources.get(name)!=h:raise ValueError('product RTL differs from base source '+name)
 return True
