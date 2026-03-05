"""
trafico/agentes_trafico.py:, Este es el agente Vehículo con perfil de riesgo e intención de giro en intersecciones.
"""

from __future__ import annotations  # compat tipos

from dataclasses import dataclass  # para Vehiculo
from typing import Literal  # EstadoVehiculo, IntencionGiro
from motor.sim_base import AgenteBase  # herencia

EstadoVehiculo = Literal["en_cola", "cruzando", "en_interseccion", "fuera", "accidentado"]  # estados posibles
IntencionGiro = Literal["recto", "izquierda", "derecha"]  # opciones de giro


@dataclass  # decorador
class Vehiculo(AgenteBase):  # agente vehículo
    direccion: str = "norte"  # norte/sur/este/oeste
    estado: EstadoVehiculo = "en_cola"  # estado actual
    espera_acumulada: int = 0  # ticks esperando
    intencion: str = "recto"  # alias compat
    intencion_giro: str = "recto"  # recto/izq/der en próxima intersección
    perfil_riesgo: float = 1.0  # escala violación amarillo/rojo (1.0 = normal)

    def __post_init__(self) -> None:
        if self.direccion not in ("norte", "sur", "este", "oeste"):  # validar dirección
            raise ValueError("direccion debe ser norte, sur, este u oeste")
        intencion = getattr(self, "intencion", None)  # por si viene de versión vieja
        intencion_giro = getattr(self, "intencion_giro", None)
        if intencion and not intencion_giro:  # sincronizar si solo tiene intencion
            self.intencion_giro = intencion
        elif intencion_giro and not intencion:  # sincronizar si solo tiene intencion_giro
            self.intencion = intencion_giro
        if getattr(self, "intencion_giro", None) not in ("recto", "izquierda", "derecha"):  # corregir si viene mal
            self.intencion_giro = "recto"
        if getattr(self, "intencion", None) not in ("recto", "izquierda", "derecha"):  # idem
            self.intencion = "recto"
