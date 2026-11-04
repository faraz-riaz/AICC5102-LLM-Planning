#!/usr/bin/env python3
"""Validate one LLM provider's local configuration without making API calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm_heuristics import models  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=models.PROVIDERS,
        help="Provider to validate (defaults to LLM_PROVIDER or gemini).",
    )
    parser.add_argument(
        "--model",
        help="Optional alias or exact model ID (defaults to <PROVIDER>_MODEL).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        configuration = models.describe_provider_configuration(
            args.provider, args.model
        )
    except (models.ProviderConfigurationError, ValueError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(configuration, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
