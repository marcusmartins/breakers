import unittest
import time

from breakers import Breaker
from breakers.exceptions import BreakerOpen


def echo(foo):
    return foo


class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.breaker = Breaker(service='test', threshold=5)

    def test_breaker_run_with_arg(self):
        ret = self.breaker.call(echo, *['hello', ])
        self.assertEqual(ret, 'hello')

        ret = self.breaker.call(echo, 'hello')
        self.assertEqual(ret, 'hello')

    def test_breaker_run_with_kwarg(self):
        ret = self.breaker.call(echo, **{'foo': 'hello'})
        self.assertEqual(ret, 'hello')

        ret = self.breaker.call(echo, foo='hello')
        self.assertEqual(ret, 'hello')

    def test_breaker_with_context_manager(self):
        with self.breaker():
            print('hello')

        self.assertEqual(len(self.breaker._calls), 1)

    def test_breaker_with_error(self):
        with self.assertRaises(RuntimeError):
            with self.breaker():
                raise RuntimeError("Error")

        self.assertEqual(len(self.breaker._calls), 1)
        self.assertEqual(len(self.breaker._errors), 1)

    def test_breaker_trip_open(self):
        for i in xrange(4):
            with self.assertRaises(RuntimeError):
                with self.breaker():
                    raise RuntimeError("Error")

        self.assertEqual(len(self.breaker._calls), 4)
        self.assertEqual(len(self.breaker._errors), 4)
        self.assertFalse(self.breaker.open)

        # 1 more run and we should trigger the open breaker
        try:
            with self.breaker():
                raise RuntimeError("Error")
        except Exception:
            pass

        self.assertTrue(self.breaker.open)

        # subsequent calls should get BreakerOpen exception
        with self.assertRaises(BreakerOpen):
                with self.breaker():
                    raise RuntimeError("Error")

    def test_initial_state(self):
        self.assertFalse(self.breaker.open)
        self.assertFalse(self.breaker.half_open)

    def test_breaker_state_before_reenable_period(self):
        breaker = Breaker(service='test', reenable_after=10, threshold=5)
        breaker._last_open = int(time.time()) - 5
        self.assertTrue(breaker.open)
        self.assertFalse(breaker.half_open)

    def test_breaker_state_after_reenable_period(self):
        breaker = Breaker(service='test', reenable_after=10, threshold=5)
        breaker._last_open = int(time.time()) - 11
        self.assertTrue(breaker.half_open)
        self.assertFalse(breaker.open)

    def test_increment_rolling_window_by_one(self):
        self.assertEquals(self.breaker.increment_rolling_window('_errors'), 1)

    def test_increment_rolling_window_by_sixty(self):
        for i in range(60):
            self.assertEquals(self.breaker.increment_rolling_window('_errors'), i + 1)

    def test_increment_rolling_window_eviction(self):
        # create a breaker that tracks event for 1 second
        breaker = Breaker(service='test', duration=1, threshold=5)
        self.assertEquals(breaker.increment_rolling_window('_errors'), 1)
        # sleep for over a second so that previous event will be cleaned
        #time.sleep(2)
        #self.assertEquals(breaker.increment_rolling_window('_errors'), 1)

    def test_should_open_if_exceeds_threshold(self):
        breaker = Breaker(service='test', threshold=5)
        self.assertTrue(breaker.should_open(6))

    def test_should_open_if_not_exceeds_threshold(self):
        breaker = Breaker(service='test', threshold=5)
        self.assertFalse(breaker.should_open(4))

    def test_process_a_single_error(self):
        self.breaker.process_error()
        self.assertFalse(self.breaker.open)
        self.assertFalse(self.breaker.half_open)

    def test_trip_after_enough_errors(self):
        breaker = Breaker(service='test', threshold=2)
        for i in range(2):
            breaker.process_error()
        self.assertTrue(breaker.open)
        self.assertFalse(breaker.half_open)
        # compare against an stale timestamp
        stale_now = time.time() - 1
        self.assertGreater(breaker.last_open, stale_now)
        self.assertTrue(breaker.open)

    def test_process_success(self):
        breaker = Breaker(service='test', threshold=1, reenable_after=1)
        # compare against an stale timestamp
        breaker._last_open = time.time() - 2
        self.assertTrue(breaker.half_open)

        # an success should reset the breaker
        breaker.process_success()
        self.assertIsNone(breaker.last_open)
        self.assertFalse(breaker.half_open)
        self.assertEqual(len(breaker._errors), 0)

    def test_should_be_open_based_on_percentage(self):
        # set to 10%
        breaker = Breaker(service='test', threshold=10, duration=60,
                          strategy='percentage')
        # first we run 60 times to bump the number of runs.
        for i in range(60):
            breaker.increment_rolling_window('_calls')

        # five errors out of 60 runs is just bellow 10%
        for i in range(5):
            breaker.process_error()
        self.assertFalse(breaker.open)
        # one more error and we're above 10%
        breaker.process_error()
        self.assertTrue(breaker.open)
