from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PriceHistory:
    """
    Tracks dynamic pricing for a single crop over time.

    - base_price: baseline sell price for the crop.
    - current_multiplier: current multiplier applied to base_price.
    - history: recent history of absolute prices (base_price * multiplier).
    """
    base_price: float
    current_multiplier: float = 1.0
    history: List[float] = field(default_factory=list)
