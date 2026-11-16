"""Run with: python3 -m unittest -v"""
import unittest
from unittest.mock import patch

from engine import Status, WorkflowEngine
from tools import MockTools
from workflow import REQUEST, build_steps


def make(failures=0):
    tools = MockTools(failures=failures)
    engine = WorkflowEngine("REQ-TEST", build_steps(tools), {"request": REQUEST},
                            retry_delay=0, verbose=False)  # no real waiting in tests
    return engine, tools


def labels(engine):
    return [label for label, _ in engine.history]


class WorkflowTests(unittest.TestCase):
    def test_steps_run_in_order_and_pass_data(self):
        engine, tools = make()
        engine.run()
        engine.approve()
        engine.run()
        self.assertEqual(engine.status, Status.COMPLETED)
        self.assertEqual(labels(engine), [
            "START", "RUNNING", "SUCCESS", "RUNNING", "SUCCESS",
            "PAUSED", "APPROVED", "RUNNING", "SUCCESS", "COMPLETE"])
        # the quote used an aircraft from step 1, and step 4 sent the quote from step 2
        aircraft = engine.context["check_availability"]["aircraft"]
        self.assertIn(tools.sent[0]["aircraft"], aircraft)
        self.assertEqual(tools.sent[0], engine.context["prepare_quote"])

    def test_failed_step_is_retried(self):
        engine, _ = make(failures=1)
        engine.run()
        self.assertEqual(labels(engine)[:5], ["START", "RUNNING", "FAILED", "RETRY", "SUCCESS"])
        self.assertEqual(engine.status, Status.PAUSED)

    def test_retries_stop_after_max_attempts(self):
        engine, tools = make(failures=3)
        engine.run()
        self.assertEqual(engine.status, Status.FAILED)
        self.assertEqual(labels(engine).count("RETRY"), 2)
        self.assertNotIn("prepare_quote", engine.context)  # later steps never ran
        self.assertEqual(tools.sent, [])

    def test_waits_longer_before_each_retry(self):
        tools = MockTools(failures=3)
        engine = WorkflowEngine("REQ-TEST", build_steps(tools), {"request": REQUEST}, verbose=False)
        with patch("engine.time.sleep") as fake_sleep:  # record waits instead of waiting
            engine.run()
        self.assertEqual([call.args[0] for call in fake_sleep.call_args_list], [0.5, 1.0])

    def test_nothing_is_sent_while_paused(self):
        engine, tools = make()
        engine.run()
        engine.run()  # running again must not skip the approval
        self.assertEqual(engine.status, Status.PAUSED)
        self.assertEqual(tools.sent, [])

    def test_rejection_sends_nothing(self):
        engine, tools = make()
        engine.run()
        engine.reject()
        engine.run()
        self.assertEqual(engine.status, Status.REJECTED)
        self.assertEqual(tools.sent, [])

    def test_cannot_approve_when_nothing_is_waiting(self):
        engine, _ = make()
        with self.assertRaises(ValueError):
            engine.approve()


if __name__ == "__main__":
    unittest.main()
