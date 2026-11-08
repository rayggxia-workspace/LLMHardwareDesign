"""Binary transport to the literal finite-S C++ numeric interpreter.

This accelerates the simulator on its host CPU. It does not change a generated
hardware command, resource reservation, descriptor count or modeled time.
"""
import struct
import subprocess

import numpy as np


METRICS=('external_read_words','external_write_words','initial_zero_loads','grid_tiles',
    'dot_B_loads','dot_A_loads','dot_scales','dot_feeds','dot_executes','final_reads',
    'canonical_outputs','e_sign_services','packed_outputs','flag_outputs',
    'scatter_input_loads','scatter_basis_loads','scatter_executes','scatter_feeds','scatter_scales',
    'peak_P_extent','peak_E_extent','peak_external_tmp')


class NativeTileReplay:
    def __init__(self,ir,command):
        self.hardware=ir['hardware'];self.constants=ir.get('tile_constants',{});self.events=[]
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        self.closed=False

    def _read(self,count):
        data=bytearray()
        while len(data)<count:
            block=self.process.stdout.read(count-len(data))
            if not block:raise ValueError('native tile replay terminated/truncated output')
            data.extend(block)
        return bytes(data)

    def dot(self,node,records,b,binding):
        if self.closed:raise ValueError('native tile replay is closed')
        s=binding['dot_tile'];r,n,k=s['rows'],s['columns'],s['K'];rt,ct=s['tile']
        p=self.hardware['leaf_inventory'][binding['macro_binding']['M']]
        em=self.hardware['leaf_inventory'][binding['macro_binding']['E']] if ct>1 else None
        if records.shape!=(r,k,3) or records.min()<-32768 or records.max()>32767:
            raise ValueError('native prepared tile record region differs')
        weights=np.asarray(b,dtype=np.int64).reshape(-1,k,n)
        if weights.shape[0]!=1 or weights.min()<-32768 or weights.max()>32767:
            raise ValueError('native tile needs row-shared S16 B')
        header=(0x54494c45,1,r,n,k,rt,ct,s['final_shift'],self.hardware['sites'][p['site']]['words'],
                self.hardware['sites'][em['site']]['words'] if em else 0,binding['tile_work']['temporary_external_words'])
        self.process.stdin.write(struct.pack('<11I',*header))
        for array in (self.constants['records'],records,weights[0]):
            self.process.stdin.write(np.asarray(array,dtype='<i2').tobytes(order='C'))
        self.process.stdin.flush()
        status,length=struct.unpack('<2I',self._read(8))
        if status:
            diagnostic=self._read(length).decode('utf-8',errors='replace')
            raise ValueError('native tile replay rejected input: '+diagnostic)
        if length!=len(METRICS):raise ValueError('native tile metric protocol differs')
        metrics=dict(zip(METRICS,struct.unpack('<'+str(length)+'Q',self._read(8*length))))
        raw=np.frombuffer(self._read(8*r*n),dtype='<i8').copy().reshape(node['shape'])
        final=np.frombuffer(self._read(4*r*n),dtype='<i4').astype(np.int64).reshape(node['shape'])
        expected=binding['tile_work'];counts={key:metrics[key] for key in METRICS[:-3] if metrics[key]}
        for key in METRICS[:-3]:
            if metrics[key]!=expected.get(key,0):raise ValueError('native tile command/transfer count differs '+key)
        if (metrics['peak_P_extent']>expected['P_words'] or metrics['peak_E_extent']>expected['E_words'] or
            metrics['peak_external_tmp']>expected['temporary_external_words']):
            raise ValueError('native tile replay allocation exceeds plan')
        self.events.append({'primitive':node['id'],'tile':[rt,ct],'counts':counts,
            **{key:metrics[key] for key in METRICS[-3:]}})
        return raw,final

    def close(self):
        if self.closed:return
        self.closed=True;self.process.stdin.close()
        status=self.process.wait(timeout=10)
        self.process.stdout.close()
        if status:raise ValueError('native tile replay exited with status '+str(status))
