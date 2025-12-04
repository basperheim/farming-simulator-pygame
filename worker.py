from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

import pygame  # only needed if you later draw workers here; safe to keep for now

if TYPE_CHECKING:
    from tile import Tile
    from main import Game  # only for type hints, not required at runtime


class Worker:
    """
    Autonomous worker that moves around the grid and harvests ready crops.

    Attributes:
    - x, y: current pixel position
    - speed: movement speed in pixels/second
    - target_tile: Tile the worker is currently heading toward, if any
    """

    def __init__(self, x: float, y: float, speed: float = 70.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.target_tile: Optional["Tile"] = None

    def find_target(self, tiles: List["Tile"], current_time: float) -> None:
        """
        Pick the nearest tile with a fully grown plant.
        If none exist, clears target_tile.
        """
        ready_tiles = [t for t in tiles if t.plant and t.plant.is_ready(current_time)]
        if not ready_tiles:
            self.target_tile = None
            return

        best_tile: Optional["Tile"] = None
        best_dist_sq = float("inf")

        for t in ready_tiles:
            tx, ty = t.rect.center
            dx = tx - self.x
            dy = ty - self.y
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_tile = t

        self.target_tile = best_tile

    def update(self, game: "Game", dt: float) -> None:
        """
        Move toward the current target tile, harvesting when reached.

        `game` must provide:
        - game.game_time: current game time in seconds
        - game.tiles: list of all tiles
        - game.harvest_tile(tile): function to harvest a tile
        """
        # If target is gone or no longer ready, choose a new one
        if (
            self.target_tile is None
            or not (
                self.target_tile.plant
                and self.target_tile.plant.is_ready(game.game_time)
            )
        ):
            self.find_target(game.tiles, game.game_time)

        if self.target_tile is None:
            return

        tx, ty = self.target_tile.rect.center
        dx = tx - self.x
        dy = ty - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < 4:
            # Harvest instantly on arrival
            game.harvest_tile(self.target_tile)
            self.target_tile = None
            return

        if dist > 0:
            nx = dx / dist
            ny = dy / dist
            self.x += nx * self.speed * dt
            self.y += ny * self.speed * dt
