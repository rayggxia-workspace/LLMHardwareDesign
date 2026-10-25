"""Independent semantic admission of every actual exported clock and I/O constraint."""
import re
from decimal import Decimal
from common import need

def audit_sdc(text,ports):
 def names(direction):
  return {n if len(p['bits'])==1 else n+'['+str(p.get('offset',0)+i)+']' for n,p in ports.items()if p['direction']==direction for i in range(len(p['bits']))}
 ins=names('input')-{'clk'};outs=names('output');seen={k:{} for k in('input_delay','output_delay','input_transition','load')};single={};commands=0
 for line in text.splitlines():
  if not line.strip()or line.lstrip().startswith('#'):continue
  commands+=1
  if line=='current_design chain93':need('design'not in single,'one design');single['design']=True;continue
  m=re.fullmatch(r'create_clock -name core -period ([0-9.]+) \[get_ports \{clk\}\]',line)
  if m:need('clock'not in single and Decimal(m[1])==10,'one exact10ns clock');single['clock']=True;continue
  m=re.fullmatch(r'set_clock_transition ([0-9.]+) \[get_clocks \{core\}\]',line)
  if m:need('transition'not in single and Decimal(m[1])==Decimal('.05'),'clock0.05ns');single['transition']=True;continue
  m=re.fullmatch(r'set_clock_uncertainty ([0-9.]+) core',line)
  if m:need('uncertainty'not in single and Decimal(m[1])==0,'clock uncertainty0');single['uncertainty']=True;continue
  m=re.fullmatch(r'set_(input|output)_delay ([0-9.]+) -clock \[get_clocks \{core\}\] -(min|max) -add_delay \[get_ports \{([^}]+)\}\]',line)
  if m:
   kind,value,bound,pin=m.groups();key=kind+'_delay';tag=(pin,bound);need(tag not in seen[key]and Decimal(value)==(Decimal(0)if bound=='min'else Decimal('.1')),'exact independent IO min/max constraint');seen[key][tag]=value;continue
  m=re.fullmatch(r'set_input_transition ([0-9.]+) \[get_ports \{([^}]+)\}\]',line)
  if m:
   value,pin=m.groups();need(pin not in seen['input_transition']and Decimal(value)==Decimal('.05'),'each input fixed slew');seen['input_transition'][pin]=value;continue
  m=re.fullmatch(r'set_load -pin_load ([0-9.]+) \[get_ports \{([^}]+)\}\]',line)
  if m:
   value,pin=m.groups();need(pin not in seen['load']and Decimal(value)==10,'final10fF each output');seen['load'][pin]=value;continue
  raise ValueError('unknown or altered actual SDC statement: '+line)
 need(set(single)=={'design','clock','transition','uncertainty'},'complete actual clock policy')
 need(set(seen['input_delay'])=={(n,b)for n in ins for b in('min','max')},'every nonclock input IO min/max')
 need(set(seen['output_delay'])=={(n,b)for n in outs for b in('min','max')},'every output IO min/max')
 need(set(seen['input_transition'])==ins and set(seen['load'])==outs,'every input slew and output capacitance')
 return {'status':'PASS_EXACT_ACTUAL_EXPORTED_CLOCK_ALL_IO_CONSTRAINTS_NO_EXCEPTIONS','clock_ns':'10','input_output_max_ns':'0.1','input_output_min_ns':'0','slew_ns':'0.05','final_output_load_fF':'10','input_bits_excluding_clock':len(ins),'output_bits':len(outs),'statements_checked':commands,'clock_propagation':'ideal','actual_upstream_driver':'unmodeled'}
