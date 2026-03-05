"""
trafico/metricas_trafico.py: Este es el archivo de métricas y gráficas para MBA Tráfico: flujo, tiempo de espera, longitud de cola,
accidente y violaciones (pasos en rojo/amarillo).
"""

from __future__ import annotations  # compat tipos

from typing import Any, Dict, List, Optional, Tuple  # anotaciones
import numpy as np  # arrays y mean/cumsum
import matplotlib.pyplot as plt  # gráficas
from matplotlib.figure import Figure  # tipo retorno
from motor.grid import TipoCelda  # INTERSECCION
from motor.viz import dibujar_cuadricula, dibujar_agentes  # pintar grid y agentes


def _clusters_interseccion(terreno: np.ndarray) -> List[Tuple[int, int, int, int]]:
    alto, ancho = terreno.shape  # dimensiones
    visitado = np.zeros_like(terreno, dtype=bool)  # máscara ya visitado
    clusters: List[Tuple[int, int, int, int]] = []  # lista de bbox (min_x, min_y, max_x, max_y)

    def vecinos(x: int, y: int):  # 4-vecinos
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # arriba abajo izq der
            nx, ny = x + dx, y + dy
            if 0 <= nx < ancho and 0 <= ny < alto and terreno[ny, nx] == TipoCelda.INTERSECCION:  # dentro y es intersección
                yield nx, ny

    for j in range(alto):  # filas
        for i in range(ancho):  # columnas
            if terreno[j, i] != TipoCelda.INTERSECCION or visitado[j, i]:  # saltar si no es intersección o ya visitado
                continue
            stack = [(i, j)]  # flood-fill desde (i,j)
            min_x, min_y, max_x, max_y = i, j, i, j  # bbox inicial
            while stack:
                x, y = stack.pop()
                if visitado[y, x]:  # ya procesado
                    continue
                visitado[y, x] = True
                min_x, max_x = min(min_x, x), max(max_x, x)  # actualizar bbox x
                min_y, max_y = min(min_y, y), max(max_y, y)  # actualizar bbox y
                for nx, ny in vecinos(x, y):  # vecinos que son intersección
                    if not visitado[ny, nx]:  # añadir a la pila
                        stack.append((nx, ny))
            clusters.append((min_x, min_y, max_x, max_y))  # guardar bbox del cluster
    return clusters


def tiempo_espera_promedio(tiempos_espera_salidos: List[int]) -> float:
    if not tiempos_espera_salidos:  # lista vacía
        return 0.0
    return float(np.mean(tiempos_espera_salidos))  # media de ticks de espera


def flujo_total(metricas_flujo: List[int]) -> int:
    return sum(metricas_flujo)  # total vehículos que salieron


def graficar_movimientos(movimientos_por_tick: List[int]) -> None:
    if not movimientos_por_tick:  # nada que graficar
        return
    x = np.arange(len(movimientos_por_tick))  # eje ticks
    plt.figure(figsize=(10, 3))  # figura
    plt.plot(x, movimientos_por_tick, color="C2", label="Movimientos por tick")  # curva
    plt.xlabel("Tick")
    plt.ylabel("Movimientos")
    plt.title("Movimientos por tick")
    plt.legend()
    plt.grid(True)
    plt.show()


def graficar_cola_y_flujo(
    cola_por_tick: List[int],  # longitud cola cada tick
    flujo_por_tick: List[int],  # salidas cada tick
) -> None:
    n = len(cola_por_tick)
    x = np.arange(n)  # eje común
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)  # dos subplots
    ax1.plot(x, cola_por_tick, color="C0", label="Longitud cola")  # arriba: cola
    ax1.set_ylabel("Vehículos en cola")
    ax1.legend()
    ax1.grid(True)
    ax2.plot(x, flujo_por_tick, color="C1", label="Flujo (salidas/tick)")  # abajo: flujo
    ax2.set_ylabel("Flujo")
    ax2.set_xlabel("Tick")
    ax2.legend()
    ax2.grid(True)
    plt.suptitle("Tráfico: cola y flujo por tick")
    plt.tight_layout()
    plt.show()


def graficar_espera_promedio_acumulada(tiempos_espera_salidos: List[int]) -> None:
    if len(tiempos_espera_salidos) < 2:  # necesitamos al menos 2
        return
    promedios = np.cumsum(tiempos_espera_salidos) / np.arange(1, len(tiempos_espera_salidos) + 1)  # media acumulada
    plt.figure(figsize=(8, 4))
    plt.plot(promedios, label="Espera promedio (acumulada)")
    plt.xlabel("Vehículo que sale (orden)")
    plt.ylabel("Ticks de espera promedio")
    plt.title("Tiempo de espera promedio acumulado")
    plt.legend()
    plt.grid(True)
    plt.show()


