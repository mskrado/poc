"""holdout-harness: split-route and booking-cohort holdouts for AI pricing/booking flows.

Everything the bundled CLI prints is generated from a synthetic dataset and is
labelled "synthetic test data". It is not carrier data.
"""
from .bucketing import bucket_value, assign, assign_routes_by_market
from .stats import welch_ci, bootstrap_ratio_ci, mde, n_per_arm, cuped_adjust
from .spillover import mixed_markets, cross_bucket_customers

__version__ = "0.1.0"
LABEL = "synthetic test data"

__all__ = [
    "bucket_value", "assign", "assign_routes_by_market",
    "welch_ci", "bootstrap_ratio_ci", "mde", "n_per_arm", "cuped_adjust",
    "mixed_markets", "cross_bucket_customers", "LABEL", "__version__",
]
