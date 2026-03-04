"""
motor/sim_base.py
-----------------
Base de simulación MBA (Modelos Basados en Agentes) - 100% ESPAÑOL.

- Guarda agentes reales (Estudiante, Vehiculo, etc.), NO los convierte.
- Añade telemetría: registro de eventos (creación/movimientos) en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import numpy as np

from motor.grid import MundoCuadricula


@dataclass
class AgenteBase:
    id_agente: int


class SimulacionBase:
    def __init__(self, entorno: MundoCuadricula, semilla: int = 123, max_eventos: int = 5000) -> None:
        self.entorno = entorno
        self.semilla = semilla
        self.generador = np.random.default_rng(semilla)

        self.tiempo = 0
        self.agentes: Dict[int, Any] = {}
        self.metricas: Dict[str, List[Any]] = {}

        # Telemetría: guardar en memoria con recorte FIFO al llegar al límite
        self.eventos: List[str] = []
        self.max_eventos = max_eventos

        # Detener simulación (p.ej. por accidente)
        self.detener: bool = False

    def registrar_evento(self, texto: str) -> None:
        """Guarda un evento; recorte FIFO si se supera max_eventos."""
        self.eventos.append(texto)
        while len(self.eventos) > self.max_eventos:
            self.eventos.pop(0)

    def agregar_agente(self, agente: Any, x: int, y: int) -> None:
        if agente.id_agente in self.agentes:
            raise ValueError("id_agente duplicado")

        self.agentes[agente.id_agente] = agente
        self.entorno.colocar_agente(agente.id_agente, x, y)

    def registrar_metrica(self, nombre: str, valor: Any) -> None:
        if nombre not in self.metricas:
            self.metricas[nombre] = []
        self.metricas[nombre].append(valor)

    def paso(self) -> None:
        raise NotImplementedError("Implementa paso() en la simulación hija")

    def verificar_invariantes(self) -> None:
        """Invariantes: cada agente en grid, conteo coherente, máximo 1 agente por celda."""
        # Cada agente registrado debe estar en el entorno
        for aid in self.agentes:
            if aid not in self.entorno.agente_a_posicion:
                raise AssertionError(f"Agente {aid} no está en el entorno")
        # Conteo: cantidad de agentes en grid debe coincidir con len(agentes)
        if len(self.entorno.posicion_a_agente) != len(self.agentes):
            raise AssertionError(
                f"Inconsistencia ocupación: {len(self.entorno.posicion_a_agente)} posiciones vs {len(self.agentes)} agentes"
            )
        # Ninguna celda tiene más de un agente (implícito en posicion_a_agente 1:1, pero verificamos)
        if len(self.entorno.posicion_a_agente) != len(set(self.entorno.posicion_a_agente.values())):
            raise AssertionError("Hay posiciones con más de un agente (duplicidad)")

    def ejecutar(self, pasos: int, verificar_cada: int = 1) -> None:
        """Ejecuta pasos ticks; si self.detener se activa (p.ej. accidente), termina de forma limpia."""
        for _ in range(pasos):
            if getattr(self, "detener", False):
                break
            self.paso()
            self.tiempo += 1

            if verificar_cada > 0 and (self.tiempo % verificar_cada == 0):
                self.verificar_invariantes()
