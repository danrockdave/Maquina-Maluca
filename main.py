"""Máquina Maluca - a 2D arcade puzzle inspired by The Incredible Machine.

Everything on screen is rasterized by hand into a numpy matrix; pygame is used
only to open the window, read input, load textures and display the matrix.
"""
import pygame
from game import config as C
from game.app import App


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
    pygame.display.set_caption("Máquina Maluca")
    App(screen).run()


if __name__ == '__main__':
    main()
