"""Bounded in-process fan-out. The controller owns dispatch, never the UI."""
from queue import Queue, Empty, Full


class EventBus:
    def __init__(self, capacity=2048):
        self.queue = Queue(maxsize=capacity)
        self.subscribers = []
        self.dropped_count = 0

    def subscribe(self, consumer):
        self.subscribers.append(consumer)

    def publish(self, event):
        try:
            self.queue.put_nowait(event)
            return True
        except Full:
            self.dropped_count += 1
            return False

    def dispatch(self, limit=256):
        count = 0
        while count < limit:
            try:
                event = self.queue.get_nowait()
            except Empty:
                break
            for consumer in self.subscribers:
                consumer(event)
            count += 1
        return count
