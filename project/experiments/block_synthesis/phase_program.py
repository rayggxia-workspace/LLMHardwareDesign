"""Exact finite repeat programs with FCFS, ACK-boundary channel arbitration.

Timing-only infrastructure: every worker owns a distinct LC/M/S context.
Service times are constant symbols from a declared model. No bank/row state,
addresses, values, energy or full-system qualification is inferred here.
Long loops are skipped only when the entire normalized event/cursor state
recurs and every live loop counter decreases without crossing its boundary.
"""
from collections import Counter


class PhaseEventLimit(ValueError):
    def __init__(self,diagnostic):
        super().__init__('exact event limit exceeded before completion')
        self.diagnostic=diagnostic


def compile_program(body, channels):
    if type(channels) is not int or channels < 1:
        raise ValueError('positive channel count required')
    code = []
    def emit(node):
        if 'sequence' in node:
            for child in node['sequence']:emit(child)
        elif 'repeat' in node:
            n = node['repeat']
            if type(n) is not int or n < 0:raise ValueError('finite nonnegative repeat required')
            if not n:return
            start = len(code);code.append(None)
            emit(node['body'])
            if len(code) == start+1:
                code.pop();return
            code[start] = ('loop',n,len(code))
            code.append(('end',start))
        else:
            c,t = node['channel'],node['ticks']
            if type(c) is not int or not -1 <= c < channels or type(t) is not int or t < 0:
                raise ValueError('invalid phase channel/duration')
            if t:code.append(('phase',c,t,node.get('kind','unspecified')))
    emit(body)
    return tuple(code)


class Cursor:
    def __init__(self, code):
        self.code = code;self.pc = 0;self.stack = [];self.generations = Counter()
        self.seek()

    def seek(self):
        while self.pc < len(self.code):
            op = self.code[self.pc]
            if op[0] == 'phase':return
            if op[0] == 'loop':
                self.generations[self.pc] += 1
                self.stack.append([self.pc,op[1],self.generations[self.pc]]);self.pc += 1
            else:
                if not self.stack or self.stack[-1][0] != op[1]:raise ValueError('invalid loop cursor')
                self.stack[-1][1] -= 1
                if self.stack[-1][1]:self.pc = op[1]+1
                else:self.stack.pop();self.pc += 1

    def complete(self):
        if self.pc >= len(self.code):raise ValueError('completed finished worker')
        self.pc += 1;self.seek()

    @property
    def done(self):return self.pc == len(self.code)

    @property
    def phase(self):return self.code[self.pc]


