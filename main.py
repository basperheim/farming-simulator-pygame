import pygame
import sys
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# --- Constants ---
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
UI_PANEL_HEIGHT = 160
FPS = 60

GRID_COLS = 10
GRID_ROWS = 6
TILE_SIZE = 64
GRID_MARGIN_X = 20
GRID_MARGIN_Y = 20

GAME_DURATION = 600.0  # seconds, 10 minutes

STARTING_MONEY = 10000.0
LAND_COST = 500.0
WORKER_COST = 2000.0
WORKER_UPKEEP_PER_SECOND = 5.0

SILO_COST = 3000.0
BASE_STORAGE = 50
SILO_CAPACITY = 50

PLANT_BUTTON_WIDTH = 120
BUTTON_HEIGHT = 32

PRICE_UPDATE_INTERVAL = 20.0  # seconds
PRICE_HISTORY_LENGTH = 10


@dataclass
class PlantType:
    name: str
    color: tuple
    grow_time: float  # seconds
    seed_cost: float  # baseline seed cost
    sell_price: float  # baseline sell price


@dataclass
class PriceHistory:
    base_price: float
    current_multiplier: float = 1.0
    history: List[float] = field(default_factory=list)


class PlantInstance:
    def __init__(self, plant_type: PlantType, planted_time: float):
        self.plant_type = plant_type
        self.planted_time = planted_time

    def is_ready(self, current_time: float) -> bool:
        return (current_time - self.planted_time) >= self.plant_type.grow_time

    def progress(self, current_time: float) -> float:
        return max(
            0.0,
            min(1.0, (current_time - self.planted_time) / self.plant_type.grow_time),
        )


class Tile:
    def __init__(self, grid_x: int, grid_y: int, rect: pygame.Rect):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.rect = rect
        self.purchased = False
        self.plant: Optional[PlantInstance] = None
        self.has_silo: bool = False

    def can_plant(self) -> bool:
        # Can't plant on unpurchased land or silo tiles
        return self.purchased and self.plant is None and not self.has_silo


