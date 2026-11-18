"""Pinned Ed25519 catalog verification. No network key enrollment or clock policy."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .catalog import parse_catalog
from .common import LauncherError, app_lock, atomic_json

CATALOG_ID = "creative-group-launcher"
from .github_channels import CANONICAL_CATALOG_ID
CATALOG_IDS = (CATALOG_ID, CANONICAL_CATALOG_ID)
DOMAIN = b"CreativeGroupLauncher catalog v1\x00"
MAX_CATALOG = 4 * 1024 * 1024
MAX_SIGNATURE = 4096


def strict_json(raw: bytes, limit: int = MAX_CATALOG) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("non-finite JSON number")
    try:
        if len(raw) > limit:
            raise ValueError("size limit")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(value, dict):
            raise ValueError("object required")
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise LauncherError("카탈로그 서명 데이터 형식 오류") from exc


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def decode(value: str, size: int) -> bytes:
    try:
        result = base64.b64decode(value, validate=True)
        if len(result) != size or b64(result) != value:
            raise ValueError("invalid length/encoding")
        return result
    except (ValueError, TypeError, binascii.Error) as exc:
        raise LauncherError("서명 또는 공개키 인코딩 오류") from exc


def key_id(public: bytes) -> str:
    return hashlib.sha256(public).hexdigest()


def catalog_bytes(apps, sequence: int, *, catalog_id=CATALOG_ID) -> bytes:
    if catalog_id not in CATALOG_IDS:
        raise LauncherError("승인되지 않은 카탈로그 식별자입니다.")
    if type(sequence) is not int or not 1 <= sequence <= 2**63 - 1:
        raise LauncherError("카탈로그 순번은 양의 63비트 정수여야 합니다.")
    document = {"schema_version": 1, "catalog_id": catalog_id, "sequence": sequence,
                "apps": [app.to_dict() for app in apps]}
    raw = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    parse_catalog(strict_json(raw))
    return raw


def sign(raw: bytes, private: Ed25519PrivateKey) -> dict:
    public = private.public_key().public_bytes_raw()
    return {"schema_version": 1, "algorithm": "Ed25519", "key_id": key_id(public),
            "signature": b64(private.sign(DOMAIN + raw))}


def load_private(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Ed25519 required")
        return key
    except (ValueError, TypeError, OSError) as exc:
        raise LauncherError("외부 Ed25519 개인키를 읽을 수 없습니다.") from exc


class CatalogVerifier:
    def __init__(self, policy: dict, state_path: Path):
        # policy comes only from a bundled file or explicit local test injection.
        self.policy = strict_json(json.dumps(policy).encode())
        self.state_path = state_path
        if (set(self.policy) != {"schema_version", "catalog_id", "minimum_sequence", "keys"}
                or type(self.policy["schema_version"]) is not int
                or self.policy["schema_version"] != 1 or self.policy["catalog_id"] not in CATALOG_IDS
                or type(self.policy["minimum_sequence"]) is not int
                or not 1 <= self.policy["minimum_sequence"] <= 2**63 - 1
                or not isinstance(self.policy["keys"], dict)):
            raise LauncherError("사전 탑재 신뢰키 정책 오류")
        for name, value in self.policy["keys"].items():
            if key_id(decode(value, 32)) != name:
                raise LauncherError("사전 탑재 공개키 ID 불일치")

    @classmethod
    def bundled(cls, state_path: Path):
        path = Path(__file__).parent / "data/trusted_catalog_keys.json"
        return cls(strict_json(path.read_bytes()), state_path)

    def verify(self, raw: bytes, signature: bytes):
        metadata = strict_json(signature, MAX_SIGNATURE)
        if (set(metadata) != {"schema_version", "algorithm", "key_id", "signature"}
                or type(metadata["schema_version"]) is not int or metadata["schema_version"] != 1
                or metadata["algorithm"] != "Ed25519" or not isinstance(metadata["key_id"], str)):
            raise LauncherError("카탈로그 분리 서명 형식 오류")
        pinned = self.policy["keys"].get(metadata["key_id"])
        if pinned is None:
            raise LauncherError("알 수 없는 카탈로그 서명 키 — 운영 신뢰키 승인이 필요합니다.")
        if len(raw) > MAX_CATALOG:
            raise LauncherError("카탈로그 크기 초과")
        try:
            Ed25519PublicKey.from_public_bytes(decode(pinned, 32)).verify(
                decode(metadata["signature"], 64), DOMAIN + raw)
        except InvalidSignature as exc:
            raise LauncherError("카탈로그 전자서명 불일치 — 설치·업데이트 차단") from exc
        document = strict_json(raw)
        if (set(document) != {"schema_version", "catalog_id", "sequence", "apps"}
                or type(document["schema_version"]) is not int or document["schema_version"] != 1
                or document["catalog_id"] != self.policy["catalog_id"]
                or type(document["sequence"]) is not int
                or not self.policy["minimum_sequence"] <= document["sequence"] <= 2**63 - 1):
            raise LauncherError("서명된 카탈로그 식별자/순번 오류")
        try:
            apps = parse_catalog(document)
        except (TypeError, ValueError, AttributeError) as exc:
            raise LauncherError("서명된 카탈로그 앱 정보 오류") from exc
        return document, apps

    def _state(self):
        if not self.state_path.exists():
            return None
        try:
            state = strict_json(self.state_path.read_bytes(), 6 * 1024 * 1024)
        except OSError as exc:
            raise LauncherError("카탈로그 신뢰 상태를 읽을 수 없습니다. 자동 초기화하지 않습니다.") from exc
        return self._verify_snapshot(state)

    def _verify_snapshot(self, state):
        if set(state) != {"catalog", "signature"} or not all(isinstance(v, str) for v in state.values()):
            raise LauncherError("카탈로그 신뢰 상태 손상 — 자동 초기화하지 않습니다.")
        try:
            raw = base64.b64decode(state["catalog"], validate=True)
            signature = base64.b64decode(state["signature"], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise LauncherError("카탈로그 신뢰 상태 인코딩 오류") from exc
        document, apps = self.verify(raw, signature)
        return document, apps, hashlib.sha256(raw).hexdigest()

    def installed_release_snapshot(self, app):
        """Capture an accepted catalog while it still authorizes this install."""
        state = strict_json(self.state_path.read_bytes(), 6 * 1024 * 1024)
        self.verify_installed_release(state, app)
        return state

    def verify_installed_release(self, state, app):
        # Historical proof of a local install. Never feed it into accept().
        _, apps, _ = self._verify_snapshot(state)
        if not app.published or app not in apps:
            raise LauncherError("설치 릴리스가 보관된 서명 목록과 일치하지 않습니다.")

    def accept(self, raw: bytes, signature: bytes):
        document, apps = self.verify(raw, signature)
        digest = hashlib.sha256(raw).hexdigest()
        # One OS lock and one atomic file hold both the high-water mark and signed cache.
        with app_lock(self.state_path.with_suffix(".lock")):
            previous = self._state()
            if previous:
                old, _, old_digest = previous
                if (document["sequence"] < old["sequence"] or
                        document["sequence"] == old["sequence"] and digest != old_digest):
                    raise LauncherError("이전 순번 또는 같은 순번의 다른 카탈로그 — 재전송 차단")
                if digest == old_digest:
                    return apps
            atomic_json(self.state_path, {"catalog": b64(raw), "signature": b64(signature)})
        return apps

    def cached(self):
        state = self._state()
        return state[1] if state else None
