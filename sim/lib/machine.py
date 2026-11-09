# Hardware falso para rodar os main.py no MicroPython do Mac (teste local).
# Não vai para o Wokwi. Entradas vêm de <DIR>/in.json; saídas vão para <DIR>/out.json.
import json
import os
from sim_config import DIR

_IN = DIR + "/in.json"
_OUT = DIR + "/out.json"
_out = {}
_irqs = []   # [pino, handler, último nível]: interrupções emuladas por leitura


def _ler():
    try:
        with open(_IN) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _gravar():
    with open(_OUT + ".tmp", "w") as f:
        json.dump(_out, f)
    os.rename(_OUT + ".tmp", _OUT)


def _saida(chave, valor):
    if _out.get(chave) != valor:
        _out[chave] = valor
        _gravar()


def _verificar_irqs():
    pins = _ler().get("pins", {}) if _irqs else {}
    for item in _irqs:
        pino, handler, antes = item
        nivel = pins.get(str(pino.id), 1 if pino.pull == Pin.PULL_UP else 0)
        item[2] = nivel
        if antes == 1 and nivel == 0:
            handler(pino)


class Pin:
    IN = 1
    OUT = 3
    PULL_UP = 1
    PULL_DOWN = 2
    IRQ_RISING = 1
    IRQ_FALLING = 2

    def __init__(self, id, mode=-1, pull=-1, value=None):
        self.id = id
        self.mode = mode
        self.pull = pull
        if value is not None:
            self.value(value)

    def init(self, mode=-1, pull=-1, value=None):
        self.mode = mode
        if pull != -1:
            self.pull = pull
        if value is not None:
            self.value(value)

    def irq(self, trigger=IRQ_FALLING, handler=None):
        _irqs.append([self, handler, 1])

    def value(self, v=None):
        if v is None:
            _verificar_irqs()
            if self.mode == Pin.OUT:
                return _out.get("pin%d" % self.id, 0)
            padrao = 1 if self.pull == Pin.PULL_UP else 0
            return _ler().get("pins", {}).get(str(self.id), padrao)
        _saida("pin%d" % self.id, 1 if v else 0)

    def __call__(self, v=None):
        return self.value(v)

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)


class PWM:
    def __init__(self, pin, freq=0, duty_u16=None):
        self.pin = pin
        self._freq = freq
        self._duty = 0 if duty_u16 is None else duty_u16
        self._salvar()

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f
        self._salvar()

    def duty_u16(self, d=None):
        if d is None:
            return self._duty
        self._duty = d
        self._salvar()

    def _salvar(self):
        _saida("pwm%d" % self.pin.id, [self._freq, self._duty])


def time_pulse_us(pin, nivel, timeout_us=1000000):
    _verificar_irqs()
    cm = _ler().get("dist", {}).get(str(pin.id), 400)
    us = int(cm * 2 / 0.0343)
    return -1 if us > timeout_us else us
