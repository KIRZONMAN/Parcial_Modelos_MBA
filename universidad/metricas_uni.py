"""
universidad/metricas_uni.py
---------------------------
Funciones para:
- Resumir distribución de tiempo de los estudiantes.
- Graficar ocupación por zona en el tiempo.
"""

from __future__ import annotations

from typing import Dict, List
import numpy as np
import matplotlib.pyplot as plt

from universidad.agentes_uni import Estudiante


def resumen_porcentaje_tiempo_por_zona(agentes: Dict[int, Estudiante]) -> Dict[str, float]:
    total_aula = 0
    total_biblio = 0
    total_cafe = 0

    for _, est in agentes.items():
        total_aula += est.tiempo_por_zona.get("aula", 0)
        total_biblio += est.tiempo_por_zona.get("biblioteca", 0)
        total_cafe += est.tiempo_por_zona.get("cafeteria", 0)

    total = total_aula + total_biblio + total_cafe
    if total == 0:
        return {"aula": 0.0, "biblioteca": 0.0, "cafeteria": 0.0}

    return {
        "aula": 100.0 * total_aula / total,
        "biblioteca": 100.0 * total_biblio / total,
        "cafeteria": 100.0 * total_cafe / total,
    }


def graficar_ocupacion(metricas: Dict[str, List[int]]) -> None:
    # Acepta claves nuevas o antiguas (compatibilidad)
    ocup_aula = metricas.get("ocup_aula", metricas.get("occ_aula", []))
    ocup_biblio = metricas.get("ocup_biblioteca", metricas.get("occ_biblio", []))
    ocup_cafe = metricas.get("ocup_cafeteria", metricas.get("occ_cafe", []))

    x = np.arange(len(ocup_aula))

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
    """Devuelve los primeros n eventos (para mostrar en notebook sin spamear)."""
    return list(eventos[:n])


def ultimos_eventos(eventos: List[str], n: int = 20) -> List[str]:
    """Devuelve los últimos n eventos."""
    return list(eventos[-n:]) if len(eventos) >= n else list(eventos)


def filtrar_eventos_por_estudiante(eventos: List[str], id_estudiante: int) -> List[str]:
    """Filtra eventos que mencionan al estudiante con id_estudiante."""
    marca = f"Estudiante {id_estudiante} "
    return [e for e in eventos if marca in e]


def visitas_por_zona(agentes: Dict[int, Estudiante]) -> Dict[str, int]:
    """Total de visitas (entradas) a cada zona."""
    v = {"aula": 0, "biblioteca": 0, "cafeteria": 0}
    for est in agentes.values():
        for z, c in getattr(est, "visitas_por_zona", {}).items():
            if z in v:
                v[z] += c
    return v


def promedio_hambre(agentes: Dict[int, Estudiante]) -> float:
    """Promedio de hambre actual de los estudiantes."""
    if not agentes:
        return 0.0
    return sum(getattr(e, "hambre", 0) for e in agentes.values()) / len(agentes)


def pct_decisiones_bloqueadas(sim) -> float:
    """Porcentaje de intentos de movimiento bloqueados (sin celdas libres)."""
    tot = getattr(sim, "intentos_totales", 0)
    bloq = getattr(sim, "intentos_bloqueados", 0)
    if tot == 0:
        return 0.0
    return 100.0 * bloq / tot


def bloqueos_por_falta_cupo(sim) -> int:
    """Total de intentos bloqueados por zona llena (falta de cupo)."""
    return getattr(sim, "intentos_bloqueados", 0)


def movimientos_por_tick_serie(sim) -> List[int]:
    """Serie de movimientos realizados por tick (desde metricas si está registrado)."""
    return list(sim.metricas.get("movimientos_por_tick", []))


# Compatibilidad
def resumen_tiempo_por_zona(agents: Dict[int, Estudiante]) -> Dict[str, float]:
    return resumen_porcentaje_tiempo_por_zona(agents)


def plot_ocupacion(metrics: Dict[str, List[int]]) -> None:
    return graficar_ocupacion(metrics)