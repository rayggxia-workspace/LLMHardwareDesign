"""Render the maintained control-plan Markdown to its stable PDF companion."""
import argparse
import hashlib
import html
import math
import pathlib
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,KeepTogether


def inline(text):
    text=html.escape(text)
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:'<link href="'+m[2].replace('&amp;','&amp;')+'" color="#126087">'+m[1]+'</link>',text)
    text=re.sub(r'`([^`]+)`',r'<font color="#214c60">\1</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'\1',text)
    return text.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True,type=pathlib.Path)
    p.add_argument('--output',required=True,type=pathlib.Path)
    p.add_argument('--font-dir',required=True,type=pathlib.Path)
    a=p.parse_args()
    pdfmetrics.registerFont(TTFont('CN',str(a.font_dir/'Deng.ttf')))
    pdfmetrics.registerFont(TTFont('CNB',str(a.font_dir/'Dengb.ttf')))
    pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNB',italic='CN',boldItalic='CNB')
    source=a.input.read_bytes(); digest=hashlib.sha256(source).hexdigest()
    text=source.decode('utf-8'); lines=text.splitlines()
    navy=colors.HexColor('#173c50'); light=colors.HexColor('#edf3f6')
    body=ParagraphStyle('body',fontName='CN',fontSize=9,leading=14,spaceAfter=6,wordWrap='CJK',splitLongWords=True)
    cell=ParagraphStyle('cell',parent=body,fontSize=7.5,leading=10.7,spaceAfter=0)
    head=ParagraphStyle('thead',parent=cell,fontName='CNB',textColor=colors.white)
    h1=ParagraphStyle('h1',parent=body,fontName='CNB',fontSize=20,leading=27,textColor=navy,spaceAfter=15,keepWithNext=True)
    h2=ParagraphStyle('h2',parent=body,fontName='CNB',fontSize=13.5,leading=19,textColor=navy,spaceBefore=14,spaceAfter=8,keepWithNext=True)
    h3=ParagraphStyle('h3',parent=h2,fontSize=11,leading=16,spaceBefore=10)
    code=ParagraphStyle('code',parent=body,fontSize=7.5,leading=10.5,backColor=light,borderPadding=5,spaceAfter=3)
    bullet=ParagraphStyle('bullet',parent=body,leftIndent=14,firstLineIndent=0,bulletIndent=1,bulletFontName='CN',bulletFontSize=9)
    story=[]; i=0; table_count=0
    width=A4[0]-80
    def paragraph(s,style=body): return Paragraph(inline(s),style)
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1; continue
        if line.startswith('```'):
            block=[]; i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i]); i+=1
            i+=1
            for item in block:
                if item.strip(): story.append(Paragraph(html.escape(item).replace('  ','&#160;&#160;'),code))
                else: story.append(Spacer(1,4))
            story.append(Spacer(1,5)); continue
        heading=re.match(r'^(#{1,6})\s+(.*)',line)
        if heading:
            story.append(paragraph(heading[2],h1 if len(heading[1])==1 else h2 if len(heading[1])==2 else h3))
            i+=1; continue
        if line.startswith('|') and i+1<len(lines) and re.match(r'^\|[\s:|\-]+\|$',lines[i+1].strip()):
            raw=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=lines[i].strip().strip('|')
                values=re.split(r'(?<!\\)\|',row)
                if not all(re.fullmatch(r'[\s:\-]+',v) for v in values): raw.append([v.strip().replace('\\|','|') for v in values])
                i+=1
            n=len(raw[0]); assert all(len(row)==n for row in raw),'inconsistent Markdown table columns'
            weights=[min(90,max(12,max(len(row[c]) for row in raw))) for c in range(n)]
            available=width-30*n
            widths=[30+available*w/sum(weights) for w in weights]
            data=[[paragraph(v,head if r==0 else cell) for v in row] for r,row in enumerate(raw)]
            table=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),0.6,navy),('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#ccd9df')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,9)]); table_count+=1; continue
        item=re.match(r'^(?:[-*]\s+|(\d+)\.\s+)(.*)',line)
        if item:
            story.append(Paragraph(inline(item[2]),bullet,bulletText=(item[1]+'.') if item[1] else '-'))
            i+=1; continue
        block=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|[-*]\s|\d+\.\s)',lines[i].strip()):
            block.append(lines[i].strip()); i+=1
        story.append(paragraph(' '.join(block)))
    def decorate(canvas,doc):
        canvas.saveState(); canvas.setFont('CN',7.5); canvas.setFillColor(colors.HexColor('#647b87'))
        canvas.drawString(40,A4[1]-24,'Block 组网与母控 / 局控综合方案')
        canvas.line(40,A4[1]-30,A4[0]-40,A4[1]-30)
        canvas.drawString(40,19,'Markdown SHA-256: '+digest[:20])
        canvas.drawRightString(A4[0]-40,19,'第 '+str(doc.page)+' 页')
        canvas.restoreState()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(a.output),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=44,bottomMargin=37,
        title='Block组网与母控局控综合方案',author='Melodydt',subject='Issue179 / PR180; source SHA-256 '+digest)
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    print('PDF rendered:',a.output,'tables=',table_count,'source_sha256=',digest)


if __name__=='__main__': main()
