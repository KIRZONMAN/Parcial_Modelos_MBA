"""
universidad/agentes_uni.py
--------------------------
Define el agente Estudiante para el modelo MBA de Universidad.

Perfiles: afinidad_zona modela preferencias reales (socializar/café, estudiar/biblio, clase/aula).
Hambre: motor de cafetería (aumenta fuera, baja en cafetería).
Permanencia mínima: no puede moverse hasta cumplir tiempo en zona (duración clase/estudio/comida).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from motor.sim_base import AgenteBase


@dataclass
class Estudiante(AgenteBase):
    zona_actual: str = "aula"
    enfriamiento: int = 0
    tiempo_por_zona: Dict[str, int] = None

    # Afinidad: "aula" | "biblioteca" | "cafeteria" — perfiles reales (socializar, estudiar, clase)
    afinidad_zona: str = "aula"

    # Hambre (0..hambre_max): aumenta cada tick fuera de cafetería; baja en cafetería
    hambre: int = 0
    # Desincronizar: umbral personal (rango) y metabolismo (incremento distinto por agente)
    umbral_hambre_personal: float = 10.0  # se asigna al crear
    metabolismo: float = 1.0  # factor por el que se incrementa hambre cada tick (ej. 0.8–1.3)

    # Permanencia mínima: ticks restantes antes de poder decidir moverse
    ticks_restantes_en_zona: int = 0

    # Visitas (cuántas veces entró a cada zona)
    visitas_por_zona: Dict[str, int] = None

    def __post_init__(self) -> None:
        if self.tiempo_por_zona is None:
            self.tiempo_por_zona = {"aula": 0, "biblioteca": 0, "cafeteria": 0}
        if self.visitas_por_zona is None:
            self.visitas_por_zona = {"aula": 0, "biblioteca": 0, "cafeteria": 0}

    # Compatibilidad
    @property
    def agent_id(self) -> int:
        return self.id_agente

    @property
    def cooldown(self) -> int:
        return self.enfriamiento
