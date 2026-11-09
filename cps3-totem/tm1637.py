# Driver simples do display TM1637 (4 digitos de 7 segmentos).
# Usa 2 fios (CLK e DIO): inicio, bytes com o bit menos significativo
# primeiro, um pulso de confirmacao (ack) depois de cada byte e fim.
import time
from machine import Pin

# segmentos de cada numero (bit 0 = segmento a ... bit 6 = segmento g)
DIGITOS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
TRACO = 0x40
APAGADO = 0x00


class TM1637:
    def __init__(self, clk, dio, brilho=7):
        self.clk = Pin(clk, Pin.OUT, value=0)
        self.dio = Pin(dio, Pin.OUT, value=0)
        self.brilho = brilho
        self.mostrar([APAGADO] * 4)

    def espera(self):
        time.sleep_us(10)

    def inicio(self):
        self.dio(0)
        self.espera()
        self.clk(0)
        self.espera()

    def fim(self):
        self.dio(0)
        self.espera()
        self.clk(1)
        self.espera()
        self.dio(1)

    def enviar_byte(self, b):
        for i in range(8):
            self.dio((b >> i) & 1)
            self.espera()
            self.clk(1)
            self.espera()
            self.clk(0)
            self.espera()
        # pulso do ack (o TM1637 puxa o DIO para baixo, a gente nao le)
        self.clk(1)
        self.espera()
        self.clk(0)
        self.espera()

    def mostrar(self, segmentos):
        """Escreve os 4 digitos e liga o display."""
        self.inicio()
        self.enviar_byte(0x40)   # modo escrita, endereco anda sozinho
        self.fim()
        self.inicio()
        self.enviar_byte(0xC0)   # comeca no primeiro digito
        for s in segmentos:
            self.enviar_byte(s)
        self.fim()
        self.inicio()
        self.enviar_byte(0x88 | (self.brilho & 7))   # liga o display com brilho de 0 a 7
        self.fim()

    def numero(self, n):
        """Mostra um numero de 0 a 9999 alinhado a direita."""
        texto = str(max(0, min(9999, n)))
        texto = " " * (4 - len(texto)) + texto
        self.mostrar([APAGADO if c == " " else DIGITOS[int(c)] for c in texto])

    def tracos(self):
        self.mostrar([TRACO] * 4)
