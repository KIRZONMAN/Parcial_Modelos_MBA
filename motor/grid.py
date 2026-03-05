"""
motor/grid.py:este es el entorno matricial (MundoCuadricula) + tipos de celda (TipoCelda).
Diseñado para Universidad y Tráfico.
"""

from __future__ import annotations  # compatibilidad tipos

from dataclasses import dataclass  # dataclass para TipoCelda
from typing import Dict, List, Optional, Tuple  # tipos para anotaciones
import numpy as np  # matriz del terreno

Posicion = Tuple[int, int]  # alias (x, y)


@dataclass  # decorador para clase con campos
class TipoCelda:  # enum-like de tipos de celda
    VACIA: int = 0  # celda vacía
    MURO: int = 1  # muro (no transitable)
    AULA: int = 2  # universidad
    BIBLIOTECA: int = 3  # universidad
    CAFETERIA: int = 4  # universidad
    VIA: int = 5  # tráfico
    INTERSECCION: int = 6  # tráfico


class MundoCuadricula:  # grid con terreno y 1 agente por celda
    """MundoCuadricula con matriz terreno[y, x] y ocupación 1 agente por celda."""

    def __init__(self, ancho: int, alto: int, celda_por_defecto: int = TipoCelda.VACIA) -> None:
        self.ancho = ancho  # ancho en celdas
        self.alto = alto  # alto en celdas
        self.terreno = np.full((alto, ancho), int(celda_por_defecto), dtype=np.int32)  # matriz [y,x]
        self.posicion_a_agente: Dict[Posicion, int] = {}  # (x,y) -> id agente
        self.agente_a_posicion: Dict[int, Posicion] = {}  # id agente -> (x,y)

    def en_limites(self, x: int, y: int) -> bool:
        return 0 <= x < self.ancho and 0 <= y < self.alto  # true si (x,y) dentro del grid

    def esta_libre(self, x: int, y: int) -> bool:
        return (x, y) not in self.posicion_a_agente  # nadie en esa celda

    def obtener_tipo_celda(self, x: int, y: int) -> int:
        return int(self.terreno[y, x])  # tipo (VACIA, AULA, VIA, etc.)

    def asignar_tipo_celda(self, x: int, y: int, tipo_celda: int) -> None:
        self.terreno[y, x] = int(tipo_celda)  # pinta la celda

    def rellenar_rectangulo(self, x0: int, y0: int, w: int, h: int, tipo_celda: int) -> None:
        x1 = min(self.ancho, x0 + w)  # no pasarse del borde derecho
        y1 = min(self.alto, y0 + h)  # no pasarse del borde abajo
        self.terreno[y0:y1, x0:x1] = int(tipo_celda)  # rellena el rectángulo

    def celdas_de_tipo(self, tipo_celda: int) -> List[Posicion]:
        ys, xs = np.where(self.terreno == int(tipo_celda))  # busca todas las celdas de ese tipo
        return list(zip(xs.tolist(), ys.tolist()))  # devuelve lista (x,y)

    def colocar_agente(self, id_agente: int, x: int, y: int) -> None:
        if not self.en_limites(x, y):  # validar límites
            raise ValueError("Posición fuera del grid")
        if not self.esta_libre(x, y):  # validar que esté libre
            raise ValueError("Celda ocupada")
        if id_agente in self.agente_a_posicion:  # validar que no esté ya colocado
            raise ValueError("Agente ya colocado")
        self.posicion_a_agente[(x, y)] = id_agente  # registro posición -> id
        self.agente_a_posicion[id_agente] = (x, y)  # registro id -> posición

    def mover_agente(self, id_agente: int, nuevo_x: int, nuevo_y: int) -> None:
        if id_agente not in self.agente_a_posicion:  # agente debe existir
            raise ValueError("Agente no está colocado")
        if not self.en_limites(nuevo_x, nuevo_y):  # destino en límites
            raise ValueError("Destino fuera del grid")
        if not self.esta_libre(nuevo_x, nuevo_y):  # destino libre
            raise ValueError("Destino ocupado")
        pos_vieja = self.agente_a_posicion[id_agente]  # guardamos la anterior
        del self.posicion_a_agente[pos_vieja]  # quita de la celda vieja
        self.posicion_a_agente[(nuevo_x, nuevo_y)] = id_agente  # asigna en la nueva
        self.agente_a_posicion[id_agente] = (nuevo_x, nuevo_y)  # actualiza mapa id->pos

    def obtener_posicion_agente(self, id_agente: int) -> Posicion:
        return self.agente_a_posicion[id_agente]  # (x, y) del agente

    def celda_libre_aleatoria(
        self,
        generador: np.random.Generator,
        permitidas: Optional[List[Posicion]] = None
    ) -> Posicion:
        if permitidas is None:  # si no hay lista, todas las libres del grid
            candidatas = [
                (x, y)  # par coordenadas
                for y in range(self.alto)  # recorre filas
                for x in range(self.ancho)  # recorre columnas
                if (x, y) not in self.posicion_a_agente  # que esté libre
            ]
        else:  # si hay lista, solo las de la lista que estén libres
            candidatas = [p for p in permitidas if p not in self.posicion_a_agente]
        if not candidatas:  # no hay ninguna libre
            raise RuntimeError("No hay celdas libres disponibles")
        idx = int(generador.integers(0, len(candidatas)))  # elige una al azar
        return candidatas[idx]  # devuelve (x,y)

    @property  # alias ancho (compat)
    def width(self) -> int:
        return self.ancho

    @property  # alias alto (compat)
    def height(self) -> int:
        return self.alto

    @property  # alias terreno (compat)
    def terrain(self):
        return self.terreno

    @property  # alias posicion_a_agente (compat)
    def pos_to_agent(self):
        return self.posicion_a_agente

    @property  # alias agente_a_posicion (compat)
    def agent_to_pos(self):
        return self.agente_a_posicion

    def in_bounds(self, x: int, y: int) -> bool:
        return self.en_limites(x, y)  # delegación

    def is_free(self, x: int, y: int) -> bool:
        return self.esta_libre(x, y)  # delegación

    def get_cell(self, x: int, y: int) -> int:
        return self.obtener_tipo_celda(x, y)  # delegación

    def set_cell(self, x: int, y: int, cell_type: int) -> None:
        self.asignar_tipo_celda(x, y, cell_type)  # delegación

    def fill_rect(self, x0: int, y0: int, w: int, h: int, cell_type: int) -> None:
        self.rellenar_rectangulo(x0, y0, w, h, cell_type)  # delegación

    def cells_of_type(self, cell_type: int) -> List[Posicion]:
        return self.celdas_de_tipo(cell_type)  # delegación

    def place_agent(self, agent_id: int, x: int, y: int) -> None:
        self.colocar_agente(agent_id, x, y)  # delegación

    def move_agent(self, agent_id: int, new_x: int, new_y: int) -> None:
        self.mover_agente(agent_id, new_x, new_y)  # delegación

    def get_agent_pos(self, agent_id: int) -> Posicion:
        return self.obtener_posicion_agente(agent_id)  # delegación

    def random_free_cell(self, rng: np.random.Generator, allowed: Optional[List[Posicion]] = None) -> Posicion:
        return self.celda_libre_aleatoria(rng, allowed)  # delegación


CellType = TipoCelda  # alias módulo (compat)
GridWorld = MundoCuadricula  # alias módulo (compat)
Pos = Posicion  # alias módulo (compat)
