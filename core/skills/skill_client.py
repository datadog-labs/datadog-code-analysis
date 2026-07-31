# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import concurrent.futures
import json
import urllib.error
import urllib.parse

from core.httpclient.datadog_client import DatadogClient
from core.logger.composite_logger import log

SKILLS_PATH = "/api/unstable/iac-api/skills"


class SkillClientError(Exception):
    pass


class SkillNotFoundError(SkillClientError):
    pass


class SkillClient(DatadogClient):
    def list_skills(self):
        query = urllib.parse.urlencode({"tags": "coding_telemetry_skill:true"})
        return self._skills_request(f"{SKILLS_PATH}?{query}")["skills"]

    def get_skill(self, name):
        return self._skills_request(f"{SKILLS_PATH}/{urllib.parse.quote(name, safe='')}")

    def load_guidance(self):
        try:
            skills = self.list_skills()
        except SkillClientError as e:
            log(self._session_id, f"failed to list skills: {e}")
            return None
        if not skills:
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(skills)) as pool:
            fetched = pool.map(self._try_get_skill, [s["name"] for s in skills])

        parts = [f"## {skill['name']}\n{skill['content']}" for skill in fetched if skill]
        return "\n\n".join(parts) if parts else None

    def _try_get_skill(self, name):
        try:
            return self.get_skill(name)
        except SkillClientError as e:
            log(self._session_id, f"failed to load skill '{name}': {e}")
            return None

    def _skills_request(self, path):
        try:
            with self.request(path) as resp:
                body = json.load(resp)
            attributes = body["data"]["attributes"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise SkillNotFoundError(f"{path} not found") from e
            raise SkillClientError(f"{path} returned HTTP {e.code}") from e
        except Exception as e:
            raise SkillClientError(f"request to {path} failed: {e}") from e
        log(self._session_id, f"fetched {path} → 200")
        return attributes
