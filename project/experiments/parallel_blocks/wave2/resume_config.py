"""Change only a verified checkpoint's route margin and destination paths."""
import re


def configure_resume(config, source, destination, margin):
    assert isinstance(margin, int) and not isinstance(margin, bool) and 0 <= margin < 100
    pattern = r'^(export CAP_MARGIN\s*=\s*)(\d+)[ \t]*$'
    matches = list(re.finditer(pattern, config, re.M))
    assert len(matches) == 1, 'Checkpoint config must declare one CAP_MARGIN'
    previous = int(matches[0][2])
    config = config.replace(str(source), str(destination))
    config = re.sub(pattern, lambda m:m[1]+str(margin), config, flags=re.M)
    return config, previous
