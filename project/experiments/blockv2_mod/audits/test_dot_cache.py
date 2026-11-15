import unittest,struct
from macro_scalar_services import dot
from macro_memory import Data
from e32_dot_descriptor import encode
class Tests(unittest.TestCase):
 def test_independent_streams_and_long_kv(self):
  for k in (32,513,514):
   for columns in (1,4):
    raw=encode(topology=1,k=k,columns=columns,shift=0,result_word=0,a_address=0x1000,b_address=0x10000,b_k_stride=columns*4,b_column_stride=4)
    g=dot(raw);value=None;reads=[];result=None
    while True:
     try:op,*args=g.send(value)
     except StopIteration:break
     value=None
     if op=='read':
      reads.append(args[0]);value=Data.of(struct.pack('<16i',*([1 if args[0]<0x10000 else 2]*16)))
     elif op=='swrite':result=args[1].i32()
     elif op!='cycles':raise AssertionError(op)
    self.assertEqual(result,[k*2]*columns+[0]*(4-columns))
    self.assertEqual(len(reads),(k+15)//16+(k*columns+15)//16)
    self.assertEqual(len(reads),len(set(reads)))
if __name__=='__main__':unittest.main()
