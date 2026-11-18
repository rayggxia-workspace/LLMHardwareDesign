"""Observe real TLM bindings and resource unions; optionally calibrate E32 MUL.

This is a TLM deployment trace, not proof that the complete model has RTL.
The existing numerical and traffic acceptance remains mandatory.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import gzip
import json
from pathlib import Path

from operator_observation import OperatorObservation


class Intervals:
    def __init__(self):
        self.lo = self.hi = None
        self.closed = self.overlap = self.calls = 0

    def add(self, lo, hi):
        if hi < lo:
            raise ValueError('reversed resource interval')
        self.calls += 1
        if self.hi is None:
            self.lo, self.hi = lo, hi
        elif lo >= self.hi:
            self.closed += self.hi-self.lo
            self.lo, self.hi = lo, hi
        else:
            if lo < self.lo:
                raise ValueError('resource requests not chronological')
            self.overlap += max(0, min(hi, self.hi)-lo)
            self.hi = max(self.hi, hi)

    def seal(self, time):
        busy = self.closed
        if self.hi is not None:
            busy += max(0, min(time, self.hi)-self.lo)
            if self.hi <= time:
                self.lo = self.hi = None
            else:
                self.lo = max(time, self.lo)
        row = dict(busy_union_ps=busy, overlapping_request_ps=self.overlap, calls=self.calls)
        self.closed = self.overlap = self.calls = 0
        return row


class DeploymentObservation(OperatorObservation):
    def __init__(self, execution, *, calibrate=False):
        self._active_name = 'prefill' if execution.plan['mode']=='prefill' else 'first_token'
        self.start = 0
        self.calibrate = calibrate
        self.resources = defaultdict(Intervals)
        self.control = Counter()
        self.control_windows = {}
        self.route_counts = Counter()
        self.provider_live = {}
        self.local_live = {}
        self.trace = gzip.open(execution.output/'deployment-events.jsonl.gz', 'wt', encoding='utf-8')
        super().__init__(execution)
        self.bindings = []
        for key, provider in list(execution.providers.items()):
            self.bindings.append(dict(key=list(key), provider=provider.__qualname__,
                                     module=provider.__module__))
            execution.providers[key] = self.provider(key, provider)
        for group in ('n','e'):
            for site, unit in enumerate(getattr(execution,group)):
                unit.leaf = self.leaf(group, site, unit, unit.leaf)
        original_capture = execution.dram.capture_energy
        def capture(label):
            original_capture(label)
            if label in ('prefill_end','retire_1','retire_2','end'):
                self.seal(execution.clock.now)
                self._active_name = 'decode' if label=='retire_1' else 'outside'
        execution.dram.capture_energy = capture
        scheduler = execution.scheduler
        original_install = scheduler.install_pm
        def install(address, image_bytes, *, mother):
            lo=execution.clock.now
            original_install(address,image_bytes,mother=mother)
            hi=execution.clock.now
            kind='mother' if mother else 'local'
            self.control[kind+'_install_calls']+=1
            self.control[kind+'_install_bytes']+=image_bytes
            self.control[kind+'_install_elapsed_ps']+=hi-lo
            self.resources[kind+'_installer'].add(lo,hi)
            self.event('install',kind=kind,address=address,bytes=image_bytes,start_ps=lo,end_ps=hi)
        scheduler.install_pm=install
        original_submit=scheduler.submit_local
        def submit(target,slot,addresses,dispatch):
            lo=execution.clock.now
            handle=original_submit(target,slot,addresses,dispatch)
            if target in self.local_live:
                raise ValueError('overlapping local target')
            self.local_live[target]=(handle,lo)
            self.control['local_calls_site%d'%target]+=1
            self.event('call',target=target,slot=slot,handle=handle,addresses=list(addresses),time_ps=lo)
            return handle
        scheduler.submit_local=submit
        parent=self
        class Terminals(dict):
            def __setitem__(self,handle,success):
                matches=[(site,row) for site,row in parent.local_live.items() if row[0]==handle]
                if len(matches)!=1 or success is not True:
                    raise ValueError('unmatched or failed terminal')
                site,(_,lo)=matches[0];now=execution.clock.now
                parent.resources['local_target_%d'%site].add(lo,now)
                parent.control['local_service_plus_transport_ps_site%d'%site]+=now-lo
                parent.event('terminal',target=site,handle=handle,time_ps=now)
                del parent.local_live[site]
                super().__setitem__(handle,success)
        scheduler.terminals=Terminals(scheduler.terminals)
        import qwen3_short
        old_page=qwen3_short.run_page
        def page(*args,**kw):
            original=kw['instruction']
            def instruction(op):
                lo=execution.clock.now
                original(op)
                hi=execution.clock.now
                self.control['mother_opcode_%02x'%op]+=1
                self.control['mother_instruction_elapsed_ps']+=hi-lo
                self.resources['mother_instruction'].add(lo,hi)
            kw['instruction']=instruction
            old_page(*args,**kw)
        qwen3_short.run_page=page

    def event(self,kind,**fields):
        self.trace.write(json.dumps(dict(kind=kind,window=self._active_name,**fields),separators=(',',':'))+'\n')

    def window(self,ps):
        return self._active_name

    def provider(self,key,provider):
        def bind(record):
            run=provider(record)
            descriptor_sha=sha256(record).hexdigest()
            def start(done):
                site=key[0];lo=self.execution.clock.now
                if site in self.provider_live:
                    raise ValueError('physical target has concurrent provider services')
                self.provider_live[site]=key
                self.route_counts['/'.join(map(str,key))]+=1
                self.event('dispatch',key=list(key),descriptor_sha256=descriptor_sha,time_ps=lo)
                def end():
                    hi=self.execution.clock.now
                    self.resources['provider_site%d'%site].add(lo,hi)
                    self.control['provider_busy_ps_site%d'%site]+=hi-lo
                    del self.provider_live[site]
                    self.event('provider_done',key=list(key),time_ps=hi)
                    done()
                run(end)
            return start
        return bind

    def leaf(self,group,site,unit,leaf):
        def invoke(opcode,cycles,done):
            if opcode=='e_product_packets' and cycles!=9:
                raise ValueError('E32 source duration changed')
            actual=18 if self.calibrate and opcode=='e_product_packets' else cycles
            lo=self.execution.clock.now
            hi=lo+unit.sram.core_ps*actual-lo%unit.sram.core_ps
            block=('E32' if opcode.startswith('e_') else 'N' if opcode.startswith('n_') else 'G32')
            self.resources['site%d_%s'%(site,block)].add(lo,hi)
            self.control['%s_site%d_%s_calls'%(group,site,opcode)]+=1
            self.control['%s_site%d_%s_cycles'%(group,site,opcode)]+=actual
            # Retain the existing counter and actual completion callback. The
            # scheduler consequently recomputes all overlap and DDR waiting.
            return leaf(opcode,actual,done)
        return invoke

    def m_group(self,bank,begin,cycles):
        self.resources['site%d_M272'%bank.component_site].add(begin,begin+cycles*bank.core_ps-begin%bank.core_ps)
        self.resources['site%d_Mshared'%bank.component_site].add(begin,begin+cycles*bank.core_ps-begin%bank.core_ps)

    def native_m_group(self,bank,begin,cycles):
        self.resources['site%d_Mordinary'%bank.component_site].add(begin,begin+cycles*bank.core_ps-begin%bank.core_ps)
        self.resources['site%d_Mshared'%bank.component_site].add(begin,begin+cycles*bank.core_ps-begin%bank.core_ps)

    def seal(self,time):
        name=self._active_name
        if name in self.control_windows:
            raise ValueError('duplicate window seal')
        duration=time-self.start
        rows={k:v.seal(time) for k,v in self.resources.items()}
        if any(v['busy_union_ps']>duration for v in rows.values()):
            raise ValueError('resource union exceeds actual window')
        for key,row in rows.items():
            if key.endswith('_E32') and row['overlapping_request_ps']:
                raise ValueError('unresolved physical E32 overlap at '+key)
        self.windows[name]={'start_ps':self.start,'end_ps':time}
        if name!='outside':
            for site in range(len(self.execution.sram)):
                for suffix,target in (('M272',self.m),('Mordinary',self.native_m)):
                    row=rows.get('site%d_%s'%(site,suffix),{})
                    target[name][site]['groups_dispatched']=row.get('calls',0)
                    target[name][site]['busy_interval_union_ps']=row.get('busy_union_ps',0)
        self.control_windows[name]=dict(start_ps=self.start,end_ps=time,elapsed_ps=duration,
                                       counters=dict(self.control),resources=rows,routes=dict(self.route_counts))
        self.control.clear();self.route_counts.clear();self.start=time

    def write(self,destination):
        if self.provider_live or self.local_live:
            raise ValueError('control/provider not drained')
        self.trace.close()
        super().write(destination)
        data=dict(scope='Actual sealed-plan TLM provider/control/resource binding; physical RTL implementation and clock gating require separate evidence',
                  calibrated_e32_product_cycles=18 if self.calibrate else 9,
                  core_period_ps=self.execution.sram[0].core_ps,data_sram_bits=512,
                  bindings=sorted(self.bindings,key=lambda x:x['key']),windows=self.control_windows,
                  gating={'tlm_clock_gating_modeled':False,'power_gating_modeled':False,
                          'policy':'no unproven leakage/idle saving; gate activity is not a gated clock'},
                  physical_e32_overlap_ps=0,local_concurrent_provider_overlap=False,
                  trace_sha256=sha256((self.execution.output/'deployment-events.jsonl.gz').read_bytes()).hexdigest())
        destination.with_name('deployment-observation.json').write_text(json.dumps(data,indent=2)+'\n')
