"""Address/layout arithmetic contracts, independent of SystemC scheduling."""
import json
import random


def main():
    rng=random.Random(245)
    partitions=0;memory_cases=0;products=0
    # Each output column belongs to exactly one P; K stays ordered and complete.
    for n in range(1,130):
        for group in (8,16):
            owned=[[] for _ in range(2)]
            for column in range(n):owned[(column//group)%2].append(column)
            assert sorted(owned[0]+owned[1])==list(range(n))
            assert not(set(owned[0])&set(owned[1]))
            partitions+=1
    # Exact final dot/RNE is invariant when a prefix is served from its retained
    # byte-identical copy. Negative values and full S32/S16 endpoints are included.
    for k in (1,7,17,127,256,1025,4097,11008):
        a=[rng.randrange(-(1<<31),1<<31) for _ in range(k)]
        b=[rng.randrange(-32768,32768) for _ in range(k)]
        a[0]=-(1<<31);b[0]=-32768
        reference=sum(x*y for x,y in zip(a,b))
        for prefix in (0,min(k,256),min(k,2048)):
            retained={i:a[i] for i in range(prefix)}
            actual=sum((retained[i] if i in retained else a[i])*b[i] for i in range(k))
            assert actual==reference and -(1<<95)<=actual<(1<<95)
            products+=k
    # A 64-byte masked write must preserve every byte not produced by this row.
    # This is an independent byte-memory contract, not a claim that SystemC
    # contains numeric tensor storage or that a hardware write combiner exists.
    for rows in (1,2,9):
        for columns in (1,9,17,32,33):
            size=rows*columns*4
            value=bytes(rng.randrange(256) for _ in range(size))
            memory=bytearray([0xA5]*(size+128))
            for r in range(rows):
                for c in range(0,columns,8):
                    address=64+(r*columns+c)*4
                    data=value[(r*columns+c)*4:(r*columns+min(c+8,columns))*4]
                    while data:
                        take=min(64-address%64,len(data))
                        memory[address:address+take]=data[:take]
                        address+=take;data=data[take:]
            assert memory[:64]==bytes([0xA5]*64) and memory[64+size:]==bytes([0xA5]*64)
            assert memory[64:64+size]==value
            memory_cases+=1
    print(json.dumps(dict(passed=True,column_partition_cases=partitions,
          independent_dot_products=products,masked_byte_memory_cases=memory_cases,
          scope='independent software policy preconditions; not actual tensor arithmetic in the SystemC model')))


if __name__=='__main__':main()
