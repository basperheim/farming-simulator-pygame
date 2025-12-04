from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from plant_instance import PlantInstance


class Tile:
    """
    Single cell in the farm grid.

    Attributes:
    - grid_x, grid_y: indices in the logical grid
    - rect: pygame.Rect for drawing / hit detection
    - purchased: whether the land has been bought
    - has_silo: whether a silo occupies this tile
    - plant: PlantInstance currently planted here, or None
    """

    def __init__(self, grid_x: int, grid_y: int, rect: pygame.Rect):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.rect = rect
        self.purchased: bool = False
        self.plant: Optional["PlantInstance"] = None
        self.has_silo: bool = False

    def can_plant(self) -> bool:
        """
        Returns True if this tile can accept a new plant:
        - land must be purchased
        - no existing plant
        - no silo on the tile
        """
        return self.purchased and self.plant is None and not self.has_silo
