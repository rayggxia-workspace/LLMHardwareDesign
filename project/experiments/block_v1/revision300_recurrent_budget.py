"""Reprice the existing finite recurrent plan using a new measured R source."""
import argparse,copy,hashlib,json,math
from pathlib import Path


def calculate(root,report,template):
    raw=report.read_bytes();source=json.loads(raw)
    assert source['passed'] and source['macro']=='R' and source['variant']=='revised'
    result=copy.deepcopy(json.loads(template.read_text()))
    assert result['clock_hz']==300000000 and result['host_reserve_is_assumption']
    assert [m['model']for m in result['models']]==['qwen35','falcon']
    assert len(source['rtl_sha256'])==1
    rtl=root/'project/rtl/block_library_v1/block_v1_r.sv'
    assert next(iter(source['rtl_sha256'].values()))==hashlib.sha256(rtl.read_bytes()).hexdigest()
    result.update(source_report_sha256=hashlib.sha256(raw).hexdigest(),
        source_report=report.relative_to(root).as_posix(),
        prior_budget_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),
        prior_budget=template.relative_to(root).as_posix(),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        physical_implementation_completed=False,
        full_model_10tps_qualified=False)
    for model in result['models']:
        assert hashlib.sha256((root/model['config']).read_bytes()).hexdigest()==model['config_sha256']
        row=next(x for x in source['measurements']['cases']if x['profile']==0 and
            x['size']==model['state_rows'] and x['workload']==('gdn-update'if model['model']=='qwen35'else'ssm-update'))
        assert row['total_cycles']==sum(p['cycles']for p in row['phases'].values())
        blocks=model['blocks_per_token']
        assert blocks==model['layers']*model['heads']*model['channels_per_head']//8
        model['cold_macro_cycles']=row['total_cycles']
        model['aggregate_r_cycles_per_token']=blocks*row['total_cycles']
        model['aggregate_r_time_ms']=model['aggregate_r_cycles_per_token']/300000
        model['phase_cycles']={k:blocks*p['cycles']for k,p in row['phases'].items()}
        traffic={
            'request_valid_bytes':sum(p['request_data_valid_bytes']for p in row['phases'].values())*blocks,
            'response_valid_bytes':sum(p['response_data_valid_bytes']for p in row['phases'].values())*blocks,
            'request_container_bytes':sum(p['request_container_bytes']for p in row['phases'].values())*blocks,
            'response_container_bytes':sum(p['response_container_bytes']for p in row['phases'].values())*blocks}
        # Pipeline latency must not silently change the previous traffic plan.
        assert traffic==model['traffic'];model['traffic']=traffic
        for candidate in model['r_count_candidates']:
            batches=model['layers']*math.ceil((blocks//model['layers'])/candidate['count'])
            assert batches==candidate['scheduled_macro_batches']
            candidate['r_stage_cycles']=batches*row['total_cycles']
            candidate['r_stage_ms']=candidate['r_stage_cycles']/300000
            candidate['remaining_device_ms_after_r']=100-result['host_reserve_ms']-candidate['r_stage_ms']
        assert sum(model['phase_cycles'].values())==model['aggregate_r_cycles_per_token']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    for name in ('report','template','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parents[3]
    value=calculate(root,args.report.resolve(),args.template.resolve())
    args.output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
