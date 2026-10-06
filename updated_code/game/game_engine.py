import math
import struct
from dataclasses import dataclass

import pygame

from .round import Round


WHITE = (245, 245, 245)
BLACK = (25, 25, 25)
GRAY = (90, 90, 90)
GREEN = (40, 180, 90)
RED = (190, 55, 55)
BLUE = (50, 90, 170)
YELLOW = (225, 185, 65)
PANEL = (35, 40, 48)


@dataclass(frozen=True)
class Difficulty:
    wait_min_ms: int
    wait_max_ms: int
    rounds: int


DIFFICULTIES = {
    "Easy": Difficulty(1500, 3000, 3),
    "Medium": Difficulty(1000, 2500, 5),
    "Hard": Difficulty(500, 2000, 7),
}


class SoundEffects:
    """Small generated tones so the project needs no external audio assets."""

    def __init__(self):
        self.sounds = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=1)

            self.sounds["go"] = self._tone_sequence(
                [(880, 90), (1320, 110)], volume=0.25
            )
            self.sounds["false_start"] = self._tone_sequence(
                [(180, 180)], volume=0.30
            )
            self.sounds["end"] = self._tone_sequence(
                [(660, 100), (880, 100), (1175, 160)], volume=0.25
            )
        except pygame.error:
            # Sound is optional; the game remains fully playable without audio.
            self.sounds = {}

    @staticmethod
    def _tone_sequence(tones, volume=0.25, sample_rate=44100):
        raw = bytearray()

        for frequency, duration_ms in tones:
            sample_count = int(sample_rate * duration_ms / 1000)
            for i in range(sample_count):
                envelope = min(1.0, i / max(1, int(sample_rate * 0.01)))
                envelope *= min(
                    1.0,
                    (sample_count - i) / max(1, int(sample_rate * 0.02)),
                )
                sample = math.sin(2 * math.pi * frequency * i / sample_rate)
                value = int(32767 * volume * envelope * sample)
                raw.extend(struct.pack("<h", value))

        return pygame.mixer.Sound(buffer=bytes(raw))

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 21)
        self.big_font = pygame.font.SysFont("Arial", 50)
        self.title_font = pygame.font.SysFont("Arial", 58, bold=True)

        self.sound = SoundEffects()

        self.screen = "game"
        self.difficulty_name = "Medium"
        self.difficulty = DIFFICULTIES[self.difficulty_name]

        self.reaction_times = []
        self.round = None
        self.completed_rounds = 0
        self.result_shown_at = None
        self.pause_ms = 800

        self.start_session(self.difficulty_name)

    def start_session(self, difficulty_name):
        self.difficulty_name = difficulty_name
        self.difficulty = DIFFICULTIES[difficulty_name]
        self.reaction_times = []
        self.completed_rounds = 0
        self.result_shown_at = None
        self.screen = "game"
        self.round = self._new_round()

    def _new_round(self):
        return Round(
            self.difficulty.wait_min_ms,
            self.difficulty.wait_max_ms,
        )

    def handle_event(self, event):
        if self.screen == "game":
            self._handle_game_event(event)
        elif self.screen == "results":
            self._handle_results_event(event)

    def _handle_game_event(self, event):
        is_click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        is_space = event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE

        if not (is_click or is_space):
            return

        reaction_ms = self.round.register_input()

        if self.round.state == Round.FALSE_START:
            self.result_shown_at = pygame.time.get_ticks()
            self.sound.play("false_start")
            return

        if reaction_ms is not None:
            self.reaction_times.append(reaction_ms)
            self.completed_rounds += 1
            self.result_shown_at = pygame.time.get_ticks()

    def _handle_results_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.start_session("Easy")
            elif event.key == pygame.K_2:
                self.start_session("Medium")
            elif event.key == pygame.K_3:
                self.start_session("Hard")
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        for name, rect in self._difficulty_buttons():
            if rect.collidepoint(event.pos):
                self.start_session(name)
                return

        if self._quit_rect().collidepoint(event.pos):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self):
        if self.screen != "game":
            return

        self.round.update()

        if self.round.state not in (Round.RESULT, Round.FALSE_START):
            return

        if self.result_shown_at is None:
            return

        now = pygame.time.get_ticks()
        if now - self.result_shown_at < self.pause_ms:
            return

        self.result_shown_at = None

        if self.round.state == Round.FALSE_START:
            self.round = self._new_round()
            return

        if self.completed_rounds >= self.difficulty.rounds:
            self.screen = "results"
            self.sound.play("end")
        else:
            self.round = self._new_round()

    def average_reaction_ms(self):
        if not self.reaction_times:
            return 0
        return round(sum(self.reaction_times) / len(self.reaction_times))

    def _quit_rect(self):
        return pygame.Rect(self.width // 2 - 110, self.height - 70, 220, 44)

    def _difficulty_buttons(self):
        button_width = 180
        button_height = 50
        gap = 20

        total_width = 3 * button_width + 2 * gap
        start_x = (self.width - total_width) // 2
        y = self.height - 140

        return [
            (
                name,
                pygame.Rect(
                    start_x + i * (button_width + gap),
                    y,
                    button_width,
                    button_height,
                ),
            )
            for i, name in enumerate(("Easy", "Medium", "Hard"))
        ]

    def _draw_centered(self, screen, text, font, color, y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, y))
        screen.blit(surface, rect)

    def render(self, screen):
        if self.screen == "game":
            self._render_game(screen)
        else:
            self._render_results(screen)

    def _render_game(self, screen):
        if self.round.state == Round.WAITING:
            bg = GRAY
            message = "Wait for green..."
        elif self.round.state == Round.GO:
            bg = GREEN
            message = "CLICK / SPACE!"
        elif self.round.state == Round.FALSE_START:
            bg = RED
            message = "FALSE START!"
        else:
            bg = BLUE
            message = f"{self.round.reaction_ms} ms"

        screen.fill(bg)

        self._draw_centered(
            screen, message, self.big_font, WHITE, self.height // 2
        )

        if self.round.state in (Round.RESULT, Round.FALSE_START):
            round_number = max(1, self.completed_rounds)
        else:
            round_number = min(self.completed_rounds + 1, self.difficulty.rounds)

        difficulty_text = self.small_font.render(
            f"{self.difficulty_name}  |  {round_number}/"
            f"{self.difficulty.rounds}",
            True,
            WHITE,
        )
        screen.blit(difficulty_text, (15, 15))

        avg_text = self.small_font.render(
            f"Average: {self.average_reaction_ms()} ms",
            True,
            WHITE,
        )
        screen.blit(avg_text, (15, 45))

        if self.round.state == Round.FALSE_START:
            self._draw_centered(
                screen,
                "Restarting round...",
                self.font,
                WHITE,
                self.height // 2 + 65,
            )
        elif self.round.state == Round.RESULT:
            self._draw_centered(
                screen,
                "Next round...",
                self.font,
                WHITE,
                self.height // 2 + 65,
            )

    def _render_results(self, screen):
        screen.fill(BLACK)

        self._draw_centered(screen, "SESSION COMPLETE", self.title_font, WHITE, 60)
        self._draw_centered(
            screen,
            f"{self.difficulty_name} • Average: {self.average_reaction_ms()} ms",
            self.font,
            YELLOW,
            112,
        )

        # Results panel (scales with window width)
        panel = pygame.Rect(60, 145, self.width - 120, 180)
        pygame.draw.rect(screen, PANEL, panel, border_radius=12)

        col_width = panel.width // 2
        for index, value in enumerate(self.reaction_times, start=1):
            column = (index - 1) % 2
            row = (index - 1) // 2
            x = panel.left + 40 + column * col_width
            y = panel.top + 20 + row * 36
            text_surface = self.small_font.render(
                f"Round {index}: {value} ms", True, WHITE
            )
            screen.blit(text_surface, (x, y))

        # Replay instruction
        buttons = self._difficulty_buttons()
        button_top = buttons[0][1].top
        self._draw_centered(
            screen,
            "Play again — choose a difficulty",
            self.small_font,
            WHITE,
            button_top - 22,
        )

        # Difficulty buttons
        for name, rect in buttons:
            pygame.draw.rect(screen, BLUE, rect, border_radius=8)
            text_surface = self.font.render(name, True, WHITE)
            screen.blit(text_surface, text_surface.get_rect(center=rect.center))

        # Exit button
        quit_rect = self._quit_rect()
        pygame.draw.rect(screen, RED, quit_rect, border_radius=8)
        quit_text = self.small_font.render("Exit (Q / Esc)", True, WHITE)
        screen.blit(quit_text, quit_text.get_rect(center=quit_rect.center))