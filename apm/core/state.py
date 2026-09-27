"""Small evidence-linked state machine; workspace changes have no actor claim."""
from dataclasses import asdict, dataclass
import ntpath
import shlex


@dataclass(frozen=True)
class DerivedState:
    state: str = 'IDLE'
    summary: str = 'No observation session'
    event_ids: tuple = ()
    timestamp: str = ''
    confidence: float = 1.0
    interpretation_level: str = 'inference'
    status: str = 'inferred'

    def to_dict(self):
        return asdict(self)


def test_runner(metadata, target=''):
    argv = metadata.get('cmdline') or metadata.get('command_line') or metadata.get('command') or metadata.get('args') or target
    try:
        tokens = list(map(str, argv)) if isinstance(argv, (list, tuple)) else shlex.split(str(argv), posix=False)
    except ValueError:
        return None
    tokens = [token.strip('\"\'') for token in tokens]
    if tokens and tokens[0] == '&':
        tokens = tokens[1:]
    if not tokens:
        return None
    executable = ntpath.basename(tokens[0]).lower()
    for suffix in ('.exe', '.cmd', '.bat'):
        executable = executable.removesuffix(suffix)
    args = tokens[1:]
    if executable in ('pytest', 'py.test', 'ctest'):
        return 'pytest' if executable == 'py.test' else executable
    if executable.startswith('python') or executable == 'py':
        # Only a direct -m invocation, not text inside -c or a shell script.
        if args[:1] == ['-m'] and len(args) > 1 and args[1] in ('pytest', 'unittest'):
            return args[1]
    if executable == 'npm' and (args[:1] == ['test'] or args[:2] == ['run', 'test']):
        return 'npm test'
    if executable in ('cargo', 'dotnet') and args[:1] == ['test']:
        return executable + ' test'
    return None


class StateEngine:
    def __init__(self):
        self.current = DerivedState()
        self.active = {}

    def accept(self, event):
        state = None
        summary = ''
        confidence = event.confidence
        pid = event.metadata.get('pid', event.target)
        if event.category == 'session':
            state = 'IDLE' if event.action == 'STOP' else 'OBSERVING'
            summary = 'Observation ended' if event.action == 'STOP' else 'Watching external evidence'
            if event.action == 'STOP':
                self.active.clear()
        elif event.status == 'unavailable':
            state, summary = 'UNKNOWN', f'{event.source}: evidence unavailable'
        elif event.category in ('error',) or event.action == 'FAIL':
            state, summary = 'ERROR', f'{event.target}: failure reported'
        elif event.category == 'test':
            state = 'TESTING' if event.action in ('START', 'EXECUTE') else 'OBSERVING'
            summary = f'Test evidence: {event.target} {event.action.lower()}'
        elif event.category in ('command', 'process'):
            if event.action in ('START', 'EXECUTE', 'OPEN'):
                runner = test_runner(event.metadata, event.target)
                state = 'TESTING' if runner else ('OBSERVING' if event.action == 'OPEN' else 'EXECUTING')
                summary = f'{runner} appears to be running' if runner else f'Process observed: {event.target}'
                confidence = min(confidence, .8 if runner else 1.0)
                self.active[pid] = (state, summary)
            elif event.action == 'STOP':
                self.active.pop(pid, None)
                if event.metadata.get('exit_code') not in (None, 0):
                    state, summary = 'ERROR', f'Command returned exit code {event.metadata["exit_code"]}: {event.target}'
                elif self.active:
                    state, summary = list(self.active.values())[-1]
                else:
                    state, summary = 'OBSERVING', 'Process ended; awaiting further evidence'
        elif event.category in ('file', 'filesystem') and event.action in ('WRITE', 'CREATE', 'DELETE', 'RENAME'):
            state, summary = 'OBSERVING', f'Workspace changed: {event.target}; actor unverified'
        elif event.category == 'verification':
            state, summary = 'VERIFYING', f'Verification evidence: {event.target}'
        if state is None:
            return None
        if event.status == 'synthetic':
            summary = '[DEMO / SYNTHETIC] ' + summary
        self.current = DerivedState(state, summary, (event.event_id,), event.timestamp, confidence)
        return self.current
