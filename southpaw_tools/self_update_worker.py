"""Separate trusted dummy updater/probe. No downloaded EXE is ever executed."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import threading

from .common import LauncherError, atomic_json, inside
from .self_update import SelfUpdater


def probe(updater, transaction, result):
    journal = updater.journal(transaction)
    if journal["phase"] != "probing" or updater.current().to_dict() != journal["new"]:
        raise LauncherError("시작 검사 대상이 활성 후보와 다릅니다.")
    if result == "fail":
        return 9
    if result == "timeout":
        threading.Event().wait(5)  # Bounded dummy startup hang; not a retry/workaround.
        return 10
    atomic_json(inside(updater.home,f"health/{transaction}.json"), {
        "transaction":transaction,"release_id":journal["new"]["release_id"],
        "exe_sha256":journal["new"]["executable_sha256"],
        "nonce":journal["nonce"] if result == "ok" else "incorrect-dummy-ack"})
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["apply","recover","status","probe","hold"])
    parser.add_argument("--home",type=Path,required=True)
    parser.add_argument("--transaction")
    parser.add_argument("--probe-result",choices=["ok","fail","bad-ack","timeout"],default="ok")
    parser.add_argument("--timeout",type=float,default=5)
    parser.add_argument("--interrupt-after",choices=["switching","pointed","probing"])
    parser.add_argument("--hold-target",choices=["runtime","pointer","exe"],default="runtime")
    args = parser.parse_args(argv)
    try:
        updater = SelfUpdater(args.home)  # Rejects all real homes before an action.
        if args.action == "probe":
            return probe(updater,args.transaction,args.probe_result)
        if args.action == "apply":
            def checkpoint(phase):
                if phase == args.interrupt_after:
                    os._exit(74)  # Explicit isolated process-crash test only.
            app = updater.apply(args.transaction,probe_result=args.probe_result,
                                timeout=args.timeout,_checkpoint=checkpoint)
        elif args.action == "recover":
            app = updater.recover()
        elif args.action == "hold":
            if args.hold_target == "runtime":
                with updater.running() as current:
                    exe,_ = updater.engine.resolve_launch(current)
                    with exe.open('rb'):
                        print('READY',flush=True)
                        sys.stdin.readline()
            else:
                current = updater.current()
                target = (inside(updater.home,"current.json") if args.hold_target == "pointer"
                          else updater.engine.resolve_launch(current)[0])
                with target.open('rb'):
                    print('READY',flush=True)
                    sys.stdin.readline()
            return 0
        else:
            app = updater.current()
        print(json.dumps({"release_id":app.release_id,"version":app.version,"dummy_exe_started":False}))
        return 0
    except (LauncherError,OSError,ValueError,KeyError,TypeError) as exc:
        print(f"격리 자체 업데이트 작업 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
