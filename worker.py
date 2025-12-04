from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
import pygame

from plant_type import PlantType
from plant_instance import PlantInstance

if TYPE_CHECKING:
    from tile import Tile
    from main import Game


class Worker:
    def __init__(self, x: float, y: float, speed: float = 70.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.target_tile: Optional["Tile"] = None
        self.carried_plant_type: Optional[PlantType] = None

    def find_target(self, tiles: List["Tile"], current_time: float) -> None:
        """
        Choose nearest job based on priority:
        1) If carrying, nearest silo.
        2) Pending seeds.
        3) Ready plants.
        """
        # Priority 1: carrying -> go to silo
        if self.carried_plant_type:
            silos = [t for t in tiles if t.has_silo]
            self.target_tile = self._nearest_tile(silos)
            return

        # Priority 2: pending seeds
        pending_tiles = [
            t
            for t in tiles
            if t.pending_plant_type is not None and t.purchased and not t.has_silo
        ]
        if pending_tiles:
            self.target_tile = self._nearest_tile(pending_tiles)
            return

        # Priority 3: ready plants
        ready_tiles = [t for t in tiles if t.plant and t.plant.is_ready(current_time)]
        self.target_tile = self._nearest_tile(ready_tiles)

    def _nearest_tile(self, tiles: List["Tile"]) -> Optional["Tile"]:
        best_tile: Optional["Tile"] = None
        best_dist = float("inf")
        for t in tiles:
            tx, ty = t.rect.center
            dx = tx - self.x
            dy = ty - self.y
            dist2 = dx * dx + dy * dy
            if dist2 < best_dist:
                best_dist = dist2
                best_tile = t
        return best_tile

    def update(self, game: "Game", dt: float) -> None:
        """
        Move toward target and perform planting/harvesting/delivery.
        """
        if self._needs_new_target(game):
            self.find_target(game.tiles, game.game_time)
        if self.target_tile is None:
            return

        tx, ty = self.target_tile.rect.center
        dx = tx - self.x
        dy = ty - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 4:
            self._on_arrival(game)
            return

        if dist > 0:
            nx = dx / dist
            ny = dy / dist
            self.x += nx * self.speed * dt
            self.y += ny * self.speed * dt

    def _needs_new_target(self, game: "Game") -> bool:
        if self.target_tile is None:
            return True

        # If carrying, target must be a silo
        if self.carried_plant_type:
            return not self.target_tile.has_silo

        # Not carrying: target must still be valid pending or ready
        if self.target_tile.pending_plant_type is not None:
            return False
        return not (
            self.target_tile.plant
            and self.target_tile.plant.is_ready(game.game_time)
        )

    def _on_arrival(self, game: "Game") -> None:
        tile = self.target_tile
        if tile is None:
            return

        # Deliver if carrying and at silo
        if self.carried_plant_type and tile.has_silo:
            if game.deposit_carried_crop(self.carried_plant_type, tile):
                self.carried_plant_type = None
            self.target_tile = None
            return

        # Plant pending seed
        if (
            not self.carried_plant_type
            and tile.pending_plant_type is not None
            and tile.plant is None
        ):
            pt = tile.pending_plant_type
            tile.plant = PlantInstance(pt, game.game_time)
            tile.pending_plant_type = None
            self.target_tile = None
            return

        # Harvest ready plant (pick up)
        if (
            not self.carried_plant_type
            and tile.plant is not None
            and tile.plant.is_ready(game.game_time)
        ):
            picked = game.pick_crop_from_tile(tile)
            if picked:
                self.carried_plant_type = picked
            self.target_tile = None

    def draw(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(0, 0, 18, 18)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.rect(surface, (100, 200, 255), rect)
