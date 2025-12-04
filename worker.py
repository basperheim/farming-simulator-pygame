from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from tile import Tile
    from main import Game


class Worker:
    def __init__(self, x: float, y: float, speed: float = 70.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.target_tile: Optional["Tile"] = None

    def find_target(self, tiles: List["Tile"], current_time: float) -> None:
        """
        Choose nearest tile with a ready plant.
        """
        ready_tiles = [t for t in tiles if t.plant and t.plant.is_ready(current_time)]
        if not ready_tiles:
            self.target_tile = None
            return

        best_tile: Optional["Tile"] = None
        best_dist = float("inf")
        for t in ready_tiles:
            tx, ty = t.rect.center
            dx = tx - self.x
            dy = ty - self.y
            dist2 = dx * dx + dy * dy
            if dist2 < best_dist:
                best_dist = dist2
                best_tile = t
        self.target_tile = best_tile

    def update(self, game: "Game", dt: float) -> None:
        """
        Move toward target and harvest when reaching it.
        """
        if self.target_tile is None or not (
            self.target_tile.plant
            and self.target_tile.plant.is_ready(game.game_time)
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

    def draw(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(0, 0, 18, 18)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.rect(surface, (100, 200, 255), rect)
