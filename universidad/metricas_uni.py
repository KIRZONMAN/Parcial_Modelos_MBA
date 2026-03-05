"""
universidad/metricas_uni.py: Funciones para:
- Resumir distribución de tiempo de los estudiantes.
- Graficar ocupación por zona en el tiempo.
"""

from __future__ import annotations  # compat tipos

from typing import Dict, List  # anotaciones
import numpy as np  # arange
import matplotlib.pyplot as plt  # gráficas
from universidad.agentes_uni import Estudiante  # tipo agente


def resumen_porcentaje_tiempo_por_zona(agentes: Dict[int, Estudiante]) -> Dict[str, float]:
    total_aula = 0
    total_biblio = 0
    total_cafe = 0
    for _, est in agentes.items():  # sumar tiempo de cada estudiante por zona
        total_aula += est.tiempo_por_zona.get("aula", 0)
        total_biblio += est.tiempo_por_zona.get("biblioteca", 0)
        total_cafe += est.tiempo_por_zona.get("cafeteria", 0)
    total = total_aula + total_biblio + total_cafe
    if total == 0:  # evitar división por cero
        return {"aula": 0.0, "biblioteca": 0.0, "cafeteria": 0.0}
    return {  # porcentajes
        "aula": 100.0 * total_aula / total,
        "biblioteca": 100.0 * total_biblio / total,
        "cafeteria": 100.0 * total_cafe / total,
    }


def graficar_ocupacion(metricas: Dict[str, List[int]]) -> None:
    ocup_aula = metricas.get("ocup_aula", metricas.get("occ_aula", []))  # acepta nombres viejos
    ocup_biblio = metricas.get("ocup_biblioteca", metricas.get("occ_biblio", []))
    ocup_cafe = metricas.get("ocup_cafeteria", metricas.get("occ_cafe", []))
    x = np.arange(len(ocup_aula))  # eje ticks
    plt.figure(figsize=(10, 4))
    plt.plot(x, ocup_aula, label="Aula")
    plt.plot(x, ocup_biblio, label="Biblioteca")
    plt.plot(x, ocup_cafe, label="Cafetería")
    plt.title("Ocupación por zona vs tiempo (ticks)")
    plt.xlabel("Tick")
    plt.ylabel("Número de estudiantes")
    plt.legend()
    plt.grid(True)
    plt.show()


def primeros_eventos(eventos: List[str], n: int = 20) -> List[str]:
    return list(eventos[:n])  # para no spamear en notebook


def ultimos_eventos(eventos: List[str], n: int = 20) -> List[str]:
    return list(eventos[-n:]) if len(eventos) >= n else list(eventos)  # últimos n o todos


def filtrar_eventos_por_estudiante(eventos: List[str], id_estudiante: int) -> List[str]:
    marca = f"Estudiante {id_estudiante} "  # texto que identifica al estudiante
    return [e for e in eventos if marca in e]


def visitas_por_zona(agentes: Dict[int, Estudiante]) -> Dict[str, int]:
    v = {"aula": 0, "biblioteca": 0, "cafeteria": 0}
    for est in agentes.values():  # sumar visitas de cada uno
        for z, c in getattr(est, "visitas_por_zona", {}).items():
            if z in v:
                v[z] += c
    return v


def promedio_hambre(agentes: Dict[int, Estudiante]) -> float:
    if not agentes:  # vacío
        return 0.0
    return sum(getattr(e, "hambre", 0) for e in agentes.values()) / len(agentes)  # media hambre actual


def pct_decisiones_bloqueadas(sim) -> float:
    tot = getattr(sim, "intentos_totales", 0)
    bloq = getattr(sim, "intentos_bloqueados", 0)
    if tot == 0:
        return 0.0
    return 100.0 * bloq / tot  # % intentos que no pudieron mover (zona llena)


def bloqueos_por_falta_cupo(sim) -> int:
    return getattr(sim, "intentos_bloqueados", 0)  # total bloqueos


def movimientos_por_tick_serie(sim) -> List[int]:
    return list(sim.metricas.get("movimientos_por_tick", []))  # serie desde métricas


def resumen_tiempo_por_zona(agents: Dict[int, Estudiante]) -> Dict[str, float]:
    return resumen_porcentaje_tiempo_por_zona(agents)  # alias compat


def plot_ocupacion(metrics: Dict[str, List[int]]) -> None:
    return graficar_ocupacion(metrics)  # alias compat
