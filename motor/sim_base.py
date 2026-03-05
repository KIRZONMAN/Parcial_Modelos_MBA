"""
motor/sim_base.py: Base de simulación del MBA.
"""

from __future__ import annotations  # compat tipos

from dataclasses import dataclass  # base para agentes
from typing import Any, Dict, List  # tipos
import numpy as np  # para el generador aleatorio
from motor.grid import MundoCuadricula  # entorno del grid


@dataclass  # decorador
class AgenteBase:  # base de Estudiante, Vehiculo, etc.
    id_agente: int  # único por agente


class SimulacionBase:  # base de SimulacionUniversidad, SimulacionTrafico
    def __init__(self, entorno: MundoCuadricula, semilla: int = 123, max_eventos: int = 5000) -> None:
        self.entorno = entorno  # el grid
        self.semilla = semilla  # para reproducibilidad
        self.generador = np.random.default_rng(semilla)  # rng
        self.tiempo = 0  # tick actual
        self.agentes: Dict[int, Any] = {}  # id -> agente
        self.metricas: Dict[str, List[Any]] = {}  # nombre -> lista de valores
        self.eventos: List[str] = []  # log en memoria (FIFO si se pasa de max)
        self.max_eventos = max_eventos  # tope del buffer de eventos
        self.detener: bool = False  # si true, ejecutar() para (ej. accidente)

    def registrar_evento(self, texto: str) -> None:
        """Guarda un evento; recorte FIFO si se supera max_eventos."""
        self.eventos.append(texto)  # añade al final
        while len(self.eventos) > self.max_eventos:  # recorta si pasamos del tope
            self.eventos.pop(0)  # quita los más viejos

    def agregar_agente(self, agente: Any, x: int, y: int) -> None:
        if agente.id_agente in self.agentes:  # no duplicados
            raise ValueError("id_agente duplicado")
        self.agentes[agente.id_agente] = agente  # guardamos el agente
        self.entorno.colocar_agente(agente.id_agente, x, y)  # lo ponemos en el grid

    def registrar_metrica(self, nombre: str, valor: Any) -> None:
        if nombre not in self.metricas:  # crea la lista si no existe
            self.metricas[nombre] = []
        self.metricas[nombre].append(valor)  # añade valor al historial

    def paso(self) -> None:
        raise NotImplementedError("Implementa paso() en la simulación hija")  # lo implementa la hija

    def verificar_invariantes(self) -> None:
        """Invariantes: cada agente en grid, conteo coherente, máximo 1 agente por celda."""
        for aid in self.agentes:  # cada agente debe estar en el entorno
            if aid not in self.entorno.agente_a_posicion:
                raise AssertionError(f"Agente {aid} no está en el entorno")
        if len(self.entorno.posicion_a_agente) != len(self.agentes):  # mismo número de posiciones que agentes
            raise AssertionError(
                f"Inconsistencia ocupación: {len(self.entorno.posicion_a_agente)} posiciones vs {len(self.agentes)} agentes"
            )
        if len(self.entorno.posicion_a_agente) != len(set(self.entorno.posicion_a_agente.values())):  # sin duplicados por celda
            raise AssertionError("Hay posiciones con más de un agente (duplicidad)")

    def ejecutar(self, pasos: int, verificar_cada: int = 1) -> None:
        """Ejecuta pasos ticks; si self.detener se activa (p.ej. accidente), termina de forma limpia."""
        for _ in range(pasos):  # loop de ticks
            if getattr(self, "detener", False):  # parar si hubo accidente etc
                break
            self.paso()  # un tick (lo implementa la hija)
            self.tiempo += 1  # paso() no incrementa tiempo, lo hace ejecutar
            if verificar_cada > 0 and (self.tiempo % verificar_cada == 0):  # cada N pasos
                self.verificar_invariantes()  # comprueba invariantes
