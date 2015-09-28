import time

from sortedcontainers import SortedList

from .exceptions import BreakerOpen


def now():
    return int(time.time())


class Breaker(object):
    def __init__(self, threshold, service=None, duration=60,
                 reenable_after=300, strategy='absolute'):
        """
        :param threshold: the percentage of errors in the window to open the breaker.
        :param service: (optional) an identifier for the service. Default to 'default'.
        :param duration: (optional) window in seconds to calculate error rate.
        :param reenable_after: (optional) number of seconds to keep the breaker open.
        :param strategy: (optional) 'absolute' or 'percentage'
        """
        self.service = service if service is not None else 'default'
        self.strategy = strategy

        # keep track of errors over a x seconds window
        self.duration = duration
        # open the circuit breaker when error rate is at x%
        self.threshold = threshold
        # keep the breaker open for x seconds
        self.reenable_after = reenable_after

        # internal attributes
        self._last_open = None
        # used to store rate of errors
        self._runs = SortedList()
        self._errors = SortedList()

        # minimum number of request before we start tripping
        self._minimum_threshold = 5

    def run(self):
        if self.open:
            raise BreakerOpen()

        try:
            self.increment_rolling_window('_runs')
        except Exception:
            self.process_error()
            raise
        else:
            self.process_success()

    def process_success(self):
        if self.half_open:
            self.reset()

    def reset(self):
        self._last_open = None
        self._errors = SortedList()

    def process_error(self):
        count = self.increment_rolling_window('_errors')
        if self.half_open or self.should_open(count):
            self.trip()

    @property
    def half_open(self):
        if self.last_open is not None:
            return self.last_open < (now() - self.reenable_after)
        return False

    @property
    def last_open(self):
        return self._last_open

    @property
    def open(self):
        if self.last_open is not None:
            return self.last_open > (now() - self.reenable_after)
        return False

    def trip(self):
        self._last_open = now()

    def key(self, name=None):
        return "breaker-{}-{}".format(self.service, name)

    def should_open(self, error_count):
        if self.strategy == 'absolute':
            return self.should_open_absolute(error_count)
        elif self.strategy == 'percentage':
            return self.should_open_percentage(error_count)

        raise NotImplementedError("`{}` strategy is not implemented".format(self.strategy))

    def should_open_absolute(self, error_count):
        return error_count >= self.threshold

    def should_open_percentage(self, error_count):
        # do not open until we have a reasonable number of requests
        if len(self._runs) < self._minimum_threshold:
            return False

        # calculate the percentage of errors based on the
        error_percentage = error_count * 100 / len(self._runs)
        return error_percentage >= self.threshold

    def increment_rolling_window(self, counter_name):
        """Increment the rolling window for a given counter"""
        counter = getattr(self, counter_name)

        # remove old errors from the list
        setattr(self, counter_name, SortedList(counter.irange(now() - self.duration)))

        counter = getattr(self, counter_name)
        counter.add(now())
        # return the cardinality of the list. ie num of errors
        return len(counter)
