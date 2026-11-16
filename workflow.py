"""The charter inquiry workflow: four steps, one of them a human approval."""
from engine import Step

REQUEST = {"id": "REQ-1042", "customer": "Gojo Satoru", "route": "Tokyo to Osaka"}


def build_steps(tools):
    return [
        Step("check_availability", "Check availability",
             fn=tools.check_availability, success="Aircraft availability received"),
        Step("prepare_quote", "Prepare quote",
             fn=tools.prepare_quote, success="Draft prepared"),
        Step("human_approval", "Human approval", pause_for_approval=True),
        Step("send_quote", "Send quote (mock)",
             fn=tools.send_quote, success="Mock send completed"),
    ]
