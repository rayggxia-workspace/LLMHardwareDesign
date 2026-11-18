"""Cross-check the rolling PDF's displayed values against its indexed JSON inputs."""

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform

from pypdf import PdfReader
from build_energy_report import COMPONENTS, WINDOWS, load_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('report-validation-v2.json'))
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    index = json.loads((directory / 'energy_report_models.json').read_bytes())
    if index.get('format') in ('arithmetic-v3','control-v4'):
        import subprocess
        import sys
        script='verify_control_report.py' if index.get('format')=='control-v4' else 'verify_arithmetic_report.py'
        subprocess.run([sys.executable, str(directory / script), str(args.pdf)], check=True)
        return
    reader = PdfReader(args.pdf)
    if len(reader.pages) != 19 or len(index['models']) != 7:
        raise ValueError('Unexpected v2 report structure')
    pages = [''.join(page.extract_text().split()) for page in reader.pages]
    counts = {'main_values': 0, 'component_values': 0, 'coverage_bridge_values': 0}

    def check(value, decimals, page, key):
        expected = format(value, '.' + str(decimals) + 'f')
        if expected not in page:
            raise ValueError('Displayed value missing: ' + key + ': ' + expected)
        counts[key] += 1

    for i, model in enumerate(index['models']):
        result = load_result(model, directory)
        page = pages[4 + 2 * i]
        if model['name'] not in page:
            raise ValueError('Wrong model page')
        for name in WINDOWS:
            row = result['windows'][name]
            for scope in ('covered_on_chip_subtotal', 'covered_subtotal'):
                for metric, decimals in (('energy_mj_per_token', 3), ('average_power_w', 4)):
                    for edge in row[scope][metric]:
                        check(edge, decimals, page, 'main_values')
            for keys in COMPONENTS.values():
                for edge in (0, 1):
                    value = sum(row['components'][k]['energy_mj_per_token'][edge] for k in keys)
                    check(value, 6, page, 'component_values')
        row = result['windows']['decode']
        for edge in (0, 1):
            new = row['covered_on_chip_subtotal']['energy_mj_per_token'][edge]
            added = row['newly_included_subtotal']['energy_mj_per_token'][edge]
            old = row['prior_with_wire_covered_on_chip_subtotal']['energy_mj_per_token'][edge]
            for value in (old, new - added, added, new):
                check(value, 3, pages[3], 'coverage_bridge_values')
    links = [str(a.get_object()['/A']['/URI']) for p in reader.pages for a in p.get('/Annots', [])
             if a.get_object().get('/A', {}).get('/URI')]
    if len(links) != 11 or not all(link.startswith('https://github.com/rayggxia-workspace/LLMHardwareDesign/') for link in links):
        raise ValueError('Unexpected report links')
    receipt = {
        'checked_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'python': platform.python_version(),
        'revision': index['revision'], 'evidence_commit': index['source_commit'],
        'pages': len(reader.pages), 'pdf_sha256': sha256(args.pdf.read_bytes()).hexdigest(),
        'index_sha256': sha256((directory / 'energy_report_models.json').read_bytes()).hexdigest(),
        'builder_sha256': sha256((directory / 'build_energy_report.py').read_bytes()).hexdigest(),
        'numeric_checks': counts, 'link_structure_checks': len(links), 'passed': True,
        'visual_review': 'Separate human/agent inspection required; this checker only validates extracted values and structure.'
    }
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=True))


if __name__ == '__main__':
    main()
