"""Static binary authoring only; compare every example SHA to a server run."""
import argparse,json,pathlib,sys
import images,cohort
def main():
    p=argparse.ArgumentParser(); p.add_argument('--server-report',required=True,type=pathlib.Path); p.add_argument('--output',required=True,type=pathlib.Path); a=p.parse_args()
    report=json.loads(a.server_report.read_text(encoding='utf-8')); runs={r['case']['name']:r for r in report['results']}; examples=[]
    for kind in images.SPEC['profiles']:
        files,kinds=images.build(kind,kind=='C'); reference=runs['state_commit' if kind=='C' else kind+'_k1_path1']; blobs={}
        for name,data in files.items():
            parsed=images.parse(data,kinds.get(int(name[5:])) if name!='mother' else None); digest=images.sha(data)
            images.need(digest==reference['images_sha256'][name],'example differs from server executed binary')
            blobs[name]=dict(bytes=len(data),sha256=digest,hex=data.hex(),header=parsed['header'],program=parsed['program'])
        examples.append(dict(kind=kind,source_case=reference['case']['name'],parameters=reference['case']['parameters'],images=blobs))
    fields=[dict(name=n,offset=o,bits=b) for n,o,b in [('version',0,16),('kind',2,8),('participant',3,8),('sequence',4,32),('epoch',8,32),('generation',12,32),
        ('bitmap',16,64),('transaction',24,32),('status',28,16),('flags',30,16),('value0',32,32),('value1',36,32),('value2',40,32),('value3',44,32)]]
    frame=dict(kind=cohort.KINDS['RESET_REQ'],sequence=0x12345678,epoch=2,generation=3,bitmap=0x0102030405060708)
    result=dict(schema='candidate-profile-binary-examples/0.1',deployable=False,ISA='existing v0.1; no opcode or record layout changed',
        examples=examples,management_plane=dict(status='separate proposed management wire format, no RTL serializer',bytes=64,byte_order='little',
            fields=fields,reserved='bytes48..63 all zero; all unassigned semantic fields zero per kind',kinds=cohort.KINDS,example_hex=cohort.pack(frame).hex()),
        export_kind='local static code generation, no simulation; all program SHAs equal actual server cases',python=sys.version)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Static examples match actual server image SHAs:',len(examples),'profiles')
if __name__=='__main__': main()
