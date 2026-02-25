import os, sys
import pygame

def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SoundBank:
    def __init__(self):
        pygame.mixer.init()

        self.metal_pipe = pygame.mixer.Sound(resource_path("Sounds/Metal Pipe Falling.wav"))
        self.metal_pipe.set_volume(0.3)

        self.incorrect_buzzer = pygame.mixer.Sound(resource_path("Sounds/Incorrect Buzzer.wav"))
        self.incorrect_buzzer.set_volume(0.5)

        self.correct = pygame.mixer.Sound(resource_path("Sounds/Correct.wav"))
        self.correct.set_volume(0.5)