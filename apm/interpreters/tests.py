from apm.core.state import test_runner


def interpret_test(event):
    if event.category not in ('command', 'process') or event.status in ('unavailable', 'synthetic'):
        return None
    runner = test_runner(event.metadata, event.target)
    if not runner:
        return None
    if event.action in ('START', 'EXECUTE', 'OPEN'):
        action, target = 'START', f'{runner} appears to be running'
    elif event.action == 'STOP' and isinstance(event.metadata.get('exit_code'), int):
        action = 'PASS' if event.metadata['exit_code'] == 0 else 'FAIL'
        target = f'{runner} command returned {event.metadata["exit_code"]}'
    else:
        return None
    return dict(source='test-interpreter', category='test', action=action, target=target,
                status='inferred', interpretation_level='inference', confidence=.8,
                raw_reference=event.event_id,
                metadata={'evidence_event_ids': [event.event_id], 'runner': runner,
                          'exit_code': event.metadata.get('exit_code'),
                          'note': 'Runner inferred from command; exit status is not an assertion count.'})
