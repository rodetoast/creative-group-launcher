"""Read-only comparison with the five source repositories captured before development."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from southpaw_tools.common import atomic_json, digest, read_json
from tools.import_approved import DESKTOP, SPECS


def git(root: Path, *args):
    result = subprocess.run(["git", "-c", f"safe.directory={root}", "-C", str(root),
                             "-c", "core.quotepath=false", *args], capture_output=True,
                            encoding="utf-8", check=True,
                            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    return result.stdout.strip()


def main():
    project = Path(__file__).resolve().parents[1]
    baseline = json.loads((project / "docs/baseline.local.json").read_text(encoding="utf-8"))
    rows = []
    for previous in baseline:
        root = Path(previous["Path"])
        files = git(root, "ls-files", "-c", "-o", "--exclude-standard").splitlines()
        hashes = {name: digest(root / name).upper() for name in files if (root / name).is_file()}
        # Porcelain's leading space is meaningful. Do not strip the first row.
        status = subprocess.run(["git", "-c", f"safe.directory={root}", "-C", str(root),
                                 "-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all"],
                                capture_output=True, encoding="utf-8", check=True,
                                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).stdout.splitlines()
        row = {"project": root.name, "files_checked": len(hashes),
               "source_hashes_unchanged": hashes == previous["Hashes"],
               "head_unchanged": git(root, "rev-parse", "HEAD") == previous["Head"],
               "tags_unchanged": git(root, "show-ref", "--tags").splitlines() == previous["Tags"],
               "status_unchanged": status == previous["Status"]}
        rows.append(row)
    packages = []
    for spec in SPECS:
        source = DESKTOP / spec["source"]
        packages.append({"app_id": spec["app_id"], "source_found": source.is_file(),
                         "original_zip_unchanged": digest(source) == spec["sha"] if source.is_file() else None})
    report = {"repositories": rows, "original_packages": packages,
              "passed": all(all(row[key] for key in ("source_hashes_unchanged", "head_unchanged",
                                                       "tags_unchanged", "status_unchanged")) for row in rows)
                        and all(row["original_zip_unchanged"] is not False for row in packages)}
    atomic_json(project / "docs/existing-projects-verification.local.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
