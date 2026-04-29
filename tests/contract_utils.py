import json
from pathlib import Path

from lib.output_schema import ANALYZER_NAMES

CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"


def normalize_contract(value):
    if isinstance(value, dict):
        keys = set(value)

        if keys and keys.issubset(set(ANALYZER_NAMES)):
            return {k: normalize_contract(value[k]) for k in sorted(value)}

        return {k: normalize_contract(value[k]) for k in sorted(value)}

    if isinstance(value, list):
        if not value:
            return []

        return [normalize_contract(value[0])]

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, (int, float)):
        return "number"

    if isinstance(value, str):
        return "str"

    if value is None:
        return "null"

    return type(value).__name__


def load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text())


def assert_matches_contract(actual: dict, contract_name: str) -> None:
    normalized = normalize_contract(actual)
    expected = load_contract(contract_name)
    assert normalized == expected
