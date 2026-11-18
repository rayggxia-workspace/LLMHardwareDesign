"""Exhaustive two-state Liberty Boolean truth, with fail-closed token grammar."""
import re,itertools
def evaluate(expression,values):
 tokens=re.findall(r'[A-Za-z_]\w*|[01]|[!&|^()+*\x27]',expression)
 assert ''.join(tokens)==re.sub(r'\s+','',expression),expression
 index=0
 def atom():
  nonlocal index
  t=tokens[index];index+=1
  if t=='!':v=not atom()
  elif t=='(':
   v=expr(0);assert tokens[index]==')';index+=1
  elif t in ('0','1'):v=t=='1'
  else:assert t in values,t;v=values[t]
  while index<len(tokens) and tokens[index]=="'":index+=1;v=not v
  return v
 prec={'|':1,'+':1,'^':2,'&':3,'*':3}
 def expr(level):
  nonlocal index
  left=atom()
  while index<len(tokens) and tokens[index] in prec and prec[tokens[index]]>=level:
   op=tokens[index];index+=1;right=expr(prec[op]+1)
   left=(left or right) if op in ('|','+') else ((left and right) if op in ('&','*') else (left!=right))
  return left
 result=expr(0);assert index==len(tokens);return int(result)
def signature(pins):
 inputs=sorted(x[0] for x in pins if x[1]=='input');assert len(inputs)<=8
 rows=[]
 for bits in itertools.product((0,1),repeat=len(inputs)):
  env=dict(zip(inputs,bits));rows.append([evaluate(fn,env) if fn else None for pin,direction,fn,tri in pins])
 return dict(pin_interface=[[pin,direction,tri] for pin,direction,fn,tri in pins],inputs=inputs,rows=rows)
