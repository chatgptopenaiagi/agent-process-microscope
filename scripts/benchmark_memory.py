"""Small reproducible local benchmark, synthetic records explicitly labelled."""
import json
from pathlib import Path
import sys
import time
from uuid import uuid4
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apm.core.events import Normalizer
from apm.storage.memory import Memory


def main():
    path = ROOT / 'reports' / ('memory-bench-' + str(uuid4()) + '.sqlite3')
    normalizer = Normalizer(str(uuid4()), 'synthetic-benchmark')
    stream = str(uuid4())
    process = psutil.Process()
    cpu_start = process.cpu_times()
    latencies = []
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if not 1 <= batch_size <= 32:
        raise ValueError('batch_size 1..32')
    started = time.perf_counter()
    with Memory(path) as memory:
        for start in range(1, 1001, batch_size):
            batch = []
            for seq in range(start, min(start+batch_size, 1001)):
                event = normalizer.normalize(dict(source='benchmark',category='command',action='STOP',
                    target='SYNTHETIC benchmark',status='synthetic',interpretation_level='synthetic',metadata={'exit_code':0}))
                batch.append(dict(event=event.to_dict(), stream=stream, sequence=seq))
            tick = time.perf_counter()
            memory.append_batch(batch)
            latencies.append(time.perf_counter()-tick)
        elapsed = time.perf_counter()-started
        tick = time.perf_counter(); result = memory.investigate(normalizer.session_id)
        query_ms = (time.perf_counter()-tick)*1000
        integrity = memory.verify()
        assert integrity['ok'] and integrity['records']==1000
    cpu_end = process.cpu_times()
    report = dict(label='SYNTHETIC 1000-record single-process benchmark; not agent overhead certification',
        records=1000, elapsed_seconds=elapsed, records_per_second=1000/elapsed,
        batch_size=batch_size, append_batch_p95_ms=sorted(latencies)[int((len(latencies)-1)*.95)]*1000, query_last_100_ms=query_ms,
        cpu_seconds=(cpu_end.user+cpu_end.system)-(cpu_start.user+cpu_start.system),
        rss_bytes=process.memory_info().rss, database_bytes=path.stat().st_size, wal_mode=True,
        synchronous='FULL', filesystem=str(path.parent), records_examined=result['inspected'])
    path.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
