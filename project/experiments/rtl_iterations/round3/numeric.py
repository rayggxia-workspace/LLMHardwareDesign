"""Independent unbounded-integer static W8/S32/S96 service oracle.

No RTL imports, timing assumptions, or simulator execution.
"""
import hashlib
import json
import random

S32_MIN=-(1<<31)
S32_MAX=(1<<31)-1

def rne_s32(value,shift):
 if type(value) is not int or type(shift) is not int or not 0<=shift<=63:
  raise ValueError('invalid exact quantization input')
 q,r=divmod(value,1<<shift)
 if shift and (2*r>1<<shift or (2*r==1<<shift and q&1)):q+=1
 return max(S32_MIN,min(S32_MAX,q)),int(not S32_MIN<=q<=S32_MAX)

def accumulate(a,b,prior=None):
 """b is output-column-major mathematical data, not the hardware layout."""
 if not a or not 1<=len(b)<=8 or any(len(col)!=len(a) for col in b):
  raise ValueError('dot extent mismatch')
 if any(type(x) is not int or not S32_MIN<=x<=S32_MAX for x in a):raise ValueError('A is not S32')
 if any(type(x) is not int or not -128<=x<=127 for col in b for x in col):raise ValueError('B is not signed W8')
 if prior is None:prior=[0]*len(b)
 if len(prior)!=len(b):raise ValueError('prior N mismatch')
 out=[prior[n]+sum(x*y for x,y in zip(a,col)) for n,col in enumerate(b)]
 if any(not -(1<<95)<=v<(1<<95) for v in out):raise ValueError('S96 overflow')
 return out

def input_bytes(a,b):
 """A little-endian S32; B has actual K-major x active-N byte order."""
 accumulate(a,b)
 av=b''.join((x&0xffffffff).to_bytes(4,'little') for x in a)
 bv=bytes(b[n][k]&255 for k in range(len(a)) for n in range(len(b)))
 return av,bv

def physical_read_lines(a_addr,b_addr,k,n):
 if a_addr%64 or not 1<=k<=16 or not 1<=n<=8:raise ValueError('descriptor layout')
 if not 0<=a_addr<=16320 or not 0<=b_addr<=16384-k*n:raise ValueError('input out of S')
 return [a_addr//64]+list(range(b_addr//64,(b_addr+k*n-1)//64+1))

def packet(seed,k,n,kind='random'):
 if not 1<=k<=16 or not 1<=n<=8:raise ValueError('packet shape')
 r=random.Random(seed)
 a=[r.randrange(S32_MIN,S32_MAX+1) for _ in range(k)]
 b=[[r.randrange(-128,128) for _ in range(k)] for _ in range(n)]
 if kind=='edges':
  edges=[S32_MIN,S32_MAX,-65537,-32769,-1,0,1,32767]
  a=[edges[(seed+i)%len(edges)] for i in range(k)]
  b=[[[ -128,127,-1,0,1][(seed+3*j+i)%5] for i in range(k)] for j in range(n)]
 elif kind=='ties':
  a=[0]*k;a[0]=[-7,-5,-3,-1,1,3,5,7][seed%8]
  b=[[1 if i==0 else 0 for i in range(k)] for _ in range(n)]
 elif kind!='random':raise ValueError('unknown fixture kind')
 return a,b

def self_check():
 # Positive/negative nearest-even ties, with even and odd result quotients.
 ties={-7:-4,-5:-2,-3:-2,-1:0,1:0,3:2,5:2,7:4}
 for v,q in ties.items():assert rne_s32(v,1)==(q,0)
 assert rne_s32(1<<80,0)==(S32_MAX,1)
 assert rne_s32(-(1<<80),0)==(S32_MIN,1)
 records=[]
 for k in (1,7,8,15,16):
  for n in (1,3,8):
   for kind in ('random','edges','ties'):
    a,b=packet(247000+k*8+n,k,n,kind);av,bv=input_bytes(a,b)
    # Decode actual layout independently and compare to the mathematical data.
    aa=[int.from_bytes(av[4*i:4*i+4],'little',signed=True) for i in range(k)]
    bb=[[int.from_bytes(bv[i*n+j:i*n+j+1],'little',signed=True) for i in range(k)] for j in range(n)]
    assert aa==a and bb==b
    raw=accumulate(aa,bb)
    cut=max(1,k//2)
    if cut<k:
     first=accumulate(a[:cut],[col[:cut] for col in b])
     assert accumulate(a[cut:],[col[cut:] for col in b],first)==raw
    for shift in (0,1,16,31,63):
     values=[rne_s32(v,shift) for v in raw]
     records.append([k,n,kind,shift,raw,values])
 for k in (1,7,8,15,16):
  for n in (1,3,8):
   assert len(physical_read_lines(0,64,k,n))==1+(k*n+63)//64
   assert len(physical_read_lines(16320,16384-k*n,k,n))<=4
 negatives=0
 for action in (lambda:accumulate([1<<31],[[1]]),lambda:accumulate([1],[[128]]),
                lambda:accumulate([1],[[1]],[(1<<95)-1]),lambda:physical_read_lines(1,64,1,8),
                lambda:physical_read_lines(0,16384,1,1),lambda:rne_s32(1,64)):
  try:action()
  except ValueError:negatives+=1
  else:raise AssertionError('oracle invalid input accepted')
 raw=json.dumps(records,separators=(',',':')).encode()
 return dict(passed=True,cases=len(records),negative_rejections=negatives,
             numeric_sha256=hashlib.sha256(raw).hexdigest(),scope='Python integer/layout oracle only; no RTL or timing proof')

if __name__=='__main__':print(json.dumps(self_check(),indent=2))
