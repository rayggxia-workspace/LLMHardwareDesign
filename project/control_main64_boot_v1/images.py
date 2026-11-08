"""Hand-authored R8.2 programs; R8.3 compiler integration remains separate."""
import argparse,hashlib,importlib.util,json,sys,zlib
from pathlib import Path
from contract import ROOT,HERE,ABI,PAIRS,NAMES,topology
sys.path.insert(0,str(ROOT/'project/control_p_compute_v0_1'))
from run_a2 import assemble,mem
spec=importlib.util.spec_from_file_location('r82_old_numeric_vectors',ROOT/'project/control_five_boot_v1/images.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)


def rows(kind,peer,epoch):
    if kind==0:
        code=[old.command(0,3,(23,24),25),old.command(0,3,(23,24,26),27)]
        if peer==0:
            for source,dst in ((25,80),(27,81),(80,90),(81,91)):
                code += [dict(native_op=0x103,native0=dst),dict(native_op=0x101,native0=source|dst<<10),dict(native_op=0x102)]
        else:code += [dict(native_op=0x101,native0=25|60<<10)]
        return code
    code=old.operations(kind,epoch)
    if kind in (1,2) and peer==3:code += [dict(native_op=0x101,native0=15|60<<10)]
    return code


def generate(pair,out):
    k0,k1=pair
    for epoch,variant,fault in ((1,0,False),(2,0,False),(1,0,True)):
        dst=out/(f'e{epoch}-fault' if fault else f'e{epoch}-v{variant}');dst.mkdir(parents=True,exist_ok=True)
        images=[];seeds=[];checks=[];flows=[[],[]];write_bytes=0
        if k1==3 and k0 in (0,1,2):
            mother=[dict(op='G_CALL',a=0,b=2,c=0),dict(op='G_WAIT',x=4),dict(op='G_CALL',a=1,b=3,c=0),dict(op='G_WAIT',x=8),dict(op='G_END')]
        else:mother=[dict(op='G_CALL',a=0,b=2,c=0),dict(op='G_CALL',a=1,b=3,c=0),dict(op='G_WAIT',x=12),dict(op='G_END')]
        images.append(('mother',assemble('mother',mother,{},198000+k0*100+k1*10,0,ABI,topology(k0,k1),instruction_version=2)))
        for side,kind in enumerate(pair):
            peer=pair[1-side];operations=[dict(native_op=0xffff)] if fault else rows(kind,peer,epoch)
            program=[];records=[]
            for index,row in enumerate(operations):
                program += [dict(op='L_EXEC',a=0,b=0,c=index),dict(op='L_WAIT',x=1)]
                records.append(dict(row,resource=0,service=0,native_abi_id=ABI))
            program.append(dict(op='L_END'));image_id=198001+k0*100+k1*10+side
            task=dict(block_type=kind,entry_pc=0,max_steps=len(program),required_resources=1,program_image_id=image_id,topology_id=topology(k0,k1),native_abi_id=ABI)
            images.append((f'local{side}',assemble('local',program,dict(task=[task],execution=records),image_id,1,ABI,topology(k0,k1),instruction_version=2)))
            if kind==0:
                aa=2+side;bb=3+side;cc=5+side
                for address,value in ((23,old.pack16([aa]*8)),(24,old.pack16([bb]*8)),(26,old.pack16([cc]*8))):seeds.append((12,side+1,address*16,value))
                own=[old.pack16([aa*bb]*8),old.pack16([aa*bb+cc]*8)]
                if peer==0:
                    other=[old.pack16([(3-side)*(4-side)]*8),old.pack16([(3-side)*(4-side)+(6-side)]*8)]
                    flows[side]=own+other;write_bytes+=96
                else:
                    flows[side]=own[:1];write_bytes+=32
                    checks.append((11,2,60*16,own[0],(1<<128)-1))
            else:
                ss,cc=old.vectors(kind,epoch,0)
                seeds += [(op,side+1,addr,val) for op,target,addr,val in ss if target==side+1]
                checks += [(op,side+1,addr,val,mask) for op,target,addr,val,mask in cc if target==side+1]
                write_bytes += {1:32,2:48,3:32,4:64}[kind]
                if kind in (1,2) and peer==3:
                    value=next(val for op,target,addr,val,mask in cc if target==side+1 and addr==15*16)
                    flows[side]=[value];checks.append((11,2,60*16,value,(1<<128)-1))
        counts=[];crcs=[];index=[]
        for name,data in images:
            mem(dst/(name+'.mem'),data);counts.append(len(data)//16);crcs.append(zlib.crc32(data))
            index.append({'role':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'crc32':crcs[-1]})
        counts += [len(seeds),len(checks),write_bytes]
        for name,values,width in [('counts',counts,8),('crc',crcs,8),('flow-counts',list(map(len,flows)),8)]:
            (dst/(name+'.mem')).write_text(''.join(f'{x:0{width}x}\n' for x in values))
        for side,values in enumerate(flows):
            (dst/f'flows{side}.mem').write_text(''.join(f'{x:032x}\n' for x in values) or '0\n')
        (dst/'seeds.mem').write_text(''.join(f'{op<<272|target<<270|addr<<256|value:069x}\n' for op,target,addr,value in seeds))
        (dst/'checks.mem').write_text(''.join(f'{op<<1040|target<<1038|addr<<1024|mask<<512|value:0261x}\n' for op,target,addr,value,mask in checks))
        (dst/'reference.json').write_text(json.dumps({'pair':list(pair),'epoch':epoch,'fault':fault,'images':index,'expected_writes':write_bytes,'flows':flows,'checks':checks,'seeds':seeds,
            'scope':'hand-authored programs; U/F/C to P passive RAW copy only, no format conversion; J/P independent kernels, no J-to-P commit chain'},indent=2)+'\n')
    print('PASS R8.2 hand-authored program images',NAMES[k0]+'/'+NAMES[k1])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pair',type=int,choices=range(9),required=True);p.add_argument('out',type=Path);a=p.parse_args();generate(PAIRS[a.pair],a.out)
