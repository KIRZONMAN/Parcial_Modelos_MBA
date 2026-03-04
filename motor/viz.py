"""
motor/viz.py
------------
Visualización con matplotlib para el grid y agentes.

NOTA:
- Incluye aliases para compatibilidad:
  default_colormap / draw_grid / draw_agents
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


def colormap_por_defecto() -> ListedColormap:
    colores = [
        "#FFFFFF",  # 0 VACIA
        "#444444",  # 1 MURO
        "#B3E5FC",  # 2 AULA
        "#C8E6C9",  # 3 BIBLIOTECA
        "#FFE0B2",  # 4 CAFETERIA
        "#E0E0E0",  # 5 VIA
        "#D1C4E9",  # 6 INTERSECCION
    ]
    return ListedColormap(colores)


def dibujar_cuadricula(ax: plt.Axes, terreno: np.ndarray) -> None:
    ax.imshow(terreno, cmap=colormap_por_defecto(), origin="upper", interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])


def dibujar_agentes(
    ax: plt.Axes,
    posiciones: List[Tuple[int, int]],
    color: str = "black",
    tamano: int = 30
) -> None:
    if not posiciones:
        return
    xs = [p[0] for p in posiciones]
    ys = [p[1] for p in posiciones]
    ax.scatter(xs, ys, s=tamano, c=color)


# Compatibilidad (nombres anteriores)
def default_colormap() -> ListedColormap:
    return colormap_por_defecto()

def draw_grid(ax: plt.Axes, terrain: np.ndarray) -> None:
    return dibujar_cuadricula(ax, terrain)

def draw_agents(ax: plt.Axes, positions: List[Tuple[int, int]], color: str = "black", size: int = 30) -> None:
    return dibujar_agentes(ax, positions, color=color, tamano=size)