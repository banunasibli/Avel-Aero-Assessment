"""Mocked tools. Nothing here uses the network or sends anything."""
from engine import ToolError


class MockTools:
    def __init__(self, failures=1):
        self.failures_left = failures  # how many times availability times out first
        self.sent = []                 # the fake "outbox"

    def check_availability(self, ctx):
        if self.failures_left > 0:
            self.failures_left -= 1
            raise ToolError("Temporary API timeout")
        return {"aircraft": ["Phenom 300", "Citation XLS"]}

    def prepare_quote(self, ctx):
        aircraft = ctx["check_availability"]["aircraft"][0]  # result of step 1
        request = ctx["request"]
        return {
            "customer": request["customer"],
            "route": request["route"],
            "aircraft": aircraft,
            "price": 8000,
        }

    def send_quote(self, ctx):
        quote = ctx["prepare_quote"]  # result of step 2, which the human approved
        self.sent.append(quote)
        return {"sent": True}
