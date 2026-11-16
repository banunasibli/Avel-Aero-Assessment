"""Run the charter quote workflow from the command line."""
import argparse

from engine import Status, WorkflowEngine
from tools import MockTools
from workflow import REQUEST, build_steps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-times", type=int, default=1,
                        help="how many times 'check availability' times out first "
                             "(default 1; use 3 to make every attempt fail)")
    args = parser.parse_args()

    tools = MockTools(failures=args.fail_times)
    engine = WorkflowEngine(REQUEST["id"], build_steps(tools), {"request": REQUEST})

    engine.run()  # runs until it pauses, finishes, or fails

    if engine.status is Status.PAUSED:
        quote = engine.context["prepare_quote"]
        print(f"\n  Draft: {quote['customer']}, {quote['route']}, "
              f"{quote['aircraft']}, ${quote['price']:,}\n")
        answer = input("Approve sending this quote? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            engine.approve()
            engine.run()  # continues after the approval step
        else:
            engine.reject()

    print(f"\nFinal status: {engine.status.value}")


if __name__ == "__main__":
    main()
