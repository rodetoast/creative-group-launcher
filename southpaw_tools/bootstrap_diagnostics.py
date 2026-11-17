"""Bounded, exception-local Bootstrap diagnostics. Never writes files itself."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import os
import re
import json
import sys

ATTRIBUTE = '_bootstrap_failure'
LIMIT = 12


def mark(exc, operation, *, api=None, target=None, pid=None, access=None):
    """Attach only explicit provenance; innermost failing operation wins."""
    try:
        item = {'operation': operation, 'api': api}
        if target is not None:
            item['target'] = os.fspath(target)
        if type(pid) is int:
            item['pid'] = pid
        if type(access) is int:
            item['access'] = access
        info = getattr(exc, ATTRIBUTE, None)
        if info is None:
            info = {'occurred_at': datetime.now(timezone.utc).isoformat(), 'operations': [], 'secondary': []}
            setattr(exc, ATTRIBUTE, info)
        if len(info['operations']) < LIMIT and item not in info['operations']:
            info['operations'].append(item)
    except Exception:
        # Diagnostic metadata must never replace a real failure.
        pass


@contextmanager
def operation(name, **fields):
    try:
        yield
    except Exception as exc:
        mark(exc, name, **fields)
        raise


def call(name, function, *args, api=None, target=None, pid=None, access=None, **kwargs):
    with operation(name, api=api, target=target, pid=pid, access=access):
        return function(*args, **kwargs)


def diagnosed(name):
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            with operation(name, api=function.__qualname__):
                return function(*args, **kwargs)
        return run
    return decorate


def secondary(primary, error, name):
    mark(error, name)
    mark(primary, 'failure_propagation')
    try:
        items = getattr(primary, ATTRIBUTE)['secondary']
        if len(items) < 3:
            items.append(error)
    except Exception:
        pass


def _path(value, roots):
    # Lexical only: diagnosing a failure must not access the failed filesystem.
    text = os.fspath(value)
    absolute = os.path.abspath(text)
    for alias, root in roots.items():
        if root is None:
            continue
        base = os.path.abspath(root)
        try:
            if os.path.commonpath([absolute, base]).casefold() == base.casefold():
                parts = Path(os.path.relpath(absolute, base)).parts
                # Session/transaction/temporary random identifiers are not needed.
                parts = [re.sub(r'[a-fA-F0-9]{32,}', '<id>', p) if not p.startswith('.pending-') else '<temporary>'
                         for p in parts]
                return (alias + '/' + '/'.join(parts))[:300]
        except ValueError:
            continue
    # Unknown user paths are not an implicit disclosure permission.
    return '<outside-known-roots>'


def report(exc, *, home=None, data=None):
    try:
        roots = {'<launcher-home>': home, '<data-root>': data,
                 '<source>': Path(os.path.abspath(__file__)).parents[1], '<python-runtime>': sys.base_prefix}
    except Exception:
        return {'schema_version': 1, 'diagnostic_unavailable': True}
    seen = set()

    def node(error, depth=0):
        if id(error) in seen or depth >= 6 or len(seen) >= 16:
            return {'truncated': True}
        seen.add(id(error))
        info = getattr(error, ATTRIBUTE, {})
        result = {'exception_class': type(error).__name__,
                  'errno': getattr(error, 'errno', None), 'winerror': getattr(error, 'winerror', None),
                  'occurred_at': info.get('occurred_at'), 'operations': []}
        for field in ('filename', 'filename2'):
            value = getattr(error, field, None)
            if isinstance(value, (str, os.PathLike)):
                result[field] = _path(value, roots)
        for item in info.get('operations', [])[:LIMIT]:
            item = dict(item)
            if 'target' in item:
                item['target'] = _path(item['target'], roots)
            result['operations'].append(item)
        result['operation'] = (result['operations'] or [{'operation': 'unclassified'}])[0]['operation']
        frames = []
        tb = error.__traceback__
        while tb is not None:
            code = tb.tb_frame.f_code
            frames.append({'module': _path(code.co_filename, roots),
                           'function': code.co_name[:100], 'line': tb.tb_lineno})
            tb = tb.tb_next
        result['traceback'] = frames[-16:]
        if frames:
            result['python_call'] = frames[-1]
        if error.__cause__ is not None:
            result['cause'] = node(error.__cause__, depth + 1)
        if error.__context__ is not None and error.__context__ is not error.__cause__:
            result['context'] = node(error.__context__, depth + 1)
        result['suppress_context'] = bool(error.__suppress_context__)
        result['secondary'] = [node(e, depth + 1) for e in info.get('secondary', [])[:3]]
        return result

    try:
        value = {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
                 'failure': node(exc)}
        if len(json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')) > 48 * 1024:
            # Keep the original origin and identity, cap long chained failures.
            value['failure'] = {k: v for k, v in value['failure'].items()
                                if k not in {'cause', 'context', 'secondary'}}
            value['truncated'] = True
        return value
    except Exception:
        return {'schema_version': 1, 'diagnostic_unavailable': True}


def error_summary(exc):
    # Never serialize arbitrary exception text (may contain nonce/credentials/body).
    codes = [f'{key}={getattr(exc, key)}' for key in ('errno', 'winerror')
             if isinstance(getattr(exc, key, None), int)]
    return f'Bootstrap 작업 실패: {type(exc).__name__}' + (' (' + ', '.join(codes) + ')' if codes else '')
