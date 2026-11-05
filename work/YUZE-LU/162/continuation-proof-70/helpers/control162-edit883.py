from pathlib import Path
p=Path('project/experiments/control_v1/weighted_bidir_regression.py');s=p.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,a;s=s.replace(a,z,1)
sub('native=False, pin="none"):', 'native=False, pin="none", native_maze=0):')
sub("folder = out / (('native-'+pin+'-' if native else '')", "folder = out / (('nativemaze%d-'%native_maze if native_maze else '') + ('native-'+pin+'-' if native else '')")
sub('pin_access_policy=pin)', 'pin_access_policy=pin,native_zero_maze_budget=native_maze)')
sub("        if native:\n", """        if native_maze:
            assert proof['native_zero_maze_budget']==native_maze
            xs=proof['native_prefix_proof']['zero_maze_trace'];assert xs
            assert sum(r['native_zero_maze_hits']for r in xs)>0
            for r in xs:
                assert 0<=r['native_zero_maze_hits']<=r['native_zero_maze_attempts']
                assert 0<=r['native_zero_maze_wire_rejected']<=r['native_zero_maze_attempts']-r['native_zero_maze_hits']
                assert r['native_zero_maze_expanded']<=native_maze*r['native_zero_maze_attempts']
        if native:
""")
sub('native=native,pin=pin,','native=native,pin=pin,native_maze=native_maze,')
sub("    assert len(rows)==57\n    first", """    assert len(rows)==57
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        rows+=list(pool.map(lambda pair:case((256,1,pair[0],2,1),escape=True,maze=16384,native=True,pin='all',native_maze=pair[1]),
                           [(mode,budget)for mode in range(3)for budget in (16384,65536)]))
    assert len(rows)==63
    first""")
a='    return dict(passed=True, cases=rows,'
sub(a,r'''    for label,flags in [('native-maze-context',['--critical-first','--native-zero-maze=16384']),
                        ('native-maze-duplicate',['--native-prefix-first','--native-zero-maze=16384','--native-zero-maze=65536']),
                        ('native-maze-unsupported',['--native-prefix-first','--native-zero-maze=8192'])]:
        target=out/('invalid-'+label)
        result=subprocess.run([str(first/'router'),str(good),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        rejected.append(dict(case=label,returncode=result.returncode,stderr=result.stderr.decode(),rejected=True))
    folder=out/'invalid-python-native-maze';folder.mkdir()
    try:route({'net':[(6,6),(10,10)]},24,24,162,10,folder,native_zero_maze_budget=16384)
    except AssertionError:
        assert not list(folder.iterdir());rejected.append(dict(case='python-native-maze-context',rejected=True))
    else:raise AssertionError('Invalid native zero-maze context accepted')
    negative=out/'native-maze-over-wire-input.txt';negative.write_text('24 24 1 162 2 256 1 1 1 1 1 0 0 1 0 2 1\nweak 2 6 6 10 6 3\n')
    target=out/'native-maze-over-wire-output.txt'
    result=subprocess.run([str(first/'router'),str(negative),str(target),'--critical-first','--native-prefix-first','--native-zero-maze=16384'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode!=0 and not target.exists()
    assert b'disconnected finite-resource tree'in result.stderr,'Over-budget zero candidate did not yield to original finite-resource search'
    rejected.append(dict(case='native-maze-over-wire-candidate-falls-back',returncode=result.returncode,stderr=result.stderr.decode(),rejected=True,original_finite_resource_failure=True,no_final_output=True))
    assert len(rejected)==40
    return dict(passed=True, cases=rows,''')
s=s.replace("scope='All57 actual", "scope='All63 actual").replace('All previous51 cases retained','All previous57 cases retained').replace('35 invalid/failing contexts rejected','40 invalid/failing contexts rejected').replace('All features default off;', 'Six additional native-zero16384/65536 cases enforce expansion and original wire limits; a too-long zero candidate must yield to the unchanged original finite-resource failure with no final output. All features default off;')
p.write_bytes(s.encode())
