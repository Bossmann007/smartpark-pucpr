# Fita NeoPixel falsa: grava as cores em out.json.
import machine


class NeoPixel:
    def __init__(self, pin, n):
        self.n = n
        self._px = [(0, 0, 0)] * n

    def __setitem__(self, i, cor):
        self._px[i] = tuple(cor)

    def __getitem__(self, i):
        return self._px[i]

    def __len__(self):
        return self.n

    def fill(self, cor):
        self._px = [tuple(cor)] * self.n

    def write(self):
        machine._saida("neopixel", [list(c) for c in self._px])
