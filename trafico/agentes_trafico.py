"""
trafico/agentes_trafico.py
-------------------------
Agente Vehículo con perfil de riesgo (escala probabilidades de violación).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from motor.sim_base import AgenteBase

EstadoVehiculo = Literal["en_cola", "cruzando", "en_interseccion", "fuera", "accidentado"]


@dataclass
class Vehiculo(AgenteBase):
    direccion: str = "norte"
    estado: EstadoVehiculo = "en_cola"
    espera_acumulada: int = 0
    intencion: str = "recto"
    # Perfil de riesgo: escala p_pasarse_amarillo y p_pasarse_rojo (1.0 = normal)
    perfil_riesgo: float = 1.0

    def __post_init__(self) -> None:
        if self.direccion not in ("norte", "sur", "este", "oeste"):
            raise ValueError("direccion debe ser norte, sur, este u oeste")
