"""Public list prices used for MODELLED costs. Nothing here was billed.

Fetched 2026-10-05 (Europe/Moscow). Standard tier, short-context rates, USD per 1M tokens.
"""
FETCH_DATE = "2026-10-05"

FRONTIER = {
    "gpt-6.1-sol": {
        "input_per_mtok": 2.00, "output_per_mtok": 10.00,
        "source": "https://developers.openai.com/api/docs/pricing",
        "crosscheck": "https://artificialanalysis.ai/models/gpt-6-1-sol",
        "note": "Standard, short context",
    },
    "claude-opus-5.5": {
        "input_per_mtok": 4.00, "output_per_mtok": 20.00,
        "source": "https://www.anthropic.com/pricing",
        "crosscheck": "https://artificialanalysis.ai/models/claude-opus-5-5",
        "note": "Base input / output, Standard",
    },
    "gemini-3.1-pro-preview": {
        "input_per_mtok": 2.00, "output_per_mtok": 12.00,
        "source": "https://ai.google.dev/gemini-api/docs/pricing",
        "crosscheck": "https://artificialanalysis.ai/models/gemini-3-1-pro-preview",
        "note": "Paid tier, prompts <= 200k tokens",
    },
}

# Local compute is free on this box, so we model it: wall time x the public
# on-demand price of a comparable 8 vCPU / 16 GiB CPU instance.
LOCAL_INSTANCE = {
    "name": "AWS c7i.2xlarge (8 vCPU, 16 GiB), Linux on-demand",
    "usd_per_hour": 0.357,
    "source": "https://instances.vantage.sh/aws/ec2/c7i.2xlarge",
}


def frontier_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = FRONTIER[model]
    return input_tokens / 1e6 * p["input_per_mtok"] + output_tokens / 1e6 * p["output_per_mtok"]


def local_cost(wall_ms: float) -> float:
    return wall_ms / 3.6e6 * LOCAL_INSTANCE["usd_per_hour"]
