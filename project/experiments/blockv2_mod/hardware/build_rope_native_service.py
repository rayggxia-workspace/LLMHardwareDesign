"""Lift existing RoPE control to explicit E macro ports, without embedded E."""
from pathlib import Path
from rtl_ports import read,close
ROOT=Path(__file__).resolve().parents[1]
word=ROOT/'rtl/services/rope_s32_service_controller.sv'
ports={n:p for n,p in read(word.read_text()).items() if n.startswith('resource_e_')}
def expose(text):
 start=text.index('(',text.index('module '))
 # Scope has a parameter list; skip it before locating actual ports.
 end=close(text,start)
 if text[end+1:].lstrip().startswith('('):
  start=text.index('(',end+1);end=close(text,start)
 declarations=',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in ports.items())
 return text[:end]+',\n'+declarations+text[end:]
links=','.join('.'+n+'('+n+')' for n in ports)
row=(ROOT/'rtl/p_services/s128_rope_leased_row.sv').read_text()
row=expose(row.replace('module s128_rope_leased_row','module rope_native_row'))
row=row.replace('rope_e32_s128_commit rotate_word','rope_s32_service_controller rotate_word')
needle='.s_rsp_ready(commit_s_take),.s_rsp_error'
assert needle in row
row=row.replace(needle,needle+','+links)
scope=(ROOT/'rtl/p_services/s128_rope_scope.sv').read_text()
scope=expose(scope.replace('module s128_rope_scope','module rope_native_service_controller'))
scope=scope.replace('s128_rope_leased_row row','rope_native_row row')
needle='.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error);'
assert needle in scope
scope=scope.replace(needle,'.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error,'+links+');')
for name,text in [('rope_native_row',row),('rope_native_service_controller',scope)]:
 (ROOT/'rtl/services'/(name+'.sv')).write_text('// Parent controls; E macro supplied by an explicit selected endpoint.\n'+text)
