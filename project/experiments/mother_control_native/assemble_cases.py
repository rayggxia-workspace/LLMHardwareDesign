"""Independent bounded 64bit mother image producer for native profile tests."""
import argparse,json
from pathlib import Path
OPS={'CALL':0x10,'WAIT':0x11,'EVENT':0x12,'MOVI':0x13,'ADDI64':0x16,'LOOP':0x17,'END':0x1f}
def image(program,bindings=(),version=3,abi=0x02500002,max_steps=None):
    code=b''.join(((OPS[op]<<56)|(a<<48)|(b<<40)|(c<<32)|x).to_bytes(8,'little') for op,a,b,c,x in program)
    code+=b'\0'*((-len(code))%16)
    total=128+len(code)+16*len(bindings)
    header=bytearray(128)
    def field(bit,width,value):header[bit//8:(bit+width)//8]=value.to_bytes(width//8,'little')
    for bit,width,value in ((0,64,0x313041534943424c),(64,16,version),(88,8,8),(96,32,total),(128,32,0),(160,32,len(program)),(192,32,128),(416,32,(max_steps if max_steps is not None else max(1024,len(program)+1))),(480,32,900),(512,32,0x25000001),(544,32,abi),(576,16,len(bindings)),(608,32,128+len(code) if bindings else 0),(672,32,0x02590003)):
        field(bit,width,value)
    return bytes(header)+code+b''.join((event|(source<<8)).to_bytes(16,'little') for event,source in bindings)
def call(target,token=None):return ('CALL',target,target if token is None else token,0,0)
def wait(mask):return ('WAIT',0,0,0,mask)
END=('END',0,0,0,0)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    cases=[]
    def add(name,program,bindings=(),**params):
        raw=image(program,bindings,params.pop('VERSION',3),params.pop('ABI',0x02500002),params.pop('MAX_STEPS',None))
        path=args.out/(name+'.mem');path.write_text('\n'.join(f'{int.from_bytes(raw[i:i+16],"little"):032x}' for i in range(0,len(raw),16))+'\n')
        cases.append({'name':name,'image':str(path.resolve()),'WORDS':len(raw)//16,**params})
    add('threeP_plus_U',[call(i) for i in range(4)]+[wait(15),END],CALLS=4,MIN_ACTIVE=4,DELAY0=350,DELAY1=400)
    add('nine_residents',[call(i) for i in range(9)]+[wait(511),END],CALLS=9,MIN_ACTIVE=9,DELAY0=450,DELAY1=500)
    add('token15_target8',[call(8,15),wait(1<<15),END],CALLS=1)
    add('nine_ready_events',[call(i) for i in range(9)]+[('EVENT',7,i,0,0) for i in range(9)]+[wait(511),END],[(i,i) for i in range(9)],CALLS=9,READY_MASK=511,MIN_ACTIVE=4,DELAY0=500,DELAY1=550,STALL=1)
    add('reusable_jobs',[call(8,15),wait(1<<15),END],CALLS=2,RUNS=2,STALL=2)
    add('held_fourth_call',[call(i) for i in range(4)]+[wait(15),END],CALLS=4,MIN_ACTIVE=4,HOLD_TARGET=3,HOLD_CYCLES=80,DELAY0=300,DELAY1=400)
    add('cancel_nine',[call(i) for i in range(9)]+[wait(511),END],CALLS=9,MIN_ACTIVE=9,ERROR_TARGET=0,DELAY0=450,DELAY1=2000,CANCELS=8,EXPECTED=9)
    add('disabled_target8',[call(8),wait(1<<8),END],CALLS=0,ENABLED=255,EXPECTED=4,MIN_ACTIVE=0)
    add('invalid_target9',[call(9),END],CALLS=0,EXPECTED=2,MIN_ACTIVE=0)
    add('unsupported_128_image',[END],CALLS=0,MODE=2,VERSION=1,MIN_ACTIVE=0)
    add('wrong_native_abi',[END],CALLS=0,MODE=2,ABI=0x01930001,MIN_ACTIVE=0)
    for inject,label in ((1,'wrong_generation'),(2,'wrong_source'),(4,'late_wrong_job'),(5,'wrong_topology'),(6,'old_packet_version')):
        add(label,[call(i) for i in range(4)]+[wait(15),END],CALLS=4,MIN_ACTIVE=4,DELAY0=500,DELAY1=1000,INJECT=inject,CANCELS=4,EXPECTED=17)
    add('duplicate_terminal',[call(i) for i in range(4)]+[wait(15),END],CALLS=4,MIN_ACTIVE=4,DELAY0=150,DELAY1=1000,INJECT=3,CANCELS=3,EXPECTED=17)
    add('duplicate_after_result',[call(0),wait(1),END],CALLS=1,INJECT=7)
    add('old_job_after_restart',[call(0),wait(1),END],CALLS=2,RUNS=2,INJECT=8,CANCELS=1,EXPECTED=17)
    add('timeout_late_drain_recover',[call(0),wait(1),END],CALLS=1,NO_TERMINAL=0,POISON=1,CANCELS=1,RECOVER_POISON=1)
    add('past_old256',[('MOVI',0,0,0,i) for i in range(256)]+[END],CALLS=0,MIN_ACTIVE=0)
    add('full_PM_no_events',[('MOVI',0,0,0,i) for i in range(2031)]+[END],CALLS=0,MIN_ACTIVE=0)
    add('full_PM_nine_events',[call(i) for i in range(9)]+[('EVENT',7,i,0,0) for i in range(9)]+[wait(511)]+[('MOVI',0,0,0,i) for i in range(1994)]+[END],[(i,i) for i in range(9)],CALLS=9,READY_MASK=511,MIN_ACTIVE=4,DELAY0=500,DELAY1=550)
    add('past_physical_PM',[('MOVI',0,0,0,i) for i in range(2032)]+[END],CALLS=0,MIN_ACTIVE=0,MODE=6)
    add('old_v2_rejected',[END],CALLS=0,MODE=2,VERSION=2,MIN_ACTIVE=0)
    loop=[('MOVI',0,0,0,0xffffff80),('MOVI',1,0,0,1),('MOVI',7,0,0,3),call(0),wait(1),('ADDI64',0,0,0,128),('LOOP',7,0,0,3),END]
    add('bounded_pointer_loop',loop,CALLS=3,CHECK_PTR=1,PTR_START=0x1ffffff80,PTR_STRIDE=128,TIMING=1)
    add('loop_zero',[('MOVI',7,0,0,0),('LOOP',7,0,0,0),END],CALLS=0,MIN_ACTIVE=0,EXPECTED=19)
    add('loop_overbound',[('MOVI',7,0,0,65536),('LOOP',7,0,0,0),END],CALLS=0,MIN_ACTIVE=0,EXPECTED=19)
    add('loop_forward_target',[('MOVI',7,0,0,2),('LOOP',7,0,0,2),END],CALLS=0,MIN_ACTIVE=0,EXPECTED=19)
    add('pointer_overflow',[('MOVI',0,0,0,0xfffffff0),('MOVI',1,0,0,0xffffffff),('ADDI64',0,0,0,128),END],CALLS=0,MIN_ACTIVE=0,EXPECTED=18)
    add('pointer_odd_pair',[('ADDI64',1,0,0,128),END],CALLS=0,MIN_ACTIVE=0,EXPECTED=18)
    add('loop_step_budget',[('MOVI',7,0,0,2),('LOOP',7,0,0,0),END],CALLS=0,MIN_ACTIVE=0,MAX_STEPS=20,EXPECTED=12)
    add('repeated_READY_loop',[('MOVI',7,0,0,3),call(0),('EVENT',6,0,0,0),wait(1),('LOOP',7,0,0,1),END],[(0,0)],CALLS=3,READY_MASK=1,EXPECT_READY=3)
    add('cancel_inside_loop',[('MOVI',7,0,0,3)]+[call(i) for i in range(4)]+[wait(15),('LOOP',7,0,0,1),END],CALLS=4,MIN_ACTIVE=4,ERROR_TARGET=0,DELAY0=150,DELAY1=2000,CANCELS=3,EXPECTED=9)
    (args.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
if __name__=='__main__':main()
