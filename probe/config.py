"""Configuration loading. Defaults live in config.example.json; a real run
copies it to config.json and edits values. The fee cap has NO default in code:
if the key is absent, live mode refuses to start (see sender.py)."""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)


class Config:
    def __init__(self, data: dict):
        self.data = data

    def __getattr__(self, name):
        try:
            return self.data[name]
        except KeyError:
            raise AttributeError(f"config key missing: {name}")

    def get(self, name, default=None):
        return self.data.get(name, default)

    @property
    def fee_cap_lamports(self):
        """None when unset — live mode treats that as a hard refusal."""
        return self.data.get("fee_cap_lamports")

    def data_dir_path(self):
        return os.path.join(ROOT, self.data.get("data_dir", "data"))

    def validators_path(self):
        return os.path.join(ROOT, self.data.get("validators_file", "validators.json"))


def load(path: str = None) -> Config:
    if path is None:
        candidate = os.path.join(ROOT, "config.json")
        path = candidate if os.path.exists(candidate) else os.path.join(
            ROOT, "config.example.json"
        )
    with open(path) as fh:
        return Config(json.load(fh))


def load_validators(cfg: Config):
    with open(cfg.validators_path()) as fh:
        return json.load(fh)
