from __future__ import annotations

from typing import Callable
import pygame


class Button:
    """
    Simple clickable UI button.

    - rect: pygame.Rect region
    - text: label text
    - callback: function called when clicked, signature callback(button)
    - toggle: if True, behaves like a toggle button (toggled on/off)
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Callable[["Button"], None],
        toggle: bool = False,
    ):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.toggle = toggle
        self.toggled = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.toggle:
                    self.toggled = not self.toggled
                self.callback(self)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, disabled: bool = False) -> None:
        color = (80, 80, 80)
        if self.toggle and self.toggled:
            color = (60, 120, 60)
        if disabled:
            color = (60, 60, 60)

        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)

        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
