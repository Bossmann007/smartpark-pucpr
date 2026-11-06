# Wi-Fi falso: no Mac a rede já existe.
STA_IF = 0


class WLAN:
    def __init__(self, interface=STA_IF):
        self._ativo = False

    def active(self, v=None):
        if v is not None:
            self._ativo = v
        return self._ativo

    def connect(self, ssid, senha=""):
        pass

    def isconnected(self):
        return True

    def ifconfig(self):
        return ("10.10.0.2", "255.255.255.0", "10.10.0.1", "8.8.8.8")
