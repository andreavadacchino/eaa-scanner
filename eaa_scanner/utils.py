from __future__ import annotations

import shutil
import subprocess
from typing import Iterable, List, Tuple


def first_available(cmds: Iterable[List[str]]) -> Tuple[List[str] | None, str | None]:
    for cmd in cmds:
        if shutil.which(cmd[0]):
            return cmd, None
    return None, "no command found"


def run_command(cmd: List[str], timeout_sec: float = 60.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)

