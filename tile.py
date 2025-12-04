from __future__ import annotations

from typing import Optional
import pygame

from plant_instance import PlantInstance
from plant_type import PlantType


class Tile:
    def __init__(self, grid_x: int, grid_y: int, rect: pygame.Rect):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.rect = rect
        self.purchased: bool = False
        self.plant: Optional[PlantInstance] = None
        self.pending_plant_type: Optional[PlantType] = None
        self.has_silo: bool = False

    def can_plant(self) -> bool:
        """
        You can plant on purchased land that doesn't already have a plant or a silo.
        """
        return (
            self.purchased
            and self.plant is None
            and self.pending_plant_type is None
            and not self.has_silo
        )

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        game_time: float,
        selected_silo_tile: Optional["Tile"],
    ) -> None:
        """
        Draw this tile: land, plant, or silo + selection outline.
        """
        # base color: unpurchased vs purchased
        if not self.purchased:
            color = (40, 40, 40)
        else:
            color = (50, 90, 50)

        pygame.draw.rect(surface, color, self.rect)

        # Silo rendering has highest priority
        if self.has_silo:
            silo_rect = self.rect.inflate(
                -self.rect.width * 0.25, -self.rect.height * 0.25
            )
            pygame.draw.rect(surface, (130, 130, 130), silo_rect)
            pygame.draw.rect(surface, (220, 220, 220), silo_rect, 2)

            # small "S" label
            s_surf = font.render("S", True, (255, 255, 255))
            s_rect = s_surf.get_rect(center=silo_rect.center)
            surface.blit(s_surf, s_rect)

            # highlight selected silo
            if selected_silo_tile is self:
                pygame.draw.rect(surface, (0, 200, 255), self.rect, 3)
            return  # don't draw crops on silo tiles

        # plant rendering
        label_pt: Optional[PlantType] = self.pending_plant_type
        if self.plant:
            pt = self.plant.plant_type
            label_pt = pt
            prog = self.plant.progress(game_time)
            plant_rect = self.rect.inflate(
                -self.rect.width * 0.3, -self.rect.height * 0.3
            )
            filled_height = int(plant_rect.height * prog)
            filled_rect = pygame.Rect(
                plant_rect.left,
                plant_rect.bottom - filled_height,
                plant_rect.width,
                filled_height,
            )
            pygame.draw.rect(surface, pt.color, filled_rect)

            if self.plant.is_ready(game_time):
                pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)
        else:
            # border for purchased but empty land
            if self.purchased:
                pygame.draw.rect(surface, (80, 130, 80), self.rect, 1)

        # Crop label overlay for pending/active crops
        if label_pt:
            letter = label_pt.name[0].upper()
            color = (235, 235, 235)
            if self.pending_plant_type and not self.plant:
                color = (230, 210, 120)
            text_surf = font.render(letter, True, color)
            text_rect = text_surf.get_rect()
            text_rect.midtop = (self.rect.centerx, self.rect.top + 4)
            surface.blit(text_surf, text_rect)
