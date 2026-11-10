"""Lossless-content Markdown to Chinese PDF export; no new research claims."""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, KeepTogether,
)
from pypdf import PdfReader
import pdfplumber

ROOT = Path(r'D:/Study_material/Study_material/LLMHardwareDesign')
PARSER = argparse.ArgumentParser()
PARSER.add_argument('--source', type=Path, required=True)
PARSER.add_argument('--output', type=Path, required=True)
PARSER.add_argument('--qa-dir', type=Path, required=True)
PARSER.add_argument('--source-url', required=True)
PARSER.add_argument('--source-commit', required=True)
PARSER.add_argument('--artifact-marker', default='ee740f')
PARSER.add_argument('--compact-table-sections', type=int, nargs='*', default=[])
PARSER.add_argument('--title', default='LLMHardwareDesign | Issue247 优化总览与性能')
ARGS = PARSER.parse_args()
SOURCE = ARGS.source.resolve()
OUT = ARGS.output.resolve()
HERE = ARGS.qa_dir.resolve()
COMMIT = ARGS.source_commit
FROZEN_SHA = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
SOURCE_URL = ARGS.source_url
assert re.fullmatch('[0-9a-f]{40}', COMMIT)
TITLE = ARGS.title
FOOTER = f'RTL与条件评估分列 | 文档源 {FROZEN_SHA[:12]}'
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BOLD = Path('C:/Windows/Fonts/msyhbd.ttc')
CODE = Path('C:/Windows/Fonts/simsun.ttc')
PWIDTH, PHEIGHT = A4
LEFT, RIGHT, TOP, BOTTOM = 43, 43, 51, 46
WIDTH = PWIDTH-LEFT-RIGHT
INK = colors.HexColor('#172B3A')
MUTED = colors.HexColor('#516776')
BLUE = colors.HexColor('#165478')
LINE = colors.HexColor('#C9D6DF')
PALE = colors.HexColor('#F0F5F8')
DASHES = str.maketrans({'\u2010':'-', '\u2011':'-', '\u2012':'-',
                       '\u2013':'-', '\u2014':'-', '\u2212':'-',
                       '\u2500':'-', '\u2510':'+', '\u251c':'+', '\u2518':'+'})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(text):
    return text.translate(DASHES)


def plain(text):
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1',text)
    return clean(text.replace('**','').replace('`',''))


def markup(text):
    text = clean(text)
    pattern = r'(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*)'
    out=[]
    for piece in re.split(pattern,text):
        if not piece: continue
        if piece.startswith('['):
            match=re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)',piece)
            if match:
                label,destination=match.groups()
                target=destination if '://' in destination else urljoin(SOURCE_URL,destination)
                out.append('<link href="'+html.escape(target,quote=True)+'" color="#165478"><u>'+html.escape(label)+'</u></link>')
                continue
        if piece.startswith('`') and piece.endswith('`'):
            out.append('<font name="CJKCode" color="#274A60">'+html.escape(piece[1:-1])+'</font>')
        elif piece.startswith('**') and piece.endswith('**'):
            out.append('<b>'+html.escape(piece[2:-2])+'</b>')
        else:
            out.append(html.escape(piece))
    return ''.join(out)


class Document(BaseDocTemplate):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.heading_index=0
        frame=Frame(LEFT,BOTTOM,WIDTH,PHEIGHT-TOP-BOTTOM,
                    leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='normal',frames=[frame],onPage=self.decorate))

    def decorate(self,canvas,doc):
        canvas.saveState()
        canvas.setFont('CJK',8)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT,PHEIGHT-30,TITLE)
        canvas.setStrokeColor(LINE)
        canvas.line(LEFT,PHEIGHT-37,PWIDTH-RIGHT,PHEIGHT-37)
        canvas.line(LEFT,33,PWIDTH-RIGHT,33)
        canvas.setFont('CJK',7.5)
        canvas.drawString(LEFT,21,FOOTER)
        canvas.drawRightString(PWIDTH-RIGHT,21,str(doc.page))
        canvas.restoreState()

    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name in ('Title','Section'):
            self.heading_index+=1
            key='heading-'+str(self.heading_index)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,
                level=0 if flowable.style.name=='Title' else 1,closed=False)


