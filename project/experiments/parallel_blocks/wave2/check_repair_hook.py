"""Execute generated Tcl against strict mock ODB/STA objects, including escaped bus names."""
from pathlib import Path
import tempfile
import tkinter
from repair_hook import build_hook


def run(net_mode=False, wrong_master=False, missing=False):
    name = 'u.g_ask[1].r[1][3]$_DFF_P_' if net_mode else '_5406_'
    net = 'u.g_ask[1].r[1][3]'
    raw_name = name.replace('.', '\\.').replace('[', '\\[').replace(']', '\\]') if net_mode else name
    raw_net = net.replace('.', '\\.').replace('[', '\\[').replace(']', '\\]')
    before, after = ('DFF_X1','DFF_X2') if net_mode else ('MUX2_X1','MUX2_X2')
    replacement = [name, before, after]+([net] if net_mode else [])
    changes = []
    with tempfile.TemporaryDirectory() as directory:
        flow = Path(directory)/'flow'
        flow.mkdir()
        t = tkinter.Tcl()
        t.eval('namespace eval ord {}; namespace eval sta {}')
        t.setvar('env(WORK_HOME)', str(flow))
        t.createcommand('ord::get_db_block', lambda:'block')
        def block(method, *args):
            if method=='findNet': return 'NULL'
            if method=='getNets': return () if missing else ('net',)
            if method=='findInst': return 'inst' if args[0]==name and not missing else 'NULL'
            raise AssertionError(method)
        t.createcommand('block',block)
        t.createcommand('net',lambda method: raw_net if method=='getName' else ('iterm',))
        t.createcommand('iterm',lambda method:'OUTPUT' if method=='getIoType' else 'inst')
        t.createcommand('inst',lambda method:raw_name if method=='getName' else 'master')
        t.createcommand('master',lambda method:'wrong' if wrong_master else before)
        t.createcommand('sta::find_instance',lambda arg:'sta_inst' if arg==name else 'NULL')
        def replace(instance, cell):
            assert instance==name and cell==after
            changes.append((instance,cell))
            return 1
        t.createcommand('replace_cell',replace)
        t.createcommand('set_dont_touch',lambda arg:'' if arg=='sta_inst' else 1/0)
        t.createcommand('detailed_placement_helper',lambda:'')
        t.createcommand('check_placement',lambda *args:'')
        script = build_hook([replacement])
        assert t.call('info','complete',script)
        try:
            t.eval(script)
        except tkinter.TclError:
            if not (wrong_master or missing): raise
            assert not changes
        else:
            assert not wrong_master and not missing
            assert changes==[(name,after)]
        finally:
            t.eval('if {[info exists llhd_changes]} {catch {close $llhd_changes}}')
run()
run(net_mode=True)
run(net_mode=True, wrong_master=True)
run(net_mode=True, missing=True)
print('PASS: generated Tcl executes for direct and escaped bus names; missing and wrong-master targets fail before mutation')
