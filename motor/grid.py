"""
motor/grid.py
-------------
Entorno matricial (MundoCuadricula) + tipos de celda (TipoCelda).
Diseñado para Universidad y Tráfico.

NOTA:
- Incluye aliases para compatibilidad:
  CellType -> TipoCelda
  GridWorld -> MundoCuadricula
  y métodos en inglés que llaman a los equivalentes en español.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

Posicion = Tuple[int, int]  # (x, y)


@dataclass
class TipoCelda:
    VACIA: int = 0
    MURO: int = 1

    # Universidad
    AULA: int = 2
    BIBLIOTECA: int = 3
    CAFETERIA: int = 4

    # Tráfico
    VIA: int = 5
    INTERSECCION: int = 6


class MundoCuadricula:
    """MundoCuadricula con matriz terreno[y, x] y ocupación 1 agente por celda."""

    def __init__(self, ancho: int, alto: int, celda_por_defecto: int = TipoCelda.VACIA) -> None:
        self.ancho = ancho
        self.alto = alto

        # Matriz de terreno: índice [y, x]
        self.terreno = np.full((alto, ancho), int(celda_por_defecto), dtype=np.int32)

        # Ocupación
        self.posicion_a_agente: Dict[Posicion, int] = {}
        self.agente_a_posicion: Dict[int, Posicion] = {}

    # -------------------------
    # Utilidades básicas
    # -------------------------

    def en_limites(self, x: int, y: int) -> bool:
        return 0 <= x < self.ancho and 0 <= y < self.alto

    def esta_libre(self, x: int, y: int) -> bool:
        return (x, y) not in self.posicion_a_agente

    def obtener_tipo_celda(self, x: int, y: int) -> int:
        return int(self.terreno[y, x])

    def asignar_tipo_celda(self, x: int, y: int, tipo_celda: int) -> None:
        self.terreno[y, x] = int(tipo_celda)

    def rellenar_rectangulo(self, x0: int, y0: int, w: int, h: int, tipo_celda: int) -> None:
        x1 = min(self.ancho, x0 + w)
        y1 = min(self.alto, y0 + h)
        self.terreno[y0:y1, x0:x1] = int(tipo_celda)

    def celdas_de_tipo(self, tipo_celda: int) -> List[Posicion]:
        ys, xs = np.where(self.terreno == int(tipo_celda))
        return list(zip(xs.tolist(), ys.tolist()))

    # -------------------------
    # Ocupación de agentes
    # -------------------------

    def colocar_agente(self, id_agente: int, x: int, y: int) -> None:
        if not self.en_limites(x, y):
            raise ValueError("Posición fuera del grid")
        if not self.esta_libre(x, y):
            raise ValueError("Celda ocupada")
        if id_agente in self.agente_a_posicion:
            raise ValueError("Agente ya colocado")

        self.posicion_a_agente[(x, y)] = id_agente
        self.agente_a_posicion[id_agente] = (x, y)

    def mover_agente(self, id_agente: int, nuevo_x: int, nuevo_y: int) -> None:
        if id_agente not in self.agente_a_posicion:
            raise ValueError("Agente no está colocado")
        if not self.en_limites(nuevo_x, nuevo_y):
            raise ValueError("Destino fuera del grid")
        if not self.esta_libre(nuevo_x, nuevo_y):
            raise ValueError("Destino ocupado")

        pos_vieja = self.agente_a_posicion[id_agente]
        del self.posicion_a_agente[pos_vieja]

        self.posicion_a_agente[(nuevo_x, nuevo_y)] = id_agente
        self.agente_a_posicion[id_agente] = (nuevo_x, nuevo_y)

    def obtener_posicion_agente(self, id_agente: int) -> Posicion:
        return self.agente_a_posicion[id_agente]

    def celda_libre_aleatoria(
        self,
        generador: np.random.Generator,
        permitidas: Optional[List[Posicion]] = None
    ) -> Posicion:
        if permitidas is None:
            candidatas = [
                (x, y)
                for y in range(self.alto)
                for x in range(self.ancho)
                if (x, y) not in self.posicion_a_agente
            ]
        else:
            candidatas = [p for p in permitidas if p not in self.posicion_a_agente]

        if not candidatas:
            raise RuntimeError("No hay celdas libres disponibles")

        idx = int(generador.integers(0, len(candidatas)))
        return candidatas[idx]

    # =========================================================
    # Compatibilidad (nombres anteriores en inglés)
    # =========================================================

    # Alias de atributos (solo lectura, por compatibilidad)
    @property
    def width(self) -> int:
        return self.ancho

    @property
    def height(self) -> int:
        return self.alto

    @property
    def terrain(self):
        return self.terreno

    @property
    def pos_to_agent(self):
        return self.posicion_a_agente

    @property
    def agent_to_pos(self):
        return self.agente_a_posicion

    # Métodos en inglés -> llaman a los de español
    def in_bounds(self, x: int, y: int) -> bool:
        return self.en_limites(x, y)

    def is_free(self, x: int, y: int) -> bool:
        return self.esta_libre(x, y)

    def get_cell(self, x: int, y: int) -> int:
        return self.obtener_tipo_celda(x, y)

    def set_cell(self, x: int, y: int, cell_type: int) -> None:
        self.asignar_tipo_celda(x, y, cell_type)

    def fill_rect(self, x0: int, y0: int, w: int, h: int, cell_type: int) -> None:
        self.rellenar_rectangulo(x0, y0, w, h, cell_type)

    def cells_of_type(self, cell_type: int) -> List[Posicion]:
        return self.celdas_de_tipo(cell_type)

    def place_agent(self, agent_id: int, x: int, y: int) -> None:
        self.colocar_agente(agent_id, x, y)

    def move_agent(self, agent_id: int, new_x: int, new_y: int) -> None:
        self.mover_agente(agent_id, new_x, new_y)

    def get_agent_pos(self, agent_id: int) -> Posicion:
        return self.obtener_posicion_agente(agent_id)

    def random_free_cell(self, rng: np.random.Generator, allowed: Optional[List[Posicion]] = None) -> Posicion:
        return self.celda_libre_aleatoria(rng, allowed)


# Aliases de compatibilidad a nivel de módulo
CellType = TipoCelda
GridWorld = MundoCuadricula
Pos = Posicion