class Worker:
    def __init__(self, x: float, y: float, speed: float = 70.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.target_tile: Optional[Tile] = None

    def find_target(self, tiles: List[Tile], current_time: float):
        # Choose nearest ready tile
        ready_tiles = [t for t in tiles if t.plant and t.plant.is_ready(current_time)]
        if not ready_tiles:
            self.target_tile = None
            return
        best_tile = None
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

    def update(self, game, dt: float):
        # If target gone or no longer ready, find a new one
        if self.target_tile is None or not (
            self.target_tile.plant and self.target_tile.plant.is_ready(game.game_time)
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


class Button:
    def __init__(self, rect: pygame.Rect, text: str, callback, toggle: bool = False):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.toggle = toggle
        self.toggled = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.toggle:
                    self.toggled = not self.toggled
                self.callback(self)

    def draw(self, surface, font, disabled: bool = False):
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


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Fast Farming & Trading Prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 36)

        self.running = True
        self.paused = False
        self.game_time = 0.0
        self.game_over = False

        self.money = STARTING_MONEY
        self.workers: List[Worker] = []
        self.num_silos = 0
        self.inventory: Dict[str, int] = {}

        self.plant_types: List[PlantType] = self.create_plant_types()
        self.price_histories: Dict[str, PriceHistory] = self.create_price_histories()
        self.selected_plant_type: PlantType = self.plant_types[0]

        self.tiles: List[Tile] = self.create_tiles()
        # Start with one worker in the middle
        self.workers.append(
            Worker(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - UI_PANEL_HEIGHT)
        )

        self.buttons: List[Button] = []
        self.silo_mode: bool = False
        self.silo_button: Optional[Button] = None
        self.sell_button: Optional[Button] = None
        self.selected_silo_tile: Optional[Tile] = None

        self.price_update_timer: float = 0.0

        self.create_buttons()

    def create_plant_types(self) -> List[PlantType]:
        # Slower grow times now
        return [
            PlantType("Wheat", (218, 165, 32), 15.0, 50.0, 80.0),
            PlantType("Corn", (255, 215, 0), 25.0, 80.0, 150.0),
            PlantType("Berries", (178, 34, 34), 40.0, 120.0, 260.0),
            PlantType("Pumpkin", (255, 140, 0), 60.0, 160.0, 340.0),
        ]

    def create_price_histories(self) -> Dict[str, PriceHistory]:
        histories: Dict[str, PriceHistory] = {}
        for pt in self.plant_types:
            ph = PriceHistory(base_price=pt.sell_price)
            ph.history.append(pt.sell_price)
            histories[pt.name] = ph
        return histories

    def create_tiles(self) -> List[Tile]:
        tiles = []
        start_x = GRID_MARGIN_X
        start_y = GRID_MARGIN_Y
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                rect = pygame.Rect(
                    start_x + x * TILE_SIZE,
                    start_y + y * TILE_SIZE,
                    TILE_SIZE - 2,
                    TILE_SIZE - 2,
                )
                tiles.append(Tile(x, y, rect))
        return tiles

    def create_buttons(self):
        panel_top = WINDOW_HEIGHT - UI_PANEL_HEIGHT + 10
        x = 20

        # Plant selection buttons
        for pt in self.plant_types:
            rect = pygame.Rect(x, panel_top, PLANT_BUTTON_WIDTH, BUTTON_HEIGHT)

            def make_callback(plant_type):
                def callback(btn):
                    self.selected_plant_type = plant_type
                    # untoggle other plant buttons
                    plant_names = [p.name for p in self.plant_types]
                    for b in self.buttons:
                        if b.toggle and b is not btn and b.text in plant_names:
                            b.toggled = False
                    # turning off silo mode when selecting plants
                    if self.silo_button is not None:
                        self.silo_button.toggled = False
                    self.silo_mode = False

                return callback

            btn = Button(rect, pt.name, make_callback(pt), toggle=True)
            if pt is self.selected_plant_type:
                btn.toggled = True
            self.buttons.append(btn)
            x += PLANT_BUTTON_WIDTH + 10

        panel_top += BUTTON_HEIGHT + 10
        x = 20

        # Buy worker
        def buy_worker(_btn):
            if self.money >= WORKER_COST and not self.game_over:
                self.money -= WORKER_COST
                self.workers.append(
                    Worker(
                        WINDOW_WIDTH // 2,
                        WINDOW_HEIGHT // 2 - UI_PANEL_HEIGHT,
                    )
                )

        rect = pygame.Rect(x, panel_top, 140, BUTTON_HEIGHT)
        self.buttons.append(Button(rect, "Buy Worker", buy_worker))
        x += 150

        # Dismiss worker
        def dismiss_worker(_btn):
            if self.workers and not self.game_over:
                self.workers.pop()

        rect = pygame.Rect(x, panel_top, 160, BUTTON_HEIGHT)
        self.buttons.append(Button(rect, "Dismiss Worker", dismiss_worker))
        x += 170

        # Build silo (toggle: place silo on a purchased empty tile)
        def silo_mode_toggle(btn):
            if self.game_over:
                btn.toggled = False
                self.silo_mode = False
                return
            self.silo_mode = btn.toggled
            # deselect any silo when entering build mode
            if self.silo_mode:
                self.selected_silo_tile = None

        rect = pygame.Rect(x, panel_top, 140, BUTTON_HEIGHT)
        silo_button = Button(rect, "Build Silo", silo_mode_toggle, toggle=True)
        self.silo_button = silo_button
        self.buttons.append(silo_button)
        x += 150

        # Sell all – appears only when a silo is selected
        def sell_all(_btn):
            if not self.game_over:
                self.sell_inventory()

        rect = pygame.Rect(x, panel_top, 140, BUTTON_HEIGHT)
        self.sell_button = Button(rect, "Sell All", sell_all)
        x += 150

        # Pause
        def toggle_pause(btn):
            if not self.game_over:
                self.paused = not self.paused
                btn.toggled = self.paused

        rect = pygame.Rect(x, panel_top, 120, BUTTON_HEIGHT)
        pause_button = Button(rect, "Pause", toggle_pause, toggle=True)
        self.buttons.append(pause_button)

    @property
    def storage_capacity(self) -> int:
        return BASE_STORAGE + self.num_silos * SILO_CAPACITY

    @property
    def inventory_total(self) -> int:
        return sum(self.inventory.values())

    def get_price_info(self, plant_type: PlantType):
        ph = self.price_histories[plant_type.name]
        sell_price = ph.base_price * ph.current_multiplier
        # Seed price keeps same ratio as baseline
        ratio = plant_type.seed_cost / plant_type.sell_price
        seed_price = sell_price * ratio
        return sell_price, seed_price

    def harvest_tile(self, tile: Tile):
        if not tile.plant:
            return
        # enforce storage
        if self.inventory_total >= self.storage_capacity:
            # storage full, can't harvest
            return
        ptype = tile.plant.plant_type
        self.inventory[ptype.name] = self.inventory.get(ptype.name, 0) + 1
        tile.plant = None

    def sell_inventory(self):
        for ptype in self.plant_types:
            count = self.inventory.get(ptype.name, 0)
            if count > 0:
                sell_price, _ = self.get_price_info(ptype)
                self.money += count * sell_price
                self.inventory[ptype.name] = 0

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if not self.paused and not self.game_over:
                self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    if not self.game_over:
                        self.paused = not self.paused
                        # keep pause button visual in sync if it exists
                        for b in self.buttons:
                            if b.text == "Pause":
                                b.toggled = self.paused
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Buttons
                for btn in self.buttons:
                    btn.handle_event(event)
                if self.selected_silo_tile is not None and self.sell_button is not None:
                    self.sell_button.handle_event(event)

                # Tiles (only when clicking in grid area)
                pos = event.pos
                if pos[1] < WINDOW_HEIGHT - UI_PANEL_HEIGHT:
                    self.handle_tile_click(pos)

    def handle_tile_click(self, pos):
        clicked_any = False
        for tile in self.tiles:
            if tile.rect.collidepoint(pos):
                clicked_any = True
                # Step 1: buy land if unpurchased
                if not tile.purchased:
                    if self.money >= LAND_COST and not self.game_over:
                        self.money -= LAND_COST
                        tile.purchased = True
                    self.selected_silo_tile = None
                    return

                # Step 2: if silo mode, try to build silo on this purchased tile
                if self.silo_mode:
                    if (
                        not tile.has_silo
                        and tile.plant is None
                        and self.money >= SILO_COST
                        and not self.game_over
                    ):
                        self.money -= SILO_COST
                        tile.has_silo = True
                        self.num_silos += 1
                        self.selected_silo_tile = tile
                    # exit silo mode after one placement attempt (successful or not)
                    self.silo_mode = False
                    if self.silo_button is not None:
                        self.silo_button.toggled = False
                    return

                # Step 3: clicking on an existing silo selects it
                if tile.has_silo:
                    self.selected_silo_tile = tile
                    return

                # Step 4: normal planting behavior
                self.selected_silo_tile = None
                if tile.can_plant() and not self.game_over:
                    pt = self.selected_plant_type
                    sell_price, seed_price = self.get_price_info(pt)
                    if self.money >= seed_price:
                        self.money -= seed_price
                        tile.plant = PlantInstance(pt, self.game_time)
                return

        if not clicked_any:
            # click outside any tile clears silo selection
            self.selected_silo_tile = None

    def update_prices(self):
        for pt in self.plant_types:
            ph = self.price_histories[pt.name]
            # small random walk with mean reversion
            delta = random.uniform(-0.08, 0.08)  # +/-8%
            ph.current_multiplier += delta + (1.0 - ph.current_multiplier) * 0.1
            ph.current_multiplier = max(0.5, min(1.5, ph.current_multiplier))
            price = ph.base_price * ph.current_multiplier
            ph.history.append(price)
            if len(ph.history) > PRICE_HISTORY_LENGTH:
                ph.history.pop(0)

    def update(self, dt: float):
        if self.game_over:
            return

        self.game_time += dt
        if self.game_time >= GAME_DURATION:
            self.game_over = True
            self.paused = True

        # Worker upkeep – per second
        self.money -= WORKER_UPKEEP_PER_SECOND * len(self.workers) * dt

        # Update workers (they auto-harvest ready crops)
        for w in self.workers:
            w.update(self, dt)

        # Update price timer
        self.price_update_timer += dt
        if self.price_update_timer >= PRICE_UPDATE_INTERVAL:
            self.price_update_timer -= PRICE_UPDATE_INTERVAL
            self.update_prices()

    def draw_grid(self):
        for tile in self.tiles:
            # base color: unpurchased vs purchased
            if not tile.purchased:
                color = (40, 40, 40)
            else:
                color = (50, 90, 50)

            pygame.draw.rect(self.screen, color, tile.rect)

            # Silo rendering has highest priority
            if tile.has_silo:
                silo_rect = tile.rect.inflate(
                    -tile.rect.width * 0.25, -tile.rect.height * 0.25
                )
                pygame.draw.rect(self.screen, (130, 130, 130), silo_rect)
                pygame.draw.rect(self.screen, (220, 220, 220), silo_rect, 2)
                # small "S" label
                s_surf = self.font.render("S", True, (255, 255, 255))
                s_rect = s_surf.get_rect(center=silo_rect.center)
                self.screen.blit(s_surf, s_rect)

                # highlight selected silo
                if tile is self.selected_silo_tile:
                    pygame.draw.rect(self.screen, (0, 200, 255), tile.rect, 3)
                continue  # don't draw crops on silo tiles

            # plant rendering
            if tile.plant:
                pt = tile.plant.plant_type
                prog = tile.plant.progress(self.game_time)
                plant_rect = tile.rect.inflate(
                    -tile.rect.width * 0.3, -tile.rect.height * 0.3
                )
                filled_height = int(plant_rect.height * prog)
                filled_rect = pygame.Rect(
                    plant_rect.left,
                    plant_rect.bottom - filled_height,
                    plant_rect.width,
                    filled_height,
                )
                pygame.draw.rect(self.screen, pt.color, filled_rect)

                if tile.plant.is_ready(self.game_time):
                    pygame.draw.rect(self.screen, (255, 255, 255), tile.rect, 2)
            else:
                # border for purchased but empty land
                if tile.purchased:
                    pygame.draw.rect(self.screen, (80, 130, 80), tile.rect, 1)

    def draw_workers(self):
        for w in self.workers:
            rect = pygame.Rect(0, 0, 18, 18)
            rect.center = (int(w.x), int(w.y))
            pygame.draw.rect(self.screen, (100, 200, 255), rect)

    def draw_ui_panel(self):
        panel_rect = pygame.Rect(
            0, WINDOW_HEIGHT - UI_PANEL_HEIGHT, WINDOW_WIDTH, UI_PANEL_HEIGHT
        )
        pygame.draw.rect(self.screen, (20, 20, 20), panel_rect)
        pygame.draw.line(
            self.screen,
            (80, 80, 80),
            (0, panel_rect.top),
            (WINDOW_WIDTH, panel_rect.top),
            2,
        )

        # Buttons (always-visible)
        for btn in self.buttons:
            btn.draw(self.screen, self.font)

        # Conditional Sell All button
        if self.selected_silo_tile is not None and self.sell_button is not None:
            self.sell_button.draw(self.screen, self.font)

        # Info text
        info_y = panel_rect.top + UI_PANEL_HEIGHT - 70
        money_text = f"Money: ${int(self.money):,}"
        workers_text = (
            f"Workers: {len(self.workers)}  (Upkeep: ${WORKER_UPKEEP_PER_SECOND:.0f}/s each)"
        )
        silo_text = (
            f"Silos: {self.num_silos}  Storage: {self.inventory_total}/{self.storage_capacity}"
        )
        time_left = max(0, int(GAME_DURATION - self.game_time))
        time_text = f"Time left: {time_left // 60:02d}:{time_left % 60:02d}"

        if self.selected_silo_tile is not None:
            inv_header = "Inventory (global):"
            inv_lines = []
            for pt in self.plant_types:
                count = self.inventory.get(pt.name, 0)
                sell_price, seed_price = self.get_price_info(pt)
                inv_lines.append(
                    f"{pt.name}: {count}  Sell ${int(sell_price)}  Seed ${int(seed_price)}"
                )
            inv_texts = [inv_header] + inv_lines
        else:
            inv_texts = ["Click a silo to inspect inventory & prices."]

        texts = [money_text, workers_text, silo_text, time_text] + inv_texts
        for i, t in enumerate(texts):
            surf = self.font.render(t, True, (220, 220, 220))
            self.screen.blit(surf, (20, info_y + i * 18))

    def draw_price_panel(self):
        # Panel on the right side of the grid
        grid_right = GRID_MARGIN_X + GRID_COLS * TILE_SIZE
        panel_left = grid_right + 20
        panel_top = GRID_MARGIN_Y
        panel_width = WINDOW_WIDTH - panel_left - 20
        panel_height = GRID_ROWS * TILE_SIZE

        rect = pygame.Rect(panel_left, panel_top, panel_width, panel_height)
        pygame.draw.rect(self.screen, (15, 15, 15), rect)
        pygame.draw.rect(self.screen, (60, 60, 60), rect, 2)

        if self.selected_silo_tile is None:
            msg = "Click a silo to view\nprice history and inventory."
            for i, line in enumerate(msg.splitlines()):
                surf = self.font.render(line, True, (200, 200, 200))
                self.screen.blit(
                    surf,
                    (panel_left + 10, panel_top + 10 + i * 22),
                )
            return

        # Draw mini graphs for each crop
        n = len(self.plant_types)
        if n == 0:
            return

        section_height = panel_height // n
        for idx, pt in enumerate(self.plant_types):
            ph = self.price_histories[pt.name]
            section_top = panel_top + idx * section_height
            section_rect = pygame.Rect(
                panel_left + 5, section_top + 5, panel_width - 10, section_height - 10
            )
            pygame.draw.rect(self.screen, (25, 25, 25), section_rect)
            pygame.draw.rect(self.screen, (80, 80, 80), section_rect, 1)

            # Title and current price / count
            sell_price, seed_price = self.get_price_info(pt)
            count = self.inventory.get(pt.name, 0)
            title = f"{pt.name}: ${int(sell_price)} (seed ${int(seed_price)})  x{count}"
            title_surf = self.font.render(title, True, (220, 220, 220))
            self.screen.blit(title_surf, (section_rect.left + 4, section_rect.top + 2))

            # Graph area
            graph_margin_top = 20
            graph_rect = pygame.Rect(
                section_rect.left + 4,
                section_rect.top + graph_margin_top,
                section_rect.width - 8,
                section_rect.height - graph_margin_top - 6,
            )
            pygame.draw.rect(self.screen, (10, 10, 10), graph_rect)
            pygame.draw.rect(self.screen, (60, 60, 60), graph_rect, 1)

            points = ph.history
            if len(points) < 2:
                continue

            min_price = min(points)
            max_price = max(points)
            if max_price == min_price:
                max_price += 1.0  # avoid div by zero

            # baseline line (base price)
            base_y = graph_rect.bottom - (
                (ph.base_price - min_price) / (max_price - min_price)
            ) * graph_rect.height
            pygame.draw.line(
                self.screen,
                (80, 80, 80),
                (graph_rect.left, int(base_y)),
                (graph_rect.right, int(base_y)),
                1,
            )

            # Price lines
            step_x = graph_rect.width / (len(points) - 1)
            prev_x = graph_rect.left
            prev_y = graph_rect.bottom - (
                (points[0] - min_price) / (max_price - min_price)
            ) * graph_rect.height

            for i in range(1, len(points)):
                x = graph_rect.left + step_x * i
                y = graph_rect.bottom - (
                    (points[i] - min_price) / (max_price - min_price)
                ) * graph_rect.height
                color = (0, 200, 0) if points[i] >= points[i - 1] else (200, 0, 0)
                pygame.draw.line(self.screen, color, (prev_x, prev_y), (x, y), 2)
                prev_x, prev_y = x, y

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        msg = "Time's up!"
        msg2 = f"Final money: ${int(self.money):,}"
        surf1 = self.big_font.render(msg, True, (255, 255, 255))
        surf2 = self.big_font.render(msg2, True, (255, 255, 0))
        rect1 = surf1.get_rect(
            center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30)
        )
        rect2 = surf2.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
        self.screen.blit(surf1, rect1)
        self.screen.blit(surf2, rect2)

    def draw(self):
        self.screen.fill((10, 10, 10))
        self.draw_grid()
        self.draw_workers()
        self.draw_price_panel()
        self.draw_ui_panel()
        if self.game_over:
            self.draw_game_over()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
