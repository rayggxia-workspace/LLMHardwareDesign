import unittest
from relay import write_all
class ShortPipe(unittest.TestCase):
 def test_every_short_write_preserved(self):
  class Pipe:
   def __init__(self):self.result=bytearray()
   def write(self,view):
    n=min(3,len(view));self.result.extend(view[:n]);return n
  p=Pipe();write_all(p,b'0123456789abcdef');self.assertEqual(bytes(p.result),b'0123456789abcdef')
 def test_closed_pipe_rejected(self):
  class Pipe:
   def write(self,view):return 0
  with self.assertRaises(BrokenPipeError):write_all(Pipe(),b'123')
if __name__=='__main__':unittest.main()
