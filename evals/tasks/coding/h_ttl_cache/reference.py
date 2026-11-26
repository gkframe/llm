import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        if capacity < 1 or ttl <= 0:
            raise ValueError("capacity must be >= 1 and ttl > 0")
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self._d = OrderedDict()          # key -> (value, expires), least recent first

    def _purge(self):
        now = self.clock()
        for k in [k for k, (_, exp) in self._d.items() if now >= exp]:
            del self._d[k]

    def _live(self, key):
        item = self._d.get(key)
        if item is None:
            return None
        if self.clock() >= item[1]:
            del self._d[key]
            return None
        return item

    def set(self, key, value):
        if self._live(key) is None:
            if len(self._d) >= self.capacity:
                self._purge()
            if len(self._d) >= self.capacity:
                self._d.popitem(last=False)
        self._d[key] = (value, self.clock() + self.ttl)
        self._d.move_to_end(key)

    def get(self, key, default=None):
        item = self._live(key)
        if item is None:
            return default
        self._d.move_to_end(key)
        return item[0]

    def delete(self, key):
        if self._live(key) is None:
            return False
        del self._d[key]
        return True

    def __len__(self):
        self._purge()
        return len(self._d)

    def __contains__(self, key):
        return self._live(key) is not None
