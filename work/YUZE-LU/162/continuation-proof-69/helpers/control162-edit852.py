from pathlib import Path
p=Path('project/experiments/control_v1/weighted_bidir_regression.py');s=p.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,a;s=s.replace(a,z,1)
sub('escape=False, maze=0):','escape=False, maze=0, native=False, pin="none"):')
sub("folder = out / (('maze%d-'%maze if maze else '')", "folder = out / (('native-'+pin+'-' if native else '') + ('maze%d-'%maze if maze else '')")
sub('ordinary_zero_maze_budget=maze)', 'ordinary_zero_maze_budget=maze,native_prefix_first=native,pin_access_policy=pin)')
sub("        if margin:\n            assert proof['weighted_pair_margin'] == margin", """        if native:
            assert proof['native_prefix_proof']['frozen_prefix_matches_full_route']
            assert proof['native_prefix_proof']['stage']['frozen_nets']==2
            plan=json.loads(Path(str(folder/'router-output.txt')+'.pin-access.json').read_text())
            if pin=='all':assert plan['assigned']==plan['terminals']
            # Validate every proposed physical exit independently, including
            # foreign M11 ownership and cross-net proxy reservations.
            owners={y*48+x:n for n,ends in enumerate(terminals.values()) for x,y in ends}
            reservation={}
            for n,v,w in plan['plan']:
                assert v in {y*48+x for x,y in list(terminals.values())[n]}
                x,y=w%48,w//48;vx,vy=v%48,v//48
                assert 4<=x<44 and 4<=y<44 and (x+y)%2==0
                assert abs(x-vx)+abs(y-vy) in (0,1)
                if v!=w:assert owners.get(w,n)==n
                for node in ([w,w+48*48]if v!=w else[w+48*48]):
                    assert reservation.setdefault(node,n)==n
        if margin:
            assert proof['weighted_pair_margin'] == margin
""")
sub('escape=escape, maze=maze,','escape=escape, maze=maze,native=native,pin=pin,')
sub("    first = out/'weight32-scale1-mode0-cost2-pattern0'", """    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        rows+=list(pool.map(lambda pair:case((256,1,pair[0],2,1),escape=True,maze=16384,native=True,pin=pair[1]),
                           [(mode,pin)for mode in range(3)for pin in ('all','after-native')]))
    assert len(rows)==57
    first = out/'weight32-scale1-mode0-cost2-pattern0'""")
sub('    return dict(passed=True, cases=rows,',r'''    for label,flags in [('native-missing-context',['--native-prefix-first']),
                        ('native-duplicate',['--native-prefix-first','--native-prefix-first']),
                        ('pin-missing-native',['--pin-access=all']),
                        ('pin-duplicate',['--native-prefix-first','--pin-access=all','--pin-access=after-native']),
                        ('pin-unsupported',['--native-prefix-first','--pin-access=greedy'])]:
        target=out/('invalid-'+label)
        result=subprocess.run([str(first/'router'),str(good),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        rejected.append(dict(case=label,returncode=result.returncode,stderr=result.stderr.decode(),rejected=True))
    for label,kwargs in [('native-python-context',dict(native_prefix_first=True)),('pin-python-context',dict(pin_access_policy='all'))]:
        folder=out/label;folder.mkdir()
        try:route({'net':[(6,6),(10,10)]},24,24,162,10,folder,**kwargs)
        except AssertionError:
            assert not list(folder.iterdir());rejected.append(dict(case=label,rejected=True))
        else:raise AssertionError('Invalid native/pin Python context accepted')
    # Native zero conflicts must never produce success/output for an unroutable
    # full graph. The victim landing has four foreign fixed M11 neighbours.
    negative=out/'native-pass-global-fail-input.txt'
    negative.write_text('26 26 6 162 20 256 1 1 1 1 1 0 0 1 0 2 1\n'
                        'weak 2 6 6 8 6 8\nvictim 2 13 12 18 18 -1\n'
                        'a0 2 12 12 6 18 -1\na1 2 14 12 8 18 -1\n'
                        'a2 2 13 11 10 18 -1\na3 2 13 13 12 18 -1\n')
    target=out/'native-pass-global-fail-output.txt'
    failed=subprocess.run([str(first/'router'),str(negative),str(target),'--critical-first','--native-prefix-first','--pin-access=none'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert failed.returncode!=0 and not target.exists()
    stages=[json.loads(l)for l in failed.stdout.decode().splitlines()if l.startswith('{')]
    assert sum(x.get('native_prefix_stage_passed')is True for x in stages)==1
    assert 'blocks an ordinary terminal'in failed.stderr.decode()
    prefix_log=Path(str(target)+'.native-prefix.log')
    native_rows=[json.loads(l)for l in prefix_log.read_text().splitlines()if l.startswith('{')]
    assert [x for x in native_rows if 'conflict_nodes'in x][-1]['conflict_nodes']==0
    rejected.append(dict(case='native-pass-global-fail',returncode=failed.returncode,stderr=failed.stderr.decode(),
                         native_prefix_passed=True,full_graph_failed=True,no_final_output=True,rejected=True))
    assert len(rejected)==35
    return dict(passed=True, cases=rows,''')
s=s.replace("scope='All51 actual", "scope='All57 actual").replace("All previous45 cases retained", "All previous51 cases retained").replace('27 invalid contexts rejected.', '35 invalid/failing contexts rejected, including native-pass/global-fail. Six native-first/all or after-native pin-reservation cases independently verify frozen prefix equality, real pin ownership, parity and full zero-conflict edges/flood/wire checks.200 additional matching checks per binary use an independent exhaustive small-resource oracle.')
p.write_bytes(s.encode())
