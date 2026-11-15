"""Strict reader for the simple ANSI scalar/packed port declarations used here.

This is not a SystemVerilog elaborator. Generated connections are verified with
Verilator; unsupported declarations fail rather than guessing port widths.
"""
import re

def close(text,pos):
    level=1
    for i in range(pos+1,len(text)):
        level+=(text[i]=='(')-(text[i]==')')
        if not level:return i
    raise ValueError('unclosed parentheses')

def read(text):
    text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    m=re.search(r'\bmodule\s+(\w+)',text)
    if not m:raise ValueError('module absent')
    begin=text.index('(',m.end())
    if text[m.end():begin].strip()=='#':
        begin=text.index('(',close(text,begin)+1)
    header=text[begin+1:close(text,begin)]
    ports={};direction=None;shape='';signed=''
    for entry in header.split(','):
        entry=entry.strip()
        if not entry:continue
        d=re.match(r'(input|output|inout)\b\s*(.*)',entry,re.S)
        if d:
            direction=d[1];entry=d[2].strip();shape='';signed=''
            entry=re.sub(r'^(wire|logic|reg)\s+','',entry)
            if entry.startswith('signed '):signed='signed ';entry=entry[7:].strip()
            r=re.match(r'(\[[^\]]+\])\s*(.*)',entry,re.S)
            if r:shape=r[1]+' ';entry=r[2].strip()
        if not direction or not re.fullmatch(r'[A-Za-z_]\w*',entry):
            raise ValueError('unsupported ANSI declaration '+entry)
        if entry in ports:raise ValueError('duplicate port '+entry)
        ports[entry]={'direction':direction,'shape':shape,'signed':signed}
    return ports
