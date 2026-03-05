"""
universidad/agentes_uni.py: Define el agente Estudiante para el modelo MBA de Universidad.

Perfiles: afinidad_zona modela preferencias reales (socializar/café, estudiar/biblio, clase/aula).
Hambre: motor de cafetería (aumenta fuera, baja en cafetería).
Permanencia mínima: no puede moverse hasta cumplir tiempo en zona (duración clase/estudio/comida).
"""

from __future__ import annotations  # compat tipos

from dataclasses import dataclass  # para Estudiante
from typing import Dict  # tiempo_por_zona, visitas_por_zona
from motor.sim_base import AgenteBase  # herencia


@dataclass  # decorador
class Estudiante(AgenteBase):  # agente estudiante
    zona_actual: str = "aula"  # donde está ahora (aula, biblioteca, cafeteria)
    enfriamiento: int = 0  # ticks que faltan para poder moverse otra vez
    tiempo_por_zona: Dict[str, int] = None  # ticks acumulados en cada zona
    afinidad_zona: str = "aula"  # preferencia (socializar/café, estudiar/biblio, clase/aula)
    hambre: int = 0  # sube fuera de cafetería, baja en cafetería
    umbral_hambre_personal: float = 10.0  # se asigna al crear (desincronizar)
    metabolismo: float = 1.0  # factor de subida de hambre por tick (ej. 0.8–1.3)
    ticks_restantes_en_zona: int = 0  # permanencia mínima antes de poder decidir moverse
    visitas_por_zona: Dict[str, int] = None  # cuántas veces entró a cada zona

    def __post_init__(self) -> None:
        if self.tiempo_por_zona is None:  # inicializar contadores si no se pasaron
            self.tiempo_por_zona = {"aula": 0, "biblioteca": 0, "cafeteria": 0}
        if self.visitas_por_zona is None:
            self.visitas_por_zona = {"aula": 0, "biblioteca": 0, "cafeteria": 0}

    @property  # alias compat
    def agent_id(self) -> int:
        return self.id_agente  # alias compat

    @property  # alias compat
    def cooldown(self) -> int:
        return self.enfriamiento  # alias compat
