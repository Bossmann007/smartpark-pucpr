# Driver mínimo do display de 7 segmentos TM1637 (4 dígitos) para MicroPython.
# Protocolo de 2 fios (CLK e DIO): início, bytes com o bit menos significativo
# primeiro, um pulso de confirmação (ack) por byte e fim.
import time
from machine import Pin

# Segmentos de cada dígito (bit 0 = segmento a ... bit 6 = segmento g)
DIGITOS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
TRACO = 0x40
APAGADO = 0x00


class TM1637:
    def __init__(self, clk, dio, brilho=7):
        self.clk = Pin(clk, Pin.OUT, value=0)
        self.dio = Pin(dio, Pin.OUT, value=0)
        self.brilho = brilho
        self.mostrar([APAGADO] * 4)

    def _espera(self):
        time.sleep_us(10)

    def _inicio(self):
        self.dio(0)
        self._espera()
        self.clk(0)
        self._espera()

    def _fim(self):
        self.dio(0)
        self._espera()
        self.clk(1)
        self._espera()
        self.dio(1)

    def _byte(self, b):
        for i in range(8):
            self.dio((b >> i) & 1)
            self._espera()
            self.clk(1)
            self._espera()
            self.clk(0)
            self._espera()
        # pulso de confirmação (o TM1637 puxa DIO para baixo; não lemos)
        self.clk(0)
        self._espera()
        self.clk(1)
        self._espera()
        self.clk(0)
        self._espera()

    def mostrar(self, segmentos):
        """Escreve os 4 dígitos (lista de 4 bytes de segmentos) e liga o display."""
        self._inicio()
        self._byte(0x40)            # escrita com endereço automático
        self._fim()
        self._inicio()
        self._byte(0xC0)            # começa no dígito 0
        for s in segmentos:
            self._byte(s)
        self._fim()
        self._inicio()
        self._byte(0x88 | (self.brilho & 7))   # display ligado + brilho 0..7
        self._fim()

    def numero(self, n):
        """Número de 0 a 9999 alinhado à direita, sem zeros à esquerda."""
        texto = str(max(0, min(9999, n)))
        texto = " " * (4 - len(texto)) + texto
        self.mostrar([APAGADO if c == " " else DIGITOS[int(c)] for c in texto])

    def tracos(self):
        self.mostrar([TRACO] * 4)
