"""Render the frozen seven-model HTML report without recomputing its results."""
import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path

import reportlab
from bs4 import BeautifulSoup, NavigableString
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                               LongTable, TableStyle, KeepTogether)

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=REPO/'output/pdf/seven-model-speed-evaluation.pdf')
    parser.add_argument('--font', default='C:/Windows/Fonts/Deng.ttf')
    parser.add_argument('--bold-font', default='C:/Windows/Fonts/Dengb.ttf')
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('Deng', args.font))
    pdfmetrics.registerFont(TTFont('DengBold', args.bold_font))
    pdfmetrics.registerFontFamily('Deng', normal='Deng', bold='DengBold', italic='Deng', boldItalic='DengBold')
    navy, muted = colors.HexColor('#16324F'), colors.HexColor('#516579')
    base = dict(fontName='Deng', fontSize=10, leading=15, textColor=navy, wordWrap='CJK', spaceAfter=7)
    styles = {
        'p': ParagraphStyle('Body', **base),
        'h1': ParagraphStyle('Title', fontName='DengBold', fontSize=22, leading=29, textColor=navy, spaceAfter=12),
        'h2': ParagraphStyle('Heading', fontName='DengBold', fontSize=15, leading=21, textColor=navy, spaceBefore=8, spaceAfter=8, keepWithNext=True),
        'h3': ParagraphStyle('Subheading', fontName='DengBold', fontSize=11, leading=16, textColor=navy, spaceBefore=8, spaceAfter=5, keepWithNext=True),
        'cell': ParagraphStyle('Cell', fontName='Deng', fontSize=8.7, leading=12, textColor=navy, wordWrap='CJK'),
        'th': ParagraphStyle('HeaderCell', fontName='DengBold', fontSize=8.7, leading=12, textColor=navy, wordWrap='CJK'),
        'pre': ParagraphStyle('Code', fontName='Deng', fontSize=9, leading=14, textColor=navy, wordWrap='CJK', leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8, backColor=colors.HexColor('#EEF3F8'), borderPadding=8),
        'warning': ParagraphStyle('Warning', fontName='DengBold', fontSize=10, leading=15, textColor=colors.HexColor('#8B1A1A'), wordWrap='CJK'),
        'muted': ParagraphStyle('Muted', fontName='Deng', fontSize=8.2, leading=12, textColor=muted, wordWrap='CJK', spaceAfter=7),
    }
    styles['table_intro'] = ParagraphStyle('TableIntro', parent=styles['p'], keepWithNext=True)

    def normalize(s):
        return s.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('⚠', '注意：')

    def inline(node):
        if isinstance(node, NavigableString):
            return escape(normalize(str(node)))
        if node.name == 'br':
            return '<br/>'
        content = ''.join(inline(child) for child in node.children)
        if node.name in ('strong', 'b'):
            return '<b>'+content+'</b>'
        if node.name == 'a' and node.get('href', '').startswith('https://'):
            return '<a href="'+escape(node['href'], quote=True)+'" color="#1763A6">'+content+'</a>'
        return content

    width = A4[0] - 30*mm
    story = []
    counters = {'tables': 0, 'sections': 0, 'warning_boxes': 0}

    def process(node):
        if isinstance(node, NavigableString):
            return
        tag = node.name
        if tag in ('meta', 'style', 'title'):
            return
        if tag == 'section':
            story.append(PageBreak())
            counters['sections'] += 1
            for child in node.children:
                process(child)
        elif tag in ('h1', 'h2', 'h3', 'p'):
            style = 'muted' if 'muted' in node.get('class', []) else tag
            if tag == 'p' and node.get_text().startswith('以下是CALL'):
                style = 'table_intro'
            story.append(Paragraph(inline(node), styles[style]))
        elif tag == 'pre':
            text = escape(normalize(node.get_text())).replace('\n', '<br/>')
            story.append(Paragraph(text, styles['pre']))
        elif tag == 'div' and 'warning' in node.get('class', []):
            warning = LongTable([[Paragraph(inline(node), styles['warning'])]], colWidths=[width])
            warning.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF1E8')),
                ('BOX', (0, 0), (-1, -1), 1.1, colors.HexColor('#B6482B')),
                ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.extend([warning, Spacer(1, 9)])
            counters['warning_boxes'] += 1
        elif tag == 'table':
            rows = []
            for tr in node.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th'], recursive=False):
                    text = inline(td)
                    if counters['tables'] == 0:
                        text = {
                            '短P 输入tok/s': '短P 输入<br/>tok/s',
                            '估计P512主体 s': '估计P512<br/>主体 s',
                            '估计P512至logits s': '估计P512<br/>至logits s',
                            '估计输入tok/s（含尾部）': '估计输入<br/>tok/s<br/>（含尾部）',
                            '已有Decode tok/s': '已有<br/>Decode<br/>tok/s',
                            'Granite3.1-3B-A800M': 'Granite3.1-3B-<br/>A800M',
                        }.get(text, text)
                    cells.append(Paragraph(text, styles['th' if td.name == 'th' else 'cell']))
                rows.append(cells)
            count = len(rows[0])
            weights = [1]*count
            if count == 8 and counters['tables'] == 0:
                weights = [1.38, .92, .8, 1.05, 1.08, 1.08, .98, 1.28]
            elif count == 5:
                weights = [1.45, 1.05, .65, 1, 1]
            col_widths = [width*w/sum(weights) for w in weights]
            table = LongTable(rows, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E6EEF5')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FB')]),
                ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#C6D3DF')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.extend([table, Spacer(1, 10)])
            counters['tables'] += 1
        else:
            for child in node.children:
                process(child)

    html_path = ROOT/'seven-model-speed-report.html'
    html_bytes = html_path.read_bytes()
    soup = BeautifulSoup(html_bytes.decode('utf-8'), 'html.parser')
    process(soup)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=15*mm,
        rightMargin=15*mm, topMargin=17*mm, bottomMargin=16*mm,
        title='七模型速度仿真与512-token Prefill估算', author='Melodydt',
        subject='全层短Prefill、已有Decode与未独立验证的512-token条件估算')

    def chrome(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFont('Deng', 8)
        canvas.setFillColor(muted)
        canvas.drawString(15*mm, h-10*mm, '七模型速度评估 | Issue #291 / PR #292')
        canvas.drawRightString(w-15*mm, h-10*mm, '系统级 TLM / 512-bit SRAM / 三路 P')
        canvas.setStrokeColor(colors.HexColor('#D7E0E8'))
        canvas.line(15*mm, 12*mm, w-15*mm, 12*mm)
        canvas.drawString(15*mm, 7.5*mm, '512-token Prefill 为条件估算；独立序列验证暂缓。')
        canvas.drawRightString(w-15*mm, 7.5*mm, str(doc.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    receipt = dict(source_html_sha256=hashlib.sha256(html_bytes).hexdigest(),
        pdf_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        output=str(args.output.resolve()), reportlab=reportlab.Version, **counters)
    (ROOT/'pdf-build-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
