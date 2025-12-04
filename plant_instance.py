from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plant_type import PlantType


class PlantInstance:
    """
    A single planted crop on a tile.

    Stores:
    - plant_type: which crop type this is (Wheat, Corn, etc)
    - planted_time: game_time when it was planted
    """

    def __init__(self, plant_type: "PlantType", planted_time: float):
        self.plant_type = plant_type
        self.planted_time = planted_time

    def is_ready(self, current_time: float) -> bool:
        """Return True if the crop has fully grown."""
        return (current_time - self.planted_time) >= self.plant_type.grow_time

    def progress(self, current_time: float) -> float:
        """
        Return a value in [0, 1] indicating percentage of growth completed.
        Used for drawing the growth bar / height.
        """
        if self.plant_type.grow_time <= 0:
            return 1.0
        return max(
            0.0,
            min(1.0, (current_time - self.planted_time) / self.plant_type.grow_time),
        )