def resumen_accidentes(sim: Any) -> Dict[str, Any]:
    hubo = getattr(sim, "hubo_accidente", False)
    info = getattr(sim, "info_accidente", {})
    tick = getattr(sim, "tick_accidente", None)
    pasos_rojo = getattr(sim, "contador_pasos_en_rojo", 0)
    pasos_amarillo = getattr(sim, "contador_pasos_en_amarillo", 0)
    return {  # diccionario resumen
        "hubo_accidente": hubo,
        "tick_accidente": tick,
        "info_accidente": info,
        "tipo_violacion": info.get("tipo_violacion"),
        "causa": info.get("causa"),
        "pasos_en_rojo": pasos_rojo,
        "pasos_en_amarillo": pasos_amarillo,
    }


def graficar_estado_trafico(
    sim: Any,  # simulación
    ax: Optional[plt.Axes] = None,  # ejes opcionales
    titulo_extra: str = "",  # texto extra en título
) -> Figure:
    fig = None
    if ax is None:  # crear figura si no nos pasan ejes
        fig, ax = plt.subplots(figsize=(7, 5))
    terreno = sim.entorno.terreno  # matriz del grid
    dibujar_cuadricula(ax, terreno)  # pinta vías e intersección
    posiciones = [  # posiciones de vehículos que no están accidentados ni fuera
        sim.entorno.obtener_posicion_agente(aid)
        for aid, v in sim.agentes.items()
        if getattr(v, "estado", "") not in ("accidentado", "fuera")
    ]
    dibujar_agentes(ax, posiciones, color="navy", tamano=25)  # puntos azules

    semaforo = getattr(sim, "semaforo", None)
    if semaforo is not None:  # pintar estado semáforo en esquinas
        clusters = _clusters_interseccion(terreno)
        ms = 5  # tamaño marcador
        for (x_min, y_min, x_max, y_max) in clusters:  # por cada intersección
            for (px, py), direccion in [  # 4 esquinas con su dirección
                ((x_min, y_min), "sur"),
                ((x_max, y_min), "oeste"),
                ((x_min, y_max), "este"),
                ((x_max, y_max), "norte"),
            ]:
                if semaforo.puede_pasar(direccion):  # verde
                    color = "lime"
                elif semaforo.esta_amarillo_para(direccion):  # amarillo
                    color = "gold"
                else:  # rojo
                    color = "red"
                ax.plot(px, py, "s", color=color, markersize=ms, markeredgecolor="black", markeredgewidth=0.5)  # cuadrado

    hubo_accidente = getattr(sim, "hubo_accidente", False)
    if hubo_accidente:  # marcar celda del accidente con X roja
        info = getattr(sim, "info_accidente", {})
        pos = info.get("posicion")
        if pos is not None:
            x, y = pos
            ax.plot(x, y, "X", color="red", markersize=18, markeredgewidth=3)

    tick = getattr(sim, "tiempo", 0)
    semaforo = getattr(sim, "semaforo", None)
    fase = getattr(semaforo, "fase_actual", "?")
    estado_luz = getattr(semaforo, "estado_actual", "?")
    cola_por_tick = getattr(sim, "cola_por_tick", [])
    cola_actual = cola_por_tick[-1] if cola_por_tick else 0
    salidos = getattr(sim, "vehiculos_salidos", 0)
    partes = [f"tick={tick} | semáforo {fase} {estado_luz} | cola={cola_actual} | salidos={salidos}"]  # título base
    if hubo_accidente:  # añadir info accidente al título
        info_acc = getattr(sim, "info_accidente", {})
        tipo_viol = info_acc.get("tipo_violacion")
        causa = info_acc.get("causa", "?")
        partes.append(f" | ACCIDENTE {causa}" + (f" (violación={tipo_viol})" if tipo_viol else ""))
    if titulo_extra:
        partes.append(f" | {titulo_extra}")
    ax.set_title("".join(partes), fontsize=9)
    if fig is None:  # si nos pasaron ax, obtener figura
        fig = ax.get_figure()
    return fig


def graficar_mapa_con_accidente(
    sim: Any,
    ax: Optional[plt.Axes] = None,
    marcar_accidente: bool = True,  # no se usa aquí, lo hace graficar_estado_trafico
) -> Figure:
    return graficar_estado_trafico(sim, ax=ax, titulo_extra="")  # delega
