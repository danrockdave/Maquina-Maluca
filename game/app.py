"""Application loop: events -> update -> draw into the framebuffer -> show matrix."""
import pygame
from gfx.raster import make_framebuffer
from gfx.texture import load_all
from game.audio import Audio
from game import config as C


class App:
    def __init__(self, screen):
        self.screen = screen
        self.fb = make_framebuffer(C.SCREEN_W, C.SCREEN_H, C.BG)
        self.textures = load_all(C.TEXTURE_NAMES)
        self.audio = Audio()
        self.clock = pygame.time.Clock()
        self.scene = None
        self.running = True

    def set_scene(self, scene):
        self.scene = scene

    def quit(self):
        self.running = False

    def run(self):
        from game.scenes import SplashScene
        self.set_scene(SplashScene(self))
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.fb)
            # The only "graphics library" call: show the numeric matrix as an image
            pygame.surfarray.blit_array(self.screen, self.fb)
            pygame.display.flip()
        pygame.quit()
