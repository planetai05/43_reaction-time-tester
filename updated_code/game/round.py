import random
import pygame


class Round:
    WAITING = "waiting"
    GO = "go"
    RESULT = "result"
    FALSE_START = "false_start"

    def __init__(self, min_wait_ms=1000, max_wait_ms=3000):
        self.wait_delay_ms = random.randint(min_wait_ms, max_wait_ms)
        self.state = self.WAITING
        self.start_time = pygame.time.get_ticks()
        self.go_time = None
        self.reaction_ms = None

    def update(self):
        if self.state != self.WAITING:
            return

        now = pygame.time.get_ticks()
        if now - self.start_time >= self.wait_delay_ms:
            self.state = self.GO
            # The reaction timer starts exactly when the screen changes to green.
            self.go_time = now

    def register_input(self):
        """Return a valid reaction time, or None for a false/ignored input."""
        now = pygame.time.get_ticks()

        if self.state == self.WAITING:
            self.state = self.FALSE_START
            self.reaction_ms = None
            return None

        if self.state == self.GO:
            self.reaction_ms = now - self.go_time
            self.state = self.RESULT
            return self.reaction_ms

        # Inputs during RESULT/FALSE_START are ignored.
        return None
