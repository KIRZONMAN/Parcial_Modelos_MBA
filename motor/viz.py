"""
motor/viz.py: Archivo de visualización con matplotlib para el grid y agentes.
"""

from __future__ import annotations  # compat tipos

from typing import List, Tuple  # anotaciones
import numpy as np  # terreno
import matplotlib.pyplot as plt  # ejes y figuras
from matplotlib.colors import ListedColormap  # colormap discreto


def colormap_por_defecto() -> ListedColormap:
    colores = [  # un color por TipoCelda
        "#FFFFFF",  # vacía
        "#444444",  # muro
        "#B3E5FC",  # aula
        "#C8E6C9",  # biblioteca
        "#FFE0B2",  # cafetería
        "#E0E0E0",  # vía
        "#D1C4E9",  # intersección
    ]
    return ListedColormap(colores)  # devuelve el colormap


def dibujar_cuadricula(ax: plt.Axes, terreno: np.ndarray) -> None:
    ax.imshow(terreno, cmap=colormap_por_defecto(), origin="upper", interpolation="nearest")  # pinta el terreno
    ax.set_xticks([])  # sin números en eje x
    ax.set_yticks([])  # sin números en eje y


def dibujar_agentes(
    ax: plt.Axes,  # ejes donde dibujar
    posiciones: List[Tuple[int, int]],  # lista (x,y)
    color: str = "black",  # color de los puntos
    tamano: int = 30  # tamaño del scatter
) -> None:
    if not posiciones:  # nada que dibujar
        return
    xs = [p[0] for p in posiciones]  # coordenadas x
    ys = [p[1] for p in posiciones]  # coordenadas y
    ax.scatter(xs, ys, s=tamano, c=color)  # puntos en el grid


def default_colormap() -> ListedColormap:
    return colormap_por_defecto()  # alias compat


def draw_grid(ax: plt.Axes, terrain: np.ndarray) -> None:
    return dibujar_cuadricula(ax, terrain)  # alias compat


def draw_agents(ax: plt.Axes, positions: List[Tuple[int, int]], color: str = "black", size: int = 30) -> None:
    return dibujar_agentes(ax, positions, color=color, tamano=size)  # alias compat
