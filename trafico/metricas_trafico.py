"""
trafico/metricas_trafico.py
---------------------------
Métricas y gráficas para MBA Tráfico: flujo, tiempo de espera, longitud de cola,
accidente y violaciones (pasos en rojo/amarillo).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from motor.viz import dibujar_cuadricula, dibujar_agentes


def tiempo_espera_promedio(tiempos_espera_salidos: List[int]) -> float:
    """Tiempo promedio de espera (ticks) de los vehículos que ya salieron."""
    if not tiempos_espera_salidos:
        return 0.0
    return float(np.mean(tiempos_espera_salidos))


def flujo_total(metricas_flujo: List[int]) -> int:
    """Total de vehículos que cruzaron (throughput)."""
    return sum(metricas_flujo)


def graficar_cola_y_flujo(
    cola_por_tick: List[int],
    flujo_por_tick: List[int],
) -> None:
    """Gráfica de longitud de cola y flujo por tick."""
    n = len(cola_por_tick)
    x = np.arange(n)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax1.plot(x, cola_por_tick, color="C0", label="Longitud cola")
    ax1.set_ylabel("Vehículos en cola")
    ax1.legend()
    ax1.grid(True)
    ax2.plot(x, flujo_por_tick, color="C1", label="Flujo (salidas/tick)")
    ax2.set_ylabel("Flujo")
    ax2.set_xlabel("Tick")
    ax2.legend()
    ax2.grid(True)
    plt.suptitle("Tráfico: cola y flujo por tick")
    plt.tight_layout()
    plt.show()


def graficar_espera_promedio_acumulada(tiempos_espera_salidos: List[int]) -> None:
    """Muestra evolución del tiempo de espera promedio a medida que salen vehículos."""
    if len(tiempos_espera_salidos) < 2:
        return
    promedios = np.cumsum(tiempos_espera_salidos) / np.arange(1, len(tiempos_espera_salidos) + 1)
    plt.figure(figsize=(8, 4))
    plt.plot(promedios, label="Espera promedio (acumulada)")
    plt.xlabel("Vehículo que sale (orden)")
    plt.ylabel("Ticks de espera promedio")
    plt.title("Tiempo de espera promedio acumulado")
    plt.legend()
    plt.grid(True)
    plt.show()


def resumen_accidentes(sim: Any) -> Dict[str, Any]:
    """Resumen de accidente si ocurrió. Retorna dict con contadores y info (tipo_violacion: amarillo/rojo)."""
    hubo = getattr(sim, "hubo_accidente", False)
    info = getattr(sim, "info_accidente", {})
    tick = getattr(sim, "tick_accidente", None)
    pasos_rojo = getattr(sim, "contador_pasos_en_rojo", 0)
    pasos_amarillo = getattr(sim, "contador_pasos_en_amarillo", 0)
    return {
        "hubo_accidente": hubo,
        "tick_accidente": tick,
        "info_accidente": info,
        "tipo_violacion": info.get("tipo_violacion"),
        "pasos_en_rojo": pasos_rojo,
        "pasos_en_amarillo": pasos_amarillo,
    }


def graficar_estado_trafico(
    sim: Any,
    ax: Optional[plt.Axes] = None,
    titulo_extra: str = "",
) -> Figure:
    """
    Visualiza el estado actual del tráfico: cuadrícula (vías + intersección),
    vehículos, y si hubo accidente una X roja. Título tipo NetLogo con tick,
    semáforo, cola, throughput y tipo de violación si aplica.
    """
    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    terreno = sim.entorno.terreno
    dibujar_cuadricula(ax, terreno)
    posiciones = [
        sim.entorno.obtener_posicion_agente(aid)
        for aid, v in sim.agentes.items()
        if getattr(v, "estado", "") not in ("accidentado", "fuera")
    ]
    dibujar_agentes(ax, posiciones, color="navy", tamano=25)
    hubo_accidente = getattr(sim, "hubo_accidente", False)
    if hubo_accidente:
        info = getattr(sim, "info_accidente", {})
        pos = info.get("posicion")
        if pos is not None:
            x, y = pos
            ax.plot(x, y, "X", color="red", markersize=18, markeredgewidth=3)

    # Título informativo
    tick = getattr(sim, "tiempo", 0)
    semaforo = getattr(sim, "semaforo", None)
    fase = getattr(semaforo, "fase_actual", "?")
    estado_luz = getattr(semaforo, "estado_actual", "?")
    cola_por_tick = getattr(sim, "cola_por_tick", [])
    cola_actual = cola_por_tick[-1] if cola_por_tick else 0
    salidos = getattr(sim, "vehiculos_salidos", 0)
    partes = [f"tick={tick} | semáforo {fase} {estado_luz} | cola={cola_actual} | salidos={salidos}"]
    if hubo_accidente:
        tipo_viol = getattr(sim, "info_accidente", {}).get("tipo_violacion", "?")
        partes.append(f" | ACCIDENTE violación={tipo_viol}")
    if titulo_extra:
        partes.append(f" | {titulo_extra}")
    ax.set_title("".join(partes), fontsize=9)
    if fig is None:
        fig = ax.get_figure()
    return fig


def graficar_mapa_con_accidente(
    sim: Any,
    ax: Optional[plt.Axes] = None,
    marcar_accidente: bool = True,
) -> Figure:
    """
    Grafica el mapa de tráfico; si hubo accidente y marcar_accidente=True,
    dibuja una X roja en la celda del accidente.
    """
    return graficar_estado_trafico(sim, ax=ax, titulo_extra="")
