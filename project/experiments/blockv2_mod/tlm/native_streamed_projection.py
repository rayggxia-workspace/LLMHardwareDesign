"""Descriptor-driven U feeder joined to the PR260 P projection provider.

One selected static U/P link, one live P input key, one bounded U K-range.
No graph, layer counter, hidden source loads, or synthesized FFN schedule.
"""
from collections import Counter
from struct import unpack,unpack_from,pack
from native_tlm_u import rne

class StreamedProjection:
    def __init__(self,projection,*,input_key_offset,input_key_bytes):
        self.p=projection
        self.key_offset=input_key_offset;self.key_bytes=input_key_bytes
        self.scope=None;self.feed=None;self.request=None;self.held=None
        self.last_session=0
        self.stats=Counter()

    def projection(self,record):
        key=int.from_bytes(record[self.key_offset:self.key_offset+self.key_bytes],'little')
        full_k=unpack_from('<H',record,76)[0]
        destination=unpack_from('<H',record,84)[0]
        run=self.p.provider(record,packed_tile=self.window)
        def execute(done):
            if self.scope is not None:raise ValueError('overlapping P scopes on selected link')
            self.scope={'key':key,'full_k':full_k,'destination':destination,'next_k':0}
            def finish():
                self.release()
                if self.request is not None or self.feed is not None:
                    raise ValueError('P completed before explicit U range drained')
                self.scope=None
                done()
            run(finish)
        return execute

    def supplier(self,record):
        source,scratch,destination,tiles=unpack_from('<4H',record,16)
        key=int.from_bytes(record[24:40],'little')
        session,first=unpack_from('<IH',record,40)
        op=unpack_from('<H',record,6)[0]
        words=tiles*32
        if (op not in (1,2) or (op==1 and first) or first%128 or not 0<tiles<=32
            or source+words>1024 or scratch>1008 or destination>1008
            or source<scratch+16 and scratch<source+words
            or any(record[46:124]) or not session or not key):
            raise ValueError('invalid PFED window')
        def execute(done):
            if self.feed is not None or session<=self.last_session:
                raise ValueError('PFED live range or stale session')
            self.last_session=session
            self.feed={'source':source,'scratch':scratch,'destination':destination,
                       'key':key,'first':first//128,'end':first//128+tiles,
                       'next':first//128,'done':done}
            self.match()
        return execute

    def release(self):
        if self.held is None:return
        f=self.held;self.held=None
        self.stats['released_windows']+=1
        if f['next']==f['end']:
            if self.feed is not f:raise ValueError('PFED range identity changed')
            self.feed=None
            f['done']()

    def window(self,k,done):
        # A request for the next K window proves all consumers of the prior
        # window have drained. The final window drains at P service terminal.
        self.release()
        if self.request is not None or self.scope is None or k!=self.scope['next_k']:
            raise ValueError('P window lease ordering')
        self.scope['next_k']+=1
        self.request=(k,done)
        self.match()

    def match(self):
        if self.request is None or self.feed is None:return
        k,done=self.request;f=self.feed;s=self.scope
        if (s is None or f['key']!=s['key'] or f['destination']!=s['destination']
            or k!=f['next'] or not f['first']<=k<f['end']
            or f['end']*128>s['full_k']):
            raise ValueError('PFED does not match active P input lease')
        self.request=None
        source=f['source']+32*(k-f['first'])
        def scan(raw):
            peak=max(abs(v) for v in unpack('<128i',raw))
            shift=next(i for i in range(18) if peak<=32767<<i)
            def convert(data):
                values=tuple(rne(v,shift) for v in unpack('<128i',data))
                if any(not -32768<=v<=32767 for v in values):
                    raise ValueError('quantized activation overflow')
                packed=pack('<128h',*values)
                def committed():
                    def copy(payload):
                        f['next']+=1;self.held=f
                        self.stats['supplied_windows']+=1
                        done(payload,shift)
                    self.p.read_span(self.p.source,f['scratch'],16,copy)
                self.p.write_span(self.p.source,f['scratch'],packed,committed)
            self.p.edge(lambda:self.p.read_span(self.p.source,source,32,convert))
        self.p.read_span(self.p.source,source,32,scan)
