# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import hashlib
import json
import os
import socket
import time

from core.credentials.types import APIAppKeyCredential
from core.env.paths import app_home


class ObfuscatedCredentialCache:
    def __init__(self, filename, ttl_seconds=None):
        self._filename = filename
        self._ttl_seconds = ttl_seconds

    def _path(self):
        return os.path.join(app_home(), self._filename)

    def _read_entry(self):
        try:
            with open(self._path()) as f:
                return json.load(f)
        except Exception:
            return None

    def _write_entry(self, entry):
        path = self._path()
        try:
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            tmp_path = f"{path}.{os.getpid()}.tmp"
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({**entry, "fetched_at": time.time()}, f)
            os.replace(tmp_path, path)
        except Exception:
            pass

    def read(self):
        entry = self._read_entry()
        if entry is None:
            return None
        if self._ttl_seconds is not None and time.time() - entry.get("fetched_at", 0) >= self._ttl_seconds:
            return None
        obfuscated_api_key, nonce, dd_site = entry.get("api_key"), entry.get("nonce"), entry.get("dd_site")
        if not obfuscated_api_key or not nonce or not dd_site:
            return None
        try:
            nonce_bytes = bytes.fromhex(nonce)
            api_key = self._deobfuscate(obfuscated_api_key, nonce_bytes)
            obfuscated_app_key = entry.get("app_key")
            app_key = self._deobfuscate(obfuscated_app_key, nonce_bytes) if obfuscated_app_key else None
        except Exception:
            return None
        return (
            APIAppKeyCredential(api_key=api_key, app_key=app_key, dd_site=dd_site)
            if api_key and app_key
            else None
        )

    def write(self, cred):
        nonce = os.urandom(16)
        self._write_entry(
            {
                "api_key": self._obfuscate(cred.api_key, nonce),
                "app_key": self._obfuscate(cred.app_key, nonce) if cred.app_key else None,
                "dd_site": cred.dd_site,
                "nonce": nonce.hex(),
            }
        )

    def clear(self):
        try:
            os.remove(self._path())
        except OSError:
            pass

    def _mask(self, nonce):
        uid = str(os.getuid()) if hasattr(os, "getuid") else ""
        h = hashlib.sha256()
        h.update(socket.gethostname().encode())
        h.update(uid.encode())
        h.update(nonce)
        return h.digest()

    def _xor(self, data, mask):
        return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(data))

    def _obfuscate(self, key, nonce):
        return self._xor(key.encode(), self._mask(nonce)).hex()

    def _deobfuscate(self, obfuscated, nonce):
        return self._xor(bytes.fromhex(obfuscated), self._mask(nonce)).decode()
