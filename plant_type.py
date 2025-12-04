from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


Color = Tuple[int, int, int]


@dataclass
class PlantType:
    """
    Immutable definition of a crop type.

    - name: display name
    - color: RGB used for drawing
    - grow_time: seconds until fully grown
    - seed_cost: baseline seed cost
    - sell_price: baseline sell price
    """
    name: str
    color: Color
    grow_time: float
    seed_cost: float
    sell_price: float
