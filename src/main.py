from pathlib import Path

from command.registry import CommandRegistry
from core.loader import load_testcases
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver


def _build_observers():
    observers = [LoggerObserver()]
    try:
        from observer.allure import AllureObserver
        observers.append(AllureObserver())
    except Exception:
        # Keep CLI execution available even when allure runtime is absent.
        pass
    return observers


def load_default_commands(cmds: CommandRegistry, base_dir: str = "."):
    """
    Backward compatible command directories:
    - conf/command/** (current)
    - conf/commands/*.yaml (legacy/new_frame style)
    """
    root = Path(base_dir)
    cmds.load_dir(str(root / "conf" / "command"))
    cmds.load_dir(str(root / "conf" / "commands"))


def run_all(base_dir: str = "."):
    cmds = CommandRegistry()
    load_default_commands(cmds, base_dir=base_dir)

    engine = ExecutionEngine(cmds, observers=_build_observers())

    root = Path(base_dir)
    for tc in load_testcases(str(root / "conf" / "testcases"), cmds):
        engine.run(tc)


def main():
    run_all(".")


if __name__ == "__main__":
    main()
