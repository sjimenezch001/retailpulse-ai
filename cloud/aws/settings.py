"""Explicit single-account, single-region laboratory identity."""

import re
from dataclasses import dataclass

from cloud.aws.contracts import LabError, digest


@dataclass(frozen=True)
class Settings:
    account: str
    region: str
    environment: str
    run_id: str

    def __post_init__(self):
        for value, pattern in (
            (self.account, r"\d{12}"),
            (self.region, r"[a-z]{2}-[a-z]+-\d"),
            (self.environment, r"[a-z][a-z0-9-]{2,16}"),
            (self.run_id, r"[0-9a-f]{24}"),
        ):
            if not re.fullmatch(pattern, value):
                raise LabError("invalid_lab_selection")

    @property
    def bucket(self):
        return f"retailpulse-{self.environment}-{self.account}-{self.region}"

    @property
    def name(self):
        return f"retailpulse-{self.environment}"

    @property
    def database(self):
        return f"rp_{self.environment.replace('-', '_')}"

    @property
    def lab_id(self):
        return digest(f"{self.account}:{self.region}:{self.environment}".encode())[:16]

    @property
    def tags(self):
        return {
            "Project": "RetailPulseAI",
            "Environment": self.environment,
            "LabId": self.lab_id,
            "Stage": "RP12A",
        }

    def prefix(self, category):
        if category not in {
            "input",
            "curated",
            "scripts",
            "serving",
            "temporary",
            "results",
        }:
            raise LabError("invalid_prefix")
        return "results/" if category == "results" else f"{category}/{self.run_id}/"

    def key(self, category, filename):
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", filename) or filename in {".", ".."}:
            raise LabError("invalid_object_name")
        return self.prefix(category) + filename

    def owned_key(self, key):
        # Past run versions are still owned by this exact, tagged lab bucket.
        return bool(
            re.fullmatch(
                r"(?:input|curated|scripts|serving|temporary)/[0-9a-f]{24}/.+|results/.+",
                key,
            )
        )

    def arn(self, service, resource):
        return f"arn:aws:{service}:{self.region}:{self.account}:{resource}"
