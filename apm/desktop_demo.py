"""Small offline onboarding fixture. No observation, providers or child processes."""
from pathlib import Path
from uuid import uuid4


def create_demo(destination):
    from apm.core.events import Normalizer
    from apm.storage.memory import Memory
    from apm.evidence.capsule import export_session
    from apm.holmes.journal import Journal
    directory = Path(destination)
    directory.mkdir(parents=True, exist_ok=False)
    database = directory / 'synthetic-source.sqlite3'
    case_id = str(uuid4())
    sessions = [str(uuid4()), str(uuid4())]
    with Memory(database) as memory:
        for session in sessions:
            normalizer, stream = Normalizer(session, 'synthetic-onboarding'), str(uuid4())
            for position, exit_code in enumerate((1, 0, 1), 1):
                event = normalizer.normalize(dict(source='codex', category='command', action='STOP',
                    status='synthetic', interpretation_level='synthetic', target='SYNTHETIC demonstration outcome',
                    metadata=dict(codex_event='item.completed', item_id='demo-command',
                                  comparison_key='demo-test', exit_code=exit_code)))
                memory.append(event.to_dict(), stream, position)
    capsules = []
    for n, session in enumerate(sessions, 1):
        path = directory / f'demonstration-{n}.apmcapsule'
        export_session(database, session, case_id, path)
        capsules.append(path)
    journal = directory / 'investigation.sqlite3'
    with Journal.create(journal):
        pass
    return dict(directory=directory, database=database, capsules=capsules, journal=journal, case_id=case_id)
