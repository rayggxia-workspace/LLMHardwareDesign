"""Bounded read-only SSH capture; reuse immutable Issue16 LEF bytes."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import zipfile
from evidence import (CAPTURE_SOURCES, HERE, ROOT, check_observation, config, encoded, git,
                      index, now, provenance, sha, validate_snapshot)


def program(cfg):
    request = {'root': cfg['allowed_root'], 'files': cfg['files'], 'limits': cfg['limits']}
    return 'REQUEST = ' + repr(request) + '\n' + r'''
import base64,datetime,getpass,hashlib,json,os,pathlib,socket,stat,sys
root=pathlib.Path(REQUEST['root']).resolve(strict=True)
rows=[]
total=0
for item in REQUEST['files']:
 requested=root/item['relative_path']; resolved=requested.resolve(strict=True)
 if root not in resolved.parents: raise RuntimeError('Path leaves declared attempt')
 with resolved.open('rb') as f:
  before=os.fstat(f.fileno())
  if not stat.S_ISREG(before.st_mode) or before.st_size>REQUEST['limits']['max_file_bytes']: raise RuntimeError('Unbounded source')
  data=f.read(REQUEST['limits']['max_file_bytes']+1); after=os.fstat(f.fileno())
 stamp=lambda s:[s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]
 if stamp(before)!=stamp(after) or len(data)!=before.st_size: raise RuntimeError('Source changed during read')
 total+=len(data)
 if total>REQUEST['limits']['max_total_bytes']: raise RuntimeError('Capture too large')
 rows.append(dict(name=item['name'],requested_path=str(requested),resolved_path=str(resolved),bytes=len(data),
  sha256=hashlib.sha256(data).hexdigest(),stat_before=stamp(before),stat_after=stamp(after),base64=base64.b64encode(data).decode('ascii')))
print(json.dumps(dict(remote_user=getpass.getuser(),remote_hostname=socket.gethostname(),remote_python=sys.version,
 captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),observations=rows)))
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--identity', required=True)
    p.add_argument('--known-hosts', required=True)
    p.add_argument('--ssh', default='ssh')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.resolve().is_relative_to(ROOT):
        raise SystemExit('Use a NEW D-drive temporary capture directory outside the project')
    cfg_data = (HERE / 'inputs.json').read_bytes()
    cfg = config(cfg_data)
    prov = provenance(CAPTURE_SOURCES)
    script = program(cfg)
    argv = [a.ssh, '-F', 'NUL' if __import__('os').name == 'nt' else '/dev/null', '-T', '-i', a.identity,
            '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'PreferredAuthentications=publickey',
            '-o', 'ConnectTimeout=8', '-o', 'ConnectionAttempts=1', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UpdateHostKeys=no', '-o', 'UserKnownHostsFile=' + a.known_hosts, cfg['ssh_host'], 'python3 -B -']
    started = now()
    r = subprocess.run(argv, input=script.encode(), capture_output=True, check=True, timeout=90)
    response = json.loads(r.stdout)
    rows = response['observations']
    if response['remote_user'] != 'yuzelu' or len(rows) != 10 or {r['name'] for r in rows} != {x['name'] for x in cfg['files']}:
        raise AssertionError('Wrong SSH identity/file set')
    items = {x['name']: x for x in cfg['files']}
    files, observations = {}, []
    for row in rows:
        data = base64.b64decode(row['base64'], validate=True)
        check_observation(cfg, items[row['name']], row, data)
        files[row['name']] = data
        observations.append({k: v for k, v in row.items() if k != 'base64'})
    archive_bytes = (ROOT / cfg['lef16']['archive']).read_bytes()
    if sha(archive_bytes) != cfg['lef16']['archive_sha256']:
        raise AssertionError('Wrong source LEF16 archive')
    with zipfile.ZipFile(ROOT / cfg['lef16']['archive']) as archive:
        for name in ['ACT20.lef', 'MXU20.lef']:
            files[name] = archive.read('inputs/' + name)
        files['lef16-capture.json'] = archive.read('inputs/capture.json')
    files['inputs.json'] = cfg_data
    files['contract.json'] = (HERE / 'top-contract-completion.json').read_bytes()
    if git('status', '--porcelain') or git('rev-parse', 'HEAD') != prov['source_commit']:
        raise AssertionError('Source changed during capture')
    a.out.mkdir(parents=True)
    for name, data in files.items():
        path = a.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest = {'schema': 1, 'started_utc': started, 'finished_utc': now(), 'ssh_host': cfg['ssh_host'],
                **{k: v for k, v in response.items() if k != 'observations'}, 'observations': observations,
                'provenance': prov, 'config_sha256': sha(cfg_data), 'collector_sha256': sha(script.encode()),
                'reused_lef16_archive_sha256': sha(archive_bytes), 'files': index(a.out)}
    (a.out / 'capture.json').write_bytes(encoded(manifest))
    _, _, comparisons = validate_snapshot(a.out)
    print(json.dumps({'status': 'PASS', 'source_commit': prov['source_commit'], 'remote_files': len(rows),
                      'remote_bytes': sum(x['bytes'] for x in rows), 'producer_hash_comparisons': len(comparisons)}))


if __name__ == '__main__':
    main()
