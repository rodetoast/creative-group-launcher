"""Verify a signed release plan and publish it only with its approved SHA-256."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from southpaw_tools.catalog_trust import CatalogVerifier
from southpaw_tools.common import LauncherError, digest, read_json


REPO = "toast-source/creative-group-releases"


def verified_plan(path: Path):
    plan = read_json(path)
    sequence = plan.get("sequence")
    if (plan.get("repository") != REPO or type(sequence) is not int or sequence <= 3
            or plan.get("tag") != f"production-catalog-{sequence:06d}"
            or not re.fullmatch(r"[a-f0-9]{40}", plan.get("target", ""))
            or type(plan.get("previous_latest_id")) is not int):
        raise LauncherError("운영 Release 계획 형식 또는 대상이 다릅니다.")
    assets = path.parent / "assets"
    policy_path = path.parent / "trusted_catalog_keys.json"
    if digest(policy_path) != plan["policy_sha256"]:
        raise LauncherError("운영 공개키 정책 해시 불일치")
    verifier = CatalogVerifier(read_json(policy_path), path.parent / "unused-trust-state.json")
    if verifier.policy["minimum_sequence"] != sequence or len(verifier.policy["keys"]) != 1:
        raise LauncherError("계획에 지정된 운영 신뢰 정책이 아닙니다.")
    document, apps = verifier.verify((assets / "catalog.json").read_bytes(),
                                     (assets / "catalog.sig.json").read_bytes())
    published = [app for app in apps if app.published]
    packages = {app.package_name: app for app in published}
    expected = {"catalog.json", "catalog.sig.json", *packages}
    entries = plan["assets"]
    if (document["sequence"] != sequence or len(packages) != len(published)
            or {app.app_id for app in published} != {"tilenamer", "ps2ase", "pivot-fixer"}
            or set(entries) != expected or {item.name for item in assets.iterdir()} != expected):
        raise LauncherError("운영 자산 목록이 서명 카탈로그와 다릅니다.")
    for name, row in entries.items():
        file = assets / name
        if (file.is_symlink() or not file.is_file() or file.stat().st_size != row["size"]
                or digest(file) != row["sha256"]):
            raise LauncherError(f"승인 대상 파일과 다릅니다: {name}")
        if name in packages:
            app = packages[name]
            if row != {"size": app.package_size, "sha256": app.sha256}:
                raise LauncherError(f"서명된 패키지와 다릅니다: {name}")
    return plan, assets


def publish(path: Path, approved_hash: str, gh: str):
    if digest(path) != approved_hash:
        raise LauncherError("사용자가 승인한 게시 계획 SHA-256이 일치하지 않습니다.")
    plan, assets = verified_plan(path)
    prefix = f"repos/{REPO}"
    tag = plan["tag"]

    def run(*args):
        proc = subprocess.run([gh, *args], capture_output=True, timeout=900,
                              env={k: v for k, v in os.environ.items() if k != "GH_DEBUG"})
        if proc.returncode:
            raise LauncherError(f"GitHub CLI 종료 코드 {proc.returncode}. 원격 상태를 확인하세요.")
        return proc.stdout

    def api(endpoint, *args):
        return json.loads(run("api", endpoint, *args))

    def releases():
        pages = api(prefix + "/releases?per_page=100", "--paginate", "--slurp")
        return [row for page in pages for row in page]

    repository = api(prefix)
    latest = api(prefix + "/releases/latest")
    if (repository["full_name"] != REPO or repository["visibility"] != "public"
            or latest["id"] != plan["previous_latest_id"]
            or api(prefix + "/commits/" + repository["default_branch"])["sha"] != plan["target"]
            or any(row["tag_name"] == tag for row in releases())
            or api(prefix + f"/git/matching-refs/tags/{tag}")):
        raise LauncherError("승인 이후 저장소·Latest·대상 커밋·태그 상태가 달라졌습니다.")

    def check_remote(draft):
        rows = [row for row in releases() if row["tag_name"] == tag]
        if len(rows) != 1 or rows[0]["draft"] is not draft or rows[0]["prerelease"]:
            raise LauncherError("대상 Release 상태 불일치")
        row = rows[0]
        remote = {a["name"]: (a["size"], a.get("digest")) for a in row["assets"]}
        expected = {n: (a["size"], "sha256:" + a["sha256"]) for n, a in plan["assets"].items()}
        if remote != expected or len(row["assets"]) != len(expected):
            raise LauncherError("원격 자산 크기·SHA-256 불일치")
        return row

    run("release", "create", tag, *(str(assets / n) for n in sorted(plan["assets"])),
        "--repo", REPO, "--draft", "--latest=false", "--target", plan["target"],
        "--title", f"Creative Group Launcher Production Catalog {plan['sequence']:06d}",
        "--notes", "Signed production catalog for TileNamer, Ase-PS Bridge Pro and Pivot_Fixer.")
    draft = check_remote(True)
    redownload = path.parent / ("redownload-" + uuid4().hex)
    redownload.mkdir()
    run("release", "download", tag, "--repo", REPO, "--dir", str(redownload))
    if ({f.name for f in redownload.iterdir()} != set(plan["assets"])
            or any(digest(redownload / n) != a["sha256"] for n, a in plan["assets"].items())
            or check_remote(True)["id"] != draft["id"]
            or api(prefix + "/releases/latest")["id"] != plan["previous_latest_id"]):
        raise LauncherError("공개 직전 자산 또는 Latest 검증에 실패했습니다. 초안을 보존합니다.")
    run("release", "edit", tag, "--repo", REPO, "--draft=false", "--latest")
    public = check_remote(False)
    if public["id"] != draft["id"] or api(prefix + "/releases/latest")["id"] != public["id"]:
        raise LauncherError("공개 후 Latest를 확인할 수 없습니다. 원격 상태를 확인하세요.")
    return public["html_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--gh", default="gh")
    parser.add_argument("--approve-plan-sha256")
    args = parser.parse_args()
    path = args.plan.resolve()
    try:
        verified_plan(path)
        if args.approve_plan_sha256:
            print(publish(path, args.approve_plan_sha256, args.gh))
        else:
            print(f"Validated locally. Plan SHA-256: {digest(path)}")
    except (LauncherError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