def simulate(programs, channels, *, fast_forward=True, boundary=4, event_limit=1000000, decompose=True):
    """Integer event execution; ties ordered by request age, then worker ID.

    A repeat witness never erases residual work or assumes average bandwidth.
    The boundary tail is executed normally. event_limit rejects incomplete
    experiments, rather than returning an approximate or partial makespan.
    """
    if not programs or type(boundary) is not int or boundary < 1:
        raise ValueError('finite workers and positive boundary required')
    cursors = [Cursor(compile_program(p,channels)) for p in programs]
    if decompose and len(cursors) > 1:
        parents = list(range(len(cursors)))
        def root(i):
            while parents[i] != i:i = parents[i]
            return i
        sets = [{op[1] for op in cur.code if op[0] == 'phase' and op[1] >= 0} for cur in cursors]
        for i in range(len(cursors)):
            for j in range(i):
                if sets[i] & sets[j]:parents[root(i)] = root(j)
        components = {}
        for i in range(len(cursors)):components.setdefault(root(i),[]).append(i)
        if len(components) > 1:
            counts = Counter();finished = {};completed = [0]*len(cursors)
            total = dict(executed_events=0,fast_forward_jumps=0,skipped_ticks=0,skipped_events=0)
            details = []
            for ids in components.values():
                result = simulate([programs[i] for i in ids],channels,fast_forward=fast_forward,
                                  boundary=boundary,event_limit=event_limit,decompose=False)
                counts.update(result['phase_counts'])
                for local,i in enumerate(ids):
                    finished[i] = result['worker_completion'][local]
                    completed[i] = result['worker_phase_counts'][local]
                for field in total:total[field] += result[field]
                details.append({'workers':ids,'makespan':result['makespan']})
            return {**total,'makespan':max(finished.values()),'worker_completion':finished,
                    'phase_counts':dict(counts),'worker_phase_counts':completed,'independent_components':details,
                    'scope':'exact channel-disjoint timing components, distinct LC/M/S workers; skipped_ticks sums component time'}
    now = 0;ready = list(range(len(cursors)))
    active = {};waiting = {};finished = {};counts = Counter()
    completed = [0]*len(cursors);witnesses = {}
    executed = jumps = skipped_ticks = skipped_events = 0
    while True:
        for i in sorted(ready):
            cur = cursors[i]
            if cur.done:finished[i] = now;continue
            _,channel,ticks,kind = cur.phase
            if channel < 0:active[i] = now+ticks
            else:waiting[i] = (now,channel)
        used = {cursors[i].phase[1] for i in active if cursors[i].phase[1] >= 0}
        for channel in range(channels):
            if channel in used:continue
            candidates = [i for i,(_,c) in waiting.items() if c == channel]
            if candidates:
                i = min(candidates,key=lambda i:(waiting[i][0],i))
                active[i] = now+cursors[i].phase[2];del waiting[i]
        if len(finished) == len(cursors):break
        if not active:raise ValueError('event system failed to drain')
        if fast_forward:
            signature = (tuple((cur.pc,tuple((pc,n if n <= boundary else
                                             'entry' if n == cur.code[pc][1] else '*')
                                            for pc,n,_ in cur.stack))
                               for cur in cursors),
                         tuple(sorted((i,end-now) for i,end in active.items())),
                         tuple(sorted((i,request-now,c) for i,(request,c) in waiting.items())))
            remaining = tuple(n for cur in cursors for _,n,_ in cur.stack)
            epochs = tuple(epoch for cur in cursors for _,_,epoch in cur.stack)
            generations = tuple(cur.generations.copy() for cur in cursors)
            previous = witnesses.get(signature)
            if previous is not None:
                then,old_rem,old_epochs,old_generations,old_counts,old_done = previous
                delta = tuple(a-b for a,b in zip(old_rem,remaining))
                if len(delta) != len(remaining):raise ValueError('inconsistent recurrence witness')
                reset_progress = any(d > 0 and a != b for d,a,b in zip(delta,old_epochs,epochs))
                if now > then and delta and all(d >= 0 for d in delta) and any(delta) and not reset_progress:
                    skip = min((n-boundary-1)//d for n,d in zip(remaining,delta) if d)
                    if skip > 0:
                        period = now-then;shift = skip*period
                        idx = 0
                        for cur in cursors:
                            for frame in cur.stack:
                                frame[1] -= skip*delta[idx];idx += 1
                        for cur,old in zip(cursors,old_generations):
                            for pc in list(cur.generations):
                                cur.generations[pc] += skip*(cur.generations[pc]-old.get(pc,0))
                            for frame in cur.stack:frame[2] = cur.generations[frame[0]]
                        for key in set(counts)|set(old_counts):
                            counts[key] += skip*(counts[key]-old_counts[key])
                        extra = [skip*(n-old) for n,old in zip(completed,old_done)]
                        completed = [n+e for n,e in zip(completed,extra)]
                        now += shift
                        active = {i:end+shift for i,end in active.items()}
                        waiting = {i:(request+shift,c) for i,(request,c) in waiting.items()}
                        jumps += 1;skipped_ticks += shift;skipped_events += sum(extra)
                        # Keep outer-loop witnesses: an inner-loop jump must
                        # not erase the opportunity to recognize a repeated
                        # complete output iteration. All saved counters and
                        # times still describe actually executed states.
                elif any(d < 0 for d in delta) or reset_progress:
                    # An inner loop has reset. The old witness cannot cross
                    # this boundary; replace it rather than extrapolating.
                    witnesses[signature] = (now,remaining,epochs,generations,counts.copy(),tuple(completed))
            else:witnesses[signature] = (now,remaining,epochs,generations,counts.copy(),tuple(completed))
        now = min(active.values())
        ready = sorted(i for i,end in active.items() if end == now)
        for i in ready:
            counts[cursors[i].phase[3]] += 1;completed[i] += 1
            cursors[i].complete();del active[i]
        executed += len(ready)
        if executed > event_limit:
            raise PhaseEventLimit({'now':now,'executed_events':executed,'fast_forward_jumps':jumps,
                'skipped_events':skipped_events,'witnesses':len(witnesses),
                'cursors':[{'pc':c.pc,'stack':c.stack} for c in cursors],
                'active':active,'waiting':waiting,'finished':finished})
    return {'makespan':now,'worker_completion':finished,'phase_counts':dict(counts),
            'worker_phase_counts':completed,'executed_events':executed,
            'fast_forward_jumps':jumps,'skipped_ticks':skipped_ticks,'skipped_events':skipped_events,
            'scope':'constant-cost timing events and FCFS only; no bank/address/numerical or hardware arbitration proof'}


def native_program(body, library, meta, memory):
    """Keep native repeat structure; same order as phase_trace.phases()."""
    from memory import descriptor_ticks
    channel = meta['memory_group'] % memory['channels']
    load = descriptor_ticks(memory,1,'load',meta['io_write_ticks'])
    store = descriptor_ticks(memory,1,'store',meta['io_read_ticks'])
    def phase(c,t,kind):return {'channel':c,'ticks':t,'kind':kind}
    def seq(*nodes):return {'sequence':list(nodes)}
    def visit(node, stack=()):
        if 'call' in node:
            name = node['call']
            if name in stack:raise ValueError('recursive phase template')
            return visit(library[name],stack+(name,))
        if 'repeat' in node:return {'repeat':node['repeat'],'body':visit(node['body'],stack)}
        if 'sequence' in node:return seq(*(visit(n,stack) for n in node['sequence']))
        if node['macro'] not in ('M','IO'):raise ValueError('independent M/IO probe only')
        local = node['macro'] != 'IO'
        return seq({'repeat':node['read_words'],'body':seq(
            phase(channel,load,'external-load-until-S-commit'),
            phase(-1,meta['io_read_ticks'] if local else 0,'S-operand-read'))},
            phase(-1,node.get('ticks',0),node.get('native','IO')),
            {'repeat':node['write_words'],'body':seq(
                phase(-1,meta['io_write_ticks'] if local else 0,'S-result-write'),
                phase(channel,store,'external-store-until-ACK'))})
    return visit(body)


def cached_dot_program(binding, row, library, meta, memory):
    """The existing prepared-A/S16-B scalar Dot, with unchanged traffic.

    Prefix records are filled to S before the output loop; B staging is reused
    within one K. There is one live M context, retained over the full service.
    Only descriptor completion boundaries release the shared memory channel.
    No column tiling, dirty output retention or packing is added here.
    """
    from memory import descriptor_ticks
    c = binding['read_cache']
    if c.get('cost_model') != 'dot-prefix-state-v2' or c['components'][1] != 1:
        raise ValueError('phase probe requires stateful prepared-A/S16-B Dot')
    e = row['evaluation'];h = e['reused_prefix']
    r,n,k = c['rows'],c['columns'],c['K'];ca = c['components'][0];t = c['stripe']
    if not 0 <= h <= t <= k or ca not in (1,3):raise ValueError('unsupported selected cache state')
    if e['scratch_by_site'][c['site']] > meta['words']:raise ValueError('phase probe exceeds finite S')
    channel = meta['memory_group'] % memory['channels']
    load = descriptor_ticks(memory,1,'load',meta['io_write_ticks'])
    seq = lambda *nodes:{'sequence':list(nodes)}
    repeat = lambda count,body:{'repeat':count,'body':body}
    phase = lambda ch,ticks,kind:{'channel':ch,'ticks':ticks,'kind':kind}
    external = phase(channel,load,'external-load-until-S-commit')
    local = phase(-1,meta['io_read_ticks'],'S-operand-read')
    parts = library['partial']['sequence']
    if len(parts) != 4 or 'sequence' not in parts[2] or len(parts[2]['sequence']) != 2:
        raise ValueError('native partial template changed')
    scale,load_a,load_b,execute = parts
    def core(leaf):
        if leaf.get('read_words',0) or leaf.get('write_words',0):
            raise ValueError('core-only phase expected')
        return phase(-1,leaf['ticks'],leaf['native'])
    def operand(leaf, fetch):
        if leaf['read_words'] != 1 or leaf['write_words'] != 0:
            raise ValueError('scalar operand load template changed')
        return seq(external if fetch else seq(),local,phase(-1,leaf['ticks'],leaf['native']))
    def partial(a, streamed):
        return seq(core(scale),operand(load_a,streamed),
                   operand(load_b['sequence'][0],a == 0),
                   operand(load_b['sequence'][1],False),core(execute))
    def term(streamed):return seq(*(partial(a,streamed) for a in range(ca)))
    final = native_program({'call':'dot_final'},library,meta,memory)
    return seq(external,repeat(r*ca*(t-h),external),
               repeat(r*n,seq(repeat(t,term(False)),repeat(k-t,term(True)),final)))


def aggregate(program):
    """Exact counts and duration of a finite program, without expansion."""
    if 'repeat' in program:
        ticks,counts = aggregate(program['body'])
        return ticks*program['repeat'],Counter({k:v*program['repeat'] for k,v in counts.items()})
    if 'sequence' in program:
        ticks = 0;counts = Counter()
        for node in program['sequence']:
            t,c = aggregate(node);ticks += t;counts.update(c)
        return ticks,counts
    return program['ticks'],Counter({program['kind']:int(program['ticks'] > 0)})
