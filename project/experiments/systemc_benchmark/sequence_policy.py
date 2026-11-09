"""Keep diagnostic continuation separate from numerical qualification."""


def validate_resume(previous, identity, diagnostic):
    old_identity = {k: v for k, v in previous['identity'].items()
                    if k != 'decode_template_sha256'}
    if old_identity != identity:
        raise ValueError('resume identity changed')
    if not previous['HF_model_source_unchanged'] or not previous['source_artifact_size_mtime_unchanged']:
        raise ValueError('resume source drift')
    if not previous['batch_numeric_passed'] and not diagnostic:
        raise ValueError('previous batch failed; only explicit diagnostic continuation is allowed')


def sequence_passed(batch_passed, ancestry):
    return bool(batch_passed and all(row['numeric_passed'] for row in ancestry))
