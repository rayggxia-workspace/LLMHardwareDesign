"""Guard the 30/40 route-only sweep against silent or duplicate overrides."""
from resume_config import configure_resume

source = 'export CLOCK = 2.5\nexport FILE = /source/elab.v\nexport CAP_MARGIN = 20\nexport IO_DELAY = 0.5\n'
for margin in (20, 30, 40):
    actual, previous = configure_resume(source, '/source', '/new', margin)
    assert previous == 20
    assert actual == source.replace('/source', '/new').replace('CAP_MARGIN = 20', 'CAP_MARGIN = '+str(margin))
for invalid in (source.replace('export CAP_MARGIN = 20\n', ''), source+'export CAP_MARGIN = 20\n'):
    try:
        configure_resume(invalid, '/source', '/new', 30)
    except AssertionError:
        pass
    else:
        raise AssertionError('Missing or duplicate config unexpectedly accepted')
for invalid in (True, -1, 100, '30'):
    try:
        configure_resume(source, '/source', '/new', invalid)
    except AssertionError:
        pass
    else:
        raise AssertionError('Invalid margin unexpectedly accepted')
print('PASS: route margin override is exact; missing/duplicate/invalid values rejected')