def main():
    assert digest(SOURCE)==FROZEN_SHA,'source changed during PDF export'
    HERE.mkdir(parents=True,exist_ok=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('CJK',str(FONT),subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CJKBold',str(BOLD),subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CJKCode',str(CODE),subfontIndex=0))
    pdfmetrics.registerFontFamily('CJK',normal='CJK',bold='CJKBold',italic='CJK',boldItalic='CJKBold')
    styles={
        'body':ParagraphStyle('Body',fontName='CJK',fontSize=9.3,leading=15,
            textColor=INK,spaceAfter=8,rightIndent=11,wordWrap='CJK',splitLongWords=1,allowWidows=0,allowOrphans=0),
        'title':ParagraphStyle('Title',fontName='CJKBold',fontSize=20,leading=29,
            textColor=INK,spaceAfter=15,keepWithNext=True,wordWrap='CJK'),
        'section':ParagraphStyle('Section',fontName='CJKBold',fontSize=15,leading=22,
            textColor=BLUE,spaceBefore=4,spaceAfter=13,keepWithNext=True,wordWrap='CJK'),
        'sub':ParagraphStyle('Subsection',fontName='CJKBold',fontSize=11.2,leading=17,
            textColor=BLUE,spaceBefore=8,spaceAfter=6,keepWithNext=True,wordWrap='CJK'),
        'cell':ParagraphStyle('Cell',fontName='CJK',fontSize=8.3,leading=13,
            textColor=INK,spaceAfter=0,wordWrap='CJK',splitLongWords=1),
        'head':ParagraphStyle('CellHead',fontName='CJKBold',fontSize=8.7,leading=13,
            textColor=colors.white,wordWrap='CJK'),
        'meta':ParagraphStyle('Metadata',fontName='CJK',fontSize=7.7,leading=12,
            textColor=MUTED,spaceAfter=3,wordWrap='CJK',splitLongWords=1),
        'code':ParagraphStyle('Code',fontName='CJKCode',fontSize=8.7,leading=13,
            textColor=INK,spaceAfter=0),
    }
    source=SOURCE.read_text(encoding='utf-8')
    lines=source.splitlines()
    story=[]; units=[]; stats={'h1':0,'h2':0,'h3':0,'paragraphs':0,'tables':0,'table_rows':0,'code_blocks':0,'list_items':0}

    def paragraph(text,kind='body',record=True):
        if record: units.append({'kind':kind,'text':plain(text)})
        return Paragraph(markup(text),styles[kind])

    i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1; continue
        if line.strip() == '<!-- pagebreak -->':
            story.append(PageBreak()); i += 1; continue
        if line.startswith('# '):
            stats['h1']+=1
            story.append(paragraph(line[2:],'title'))
            metadata=[
                '文档来源 commit：'+COMMIT,
                '源文档 SHA-256：'+FROZEN_SHA,
                '原文与链接：[查看固定版本来源]('+SOURCE_URL+')',
                '口径说明：吞吐沿用旧体系的条件估计；RTL功能、局部实测、面积证据与整图条件结果分别报告。',
            ]
            box=Table([[paragraph(x,'meta',False)] for x in metadata],colWidths=[WIDTH-18])
            box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),
                ('BOX',(0,0),(-1,-1),0.5,LINE),('LEFTPADDING',(0,0),(-1,-1),9),
                ('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),3),
                ('BOTTOMPADDING',(0,0),(-1,-1),3)]))
            story.extend([box,Spacer(1,13)]);i+=1;continue
        if line.startswith('## '):
            stats['h2']+=1
            # Keep the three implementation themes and results easy to find,
            # while allowing short continuation/conclusion pages to share space.
            story.append(paragraph(line[3:],'section'));i+=1;continue
        if line.startswith('### '):
            stats['h3']+=1;story.append(paragraph(line[4:],'sub'));i+=1;continue
        if line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]);i+=1
            assert i<len(lines),'unterminated code fence'
            text=clean('\n'.join(code));units.append({'kind':'code','text':text})
            max_line=max(pdfmetrics.stringWidth(x,'CJKCode',1) for x in text.splitlines())
            size=min(8.7,(WIDTH-22)/max_line)
            assert size>=7,'code would become unreadable'
            style=ParagraphStyle('CodeSized',parent=styles['code'],fontSize=size,leading=size*1.48)
            block=Preformatted(text,style)
            box=Table([[block]],colWidths=[WIDTH])
            box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),
                ('BOX',(0,0),(-1,-1),0.5,LINE),('LEFTPADDING',(0,0),(-1,-1),11),
                ('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),8),
                ('BOTTOMPADDING',(0,0),(-1,-1),8)]))
            story.extend([box,Spacer(1,10)]);stats['code_blocks']+=1;i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                raw=lines[i].strip().strip('|').split('|');i+=1
                if all(re.fullmatch(r'\s*:?-+:?\s*',c) for c in raw):continue
                rows.append([c.strip() for c in raw])
            columns=len(rows[0]);assert all(len(row)==columns for row in rows)
            if columns==2: widths=[WIDTH*.54,WIDTH*.46]
            elif columns==3:widths=[WIDTH*.30,WIDTH*.35,WIDTH*.35]
            elif columns==4:widths=[WIDTH*.34,WIDTH*.22,WIDTH*.22,WIDTH*.22]
            elif columns==5:widths=[WIDTH*.32,WIDTH*.17,WIDTH*.17,WIDTH*.17,WIDTH*.17]
            else:raise ValueError('unsupported table')
            table=[]
            for n,row in enumerate(rows):
                table.append([paragraph(cell,'head' if n==0 else 'cell') for cell in row])
            t=Table(table,colWidths=widths,repeatRows=1,hAlign='LEFT')
            # Compact data tables preserve readable text size and keep their
            # interpretation on the same page in dense comparison sections.
            padding = 3 if stats['h2'] in ARGS.compact_table_sections else 6
            commands=[('BACKGROUND',(0,0),(-1,0),BLUE),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('GRID',(0,0),(-1,-1),0.35,LINE),('LEFTPADDING',(0,0),(-1,-1),7),
                ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),padding),
                ('BOTTOMPADDING',(0,0),(-1,-1),padding)]
            for n in range(1,len(rows)):
                if n%2==0:commands.append(('BACKGROUND',(0,n),(-1,n),colors.HexColor('#F5F8FA')))
            t.setStyle(TableStyle(commands));story.extend([t,Spacer(1,11)])
            stats['tables']+=1;stats['table_rows']+=len(rows);continue
        if re.match(r'^(\d+\. |- )',line):
            stats['list_items']+=1
            story.append(paragraph(line))
            i+=1;continue
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|\d+\. |- )',lines[i]):
            para.append(lines[i]);i+=1
        story.append(paragraph(' '.join(para)));stats['paragraphs']+=1

    doc=Document(str(OUT),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,
        topMargin=TOP,bottomMargin=BOTTOM,title=TITLE,
        author='Melodydt · LLMHardwareDesign',subject='Issue247 / PR243 已实施优化总览与最新旧体系性能',
        pageCompression=1)
    doc.build(story)
    reader=PdfReader(str(OUT))
    extracted=[]; bounds=[]; missing=[]
    with pdfplumber.open(str(OUT)) as pdf:
        for number,page in enumerate(pdf.pages,1):
            # Remove only the known repeated page furniture before content audit.
            raw=page.extract_text(x_tolerance=1.5,y_tolerance=3) or ''
            filtered=[]
            for line in raw.splitlines():
                if line.startswith('LLMHardwareDesign | Issue247'):continue
                if line.startswith('RTL与条件评估分列'):continue
                filtered.append(line)
            extracted.append('\n'.join(filtered))
            chars=[c for c in page.chars if c['text'].strip()]
            box={'page':number,'x0':min(c['x0'] for c in chars),'x1':max(c['x1'] for c in chars),
                 'top':min(c['top'] for c in chars),'bottom':max(c['bottom'] for c in chars)}
            assert box['x0']>=LEFT-1 and box['x1']<=PWIDTH-RIGHT+1,box
            assert box['top']>=10 and box['bottom']<=PHEIGHT-10,box
            bounds.append(box)
    compact=lambda x: re.sub(r'\s+','',x)
    # pypdf keeps each table cell together; pdfplumber is separately used for
    # character bounding boxes and the page text artifact.
    body_pages=[]
    for number,page in enumerate(reader.pages,1):
        page_lines=(page.extract_text() or '').splitlines()
        # The canvas decorator emits exactly these three items before content.
        # Do not drop arbitrary numeric lines: table cells such as 0 are data.
        assert page_lines[:3]==[TITLE,FOOTER,str(number)],page_lines[:3]
        body_pages.append('\n'.join(page_lines[3:]))
    text='\n'.join(body_pages)
    normalized=compact(text)
    cursor=0
    for index,unit in enumerate(units):
        wanted=compact(unit['text'])
        position=normalized.find(wanted,cursor)
        if position<0:missing.append({'index':index,'kind':unit['kind'],'text':unit['text'],'cursor':cursor,'global_position':normalized.find(wanted),'previous_units':units[max(0,index-4):index]})
        else:cursor=position+len(wanted)
    assert not missing,'content audit failed '+repr(missing[:4])
    links=[]
    for page in reader.pages:
        for a in page.get('/Annots',[]):
            v=a.get_object();action=v.get('/A',{})
            if action.get('/URI'):links.append(action['/URI'])
    assert SOURCE_URL in links
    source_links=re.findall(r'\[([^\]]+)\]\(([^)]+)\)',source)
    for _,target in source_links:
        expected=target if '://' in target else urljoin(SOURCE_URL,target)
        assert expected in links,expected
    glyphs=set(pdfmetrics.getFont('CJK').face.charToGlyph)
    unsupported=sorted(set(c for u in units for c in u['text'] if ord(c)>32 and ord(c) not in glyphs))
    assert not unsupported,unsupported
    qa={'source_file':str(SOURCE),'source_commit':COMMIT,'source_sha256':FROZEN_SHA,
        'pdf_file':str(OUT),'pdf_sha256':digest(OUT),'pages':len(reader.pages),'stats':stats,
        'audited_content_units':len(units),'missing_content_units':missing,
        'source_links':len(source_links),'pdf_link_annotations':len(links),
        'all_source_links_preserved':True,'page_character_bounds':bounds,
        'unsupported_characters':unsupported,'font_files_sha256':{str(p):digest(p) for p in [FONT,BOLD,CODE]},
        'ascii_dash_normalization':'Unicode hyphens/minus to ASCII hyphen; code box lines/corners to -/+; arrows unchanged',
        'artifact_marker':{'successful_executions':1,'exec_chunk_id':ARGS.artifact_marker,'exit_code':0},
        'visual_review':'pending; render every page before delivery'}
    (HERE/'extracted-text.txt').write_text('\n\n'.join(extracted),encoding='utf-8')
    (HERE/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'content-units.json').write_text(json.dumps(units,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:qa[k] for k in ['pdf_file','pdf_sha256','pages','stats','audited_content_units']},ensure_ascii=False))


if __name__=='__main__':main()
