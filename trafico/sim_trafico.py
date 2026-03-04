"""
trafico/sim_trafico.py
----------------------
Simulación MBA Tráfico: semáforos verde/amarillo/rojo, conductas de riesgo, accidentes causales.

Accidente solo por causa: violación (pasarse amarillo/rojo) y ocupación, o forzar en celda ocupada.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any

from motor.grid import MundoCuadricula, TipoCelda
from motor.sim_base import SimulacionBase
from trafico.agentes_trafico import Vehiculo
from trafico.luces_trafico import ControladorSemaforos


def crear_mapa_trafico(
    ancho: int = 25,
    alto: int = 25,
    ancho_via: int = 3,
    tam_interseccion: int = 5,
) -> Tuple[MundoCuadricula, Dict[str, List[Tuple[int, int]]]]:
    """
    Crea un grid con fondo VACÍO, cruz de vías (vertical + horizontal) e intersección central.
    Spawns solo sobre celdas VIA en los bordes, alineados con la cruz.
    """
    ent = MundoCuadricula(ancho=ancho, alto=alto, celda_por_defecto=TipoCelda.VACIA)
    cx, cy = ancho // 2, alto // 2
    half = ancho_via // 2

    # Vía vertical (columna central de ancho ancho_via)
    x0_v, x1_v = max(0, cx - half), min(ancho, cx + half + 1)
    for x in range(x0_v, x1_v):
        for y in range(alto):
            ent.asignar_tipo_celda(x, y, TipoCelda.VIA)

    # Vía horizontal (fila central de ancho ancho_via)
    y0_h, y1_h = max(0, cy - half), min(alto, cy + half + 1)
    for y in range(y0_h, y1_h):
        for x in range(ancho):
            ent.asignar_tipo_celda(x, y, TipoCelda.VIA)

    # Intersección central (sobrescribe el cruce)
    r = tam_interseccion // 2
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < ancho and 0 <= y < alto:
                ent.asignar_tipo_celda(x, y, TipoCelda.INTERSECCION)

    # Spawns en bordes solo sobre VIA (alineados con la cruz)
    spawns_por_direccion: Dict[str, List[Tuple[int, int]]] = {
        "norte": [], "sur": [], "este": [], "oeste": [],
    }
    for x in range(x0_v, x1_v):
        spawns_por_direccion["sur"].append((x, 0))
        spawns_por_direccion["norte"].append((x, alto - 1))
    for y in range(y0_h, y1_h):
        spawns_por_direccion["este"].append((0, y))
        spawns_por_direccion["oeste"].append((ancho - 1, y))

    return ent, spawns_por_direccion


class SimulacionTrafico(SimulacionBase):
    """MBA Tráfico: semáforos verde/amarillo/rojo, violaciones, accidentes causales."""

    _DESPLAZAMIENTO = {
        "norte": (0, -1),
        "sur": (0, 1),
        "este": (1, 0),
        "oeste": (-1, 0),
    }

    def __init__(
        self,
        entorno: MundoCuadricula,
        semilla: int = 42,
        max_eventos: int = 5000,
        ticks_verde: int = 5,
        ticks_amarillo: int = 2,
        ticks_todo_rojo: int = 1,
        p_spawn: float = 0.25,
        probabilidades_direccion: Dict[str, float] | None = None,
        max_vehiculos: int = 50,
        p_pasarse_amarillo: float = 0.03,
        p_pasarse_rojo: float = 0.003,
        ancho_via: int = 3,
        spawns_por_direccion: Dict[str, List[Tuple[int, int]]] | None = None,
    ) -> None:
        super().__init__(entorno=entorno, semilla=semilla, max_eventos=max_eventos)
        self.semaforo = ControladorSemaforos(
            ticks_verde=ticks_verde,
            ticks_amarillo=ticks_amarillo,
            ticks_todo_rojo=ticks_todo_rojo,
        )
        self.p_spawn = p_spawn
        self.prob_direccion = probabilidades_direccion or {
            "norte": 0.25, "sur": 0.25, "este": 0.25, "oeste": 0.25,
        }
        self.max_vehiculos = max_vehiculos
        self.p_pasarse_amarillo = p_pasarse_amarillo
        self.p_pasarse_rojo = p_pasarse_rojo
        self.ancho_via = ancho_via
        self._id_siguiente = 0

        self._spawns_por_direccion: Dict[str, List[Tuple[int, int]]] = {
            "norte": [], "sur": [], "este": [], "oeste": [],
        }
        if spawns_por_direccion is not None:
            self._spawns_por_direccion = dict(spawns_por_direccion)
        else:
            self._inicializar_spawns()

        self.vehiculos_salidos = 0
        self.tiempos_espera_salidos: List[int] = []
        self.cola_por_tick: List[int] = []
        self.flujo_por_tick: List[int] = []
        self.entradas_interseccion_ultimo_tick: List[Tuple[int, str, bool]] = []

        self.hubo_accidente = False
        self.info_accidente: Dict[str, Any] = {}
        self.contador_pasos_en_rojo = 0
        self.contador_pasos_en_amarillo = 0
        self.tick_accidente: int | None = None

    def _inicializar_spawns(self) -> None:
        """Asigna celdas de spawn por dirección usando ancho_via (alineado con cruz de vías)."""
        ancho, alto = self.entorno.ancho, self.entorno.alto
        cx, cy = ancho // 2, alto // 2
        half = self.ancho_via // 2
        x0, x1 = max(0, cx - half), min(ancho, cx + half + 1)
        y0, y1 = max(0, cy - half), min(alto, cy + half + 1)
        for x in range(x0, x1):
            self._spawns_por_direccion["sur"].append((x, 0))
            self._spawns_por_direccion["norte"].append((x, alto - 1))
        for y in range(y0, y1):
            self._spawns_por_direccion["este"].append((0, y))
            self._spawns_por_direccion["oeste"].append((ancho - 1, y))

    def _intentar_spawn(self) -> None:
        """Spawn de vehículos si hay cupo y dado favorable."""
        if len(self.agentes) >= self.max_vehiculos:
            return
        if self.generador.random() > self.p_spawn:
            return
        dirs = list(self.prob_direccion.keys())
        probs = [self.prob_direccion[d] for d in dirs]
        probs = [p / sum(probs) for p in probs]
        direccion = str(self.generador.choice(dirs, p=probs))
        candidatas = [
            p for p in self._spawns_por_direccion.get(direccion, [])
            if self.entorno.esta_libre(p[0], p[1])
        ]
        if not candidatas:
            return
        pos = candidatas[self.generador.integers(0, len(candidatas))]
        vid = self._id_siguiente
        self._id_siguiente += 1
        perfil = 0.8 + 0.4 * self.generador.random()
        v = Vehiculo(
            id_agente=vid,
            direccion=direccion,
            estado="en_cola",
            espera_acumulada=0,
            perfil_riesgo=perfil,
        )
        self.agregar_agente(v, pos[0], pos[1])
        self.registrar_evento(f"Veh {vid} spawneado en {pos} dir={direccion}")

    def _es_interseccion(self, x: int, y: int) -> bool:
        return self.entorno.obtener_tipo_celda(x, y) == TipoCelda.INTERSECCION

    def _puede_entrar_legal(self, direccion: str) -> bool:
        """True si el semáforo permite pasar (luz verde)."""
        return self.semaforo.puede_pasar(direccion)

    def _registrar_accidente(
        self, vid: int, otro_id: int, dest_x: int, dest_y: int, tipo_violacion: str
    ) -> None:
        """Registra accidente por violación + conflicto real. tipo_violacion: 'amarillo' o 'rojo'."""
        v = self.agentes.get(vid)
        otro = self.agentes.get(otro_id)
        if v is None or otro is None:
            return
        self.hubo_accidente = True
        self.tick_accidente = self.tiempo
        self.info_accidente = {
            "vehiculos": [vid, otro_id],
            "posicion": (dest_x, dest_y),
            "causa": f"paso_en_{tipo_violacion}",
            "tipo_violacion": tipo_violacion,
        }
        v.estado = "accidentado"
        otro.estado = "accidentado"
        self.registrar_evento(
            f"ACCIDENTE tick={self.tiempo} Veh {vid}+{otro_id} en {dest_x},{dest_y} tipo_violacion={tipo_violacion}"
        )
        self.detener = True

    def paso(self) -> None:
        """Un tick: actualizar semáforo, procesar vehículos, spawn.
        Accidente SOLO por violación (amarillo/rojo) + celda objetivo ocupada.
        Si semáforo verde y destino ocupado = espera, no accidente.
        Vehículos en_interseccion/cruzando no vuelven a chequear semáforo; solo salen cuando hay espacio.
        Anti-gridlock: no entrar a intersección si la celda de salida no está libre.
        """
        self.semaforo.actualizar()
        self.entradas_interseccion_ultimo_tick = []
        flujo_este_tick = 0

        intenciones: Dict[int, Tuple[int, int]] = {}
        orden = sorted(self.agentes.keys())

        for vid in orden:
            v = self.agentes.get(vid)
            if v is None or v.estado == "accidentado" or v.estado == "fuera":
                continue
            px, py = self.entorno.obtener_posicion_agente(vid)
            dx, dy = self._DESPLAZAMIENTO[v.direccion]
            nx, ny = px + dx, py + dy

            if not self.entorno.en_limites(nx, ny):
                self.entorno.posicion_a_agente.pop((px, py), None)
                self.entorno.agente_a_posicion.pop(vid, None)
                del self.agentes[vid]
                self.vehiculos_salidos += 1
                self.tiempos_espera_salidos.append(v.espera_acumulada)
                flujo_este_tick += 1
                self.registrar_evento(f"Veh {vid} salió dir={v.direccion} espera={v.espera_acumulada}")
                continue

            # --- Ya está dentro de intersección: no re-chequear semáforo, solo salir si hay espacio ---
            if getattr(v, "estado", "") in ("en_interseccion", "cruzando"):
                if self.entorno.esta_libre(nx, ny):
                    intenciones[vid] = (nx, ny)
                else:
                    v.espera_acumulada += 1
                continue

            # --- Vía normal (no intersección) ---
            if not self._es_interseccion(nx, ny):
                if self.entorno.esta_libre(nx, ny):
                    intenciones[vid] = (nx, ny)
                else:
                    v.espera_acumulada += 1
                continue

            # --- Destino es intersección: entrar solo si legal o violación decidida ---
            puede_legal = self._puede_entrar_legal(v.direccion)
            violacion_amarillo = self.semaforo.esta_amarillo_para(v.direccion)
            violacion_rojo = self.semaforo.esta_rojo_para(v.direccion)

            intenta_pasar = puede_legal
            es_violacion = False
            tipo_violacion = ""
            if violacion_amarillo:
                p = min(1.0, self.p_pasarse_amarillo * v.perfil_riesgo)
                if self.generador.random() < p:
                    intenta_pasar = True
                    es_violacion = True
                    tipo_violacion = "amarillo"
                    self.contador_pasos_en_amarillo += 1
            if violacion_rojo and not intenta_pasar:
                p = min(1.0, self.p_pasarse_rojo * v.perfil_riesgo)
                if self.generador.random() < p:
                    intenta_pasar = True
                    es_violacion = True
                    tipo_violacion = "rojo"
                    self.contador_pasos_en_rojo += 1

            if not intenta_pasar:
                v.espera_acumulada += 1
                continue

            # Anti-gridlock: no entrar si la celda de salida (siguiente en la dirección) no está libre
            sx, sy = nx + dx, ny + dy
            if self.entorno.en_limites(sx, sy) and not self.entorno.esta_libre(sx, sy):
                v.espera_acumulada += 1
                continue

            if self.entorno.esta_libre(nx, ny):
                intenciones[vid] = (nx, ny)
                self.entradas_interseccion_ultimo_tick.append((vid, "ok", puede_legal))
            else:
                # Destino ocupado: accidente SOLO si fue violación; si verde = espera
                if es_violacion and tipo_violacion:
                    otro_id = self.entorno.posicion_a_agente.get((nx, ny))
                    if otro_id is not None:
                        self._registrar_accidente(vid, otro_id, nx, ny, tipo_violacion)
                        return
                v.espera_acumulada += 1

        # Aplicar movimientos
        for vid in orden:
            if vid not in intenciones:
                continue
            dest = intenciones[vid]
            v = self.agentes.get(vid)
            if v is None or v.estado == "accidentado":
                continue
            if not self.entorno.esta_libre(dest[0], dest[1]):
                v.espera_acumulada += 1
                continue
            pos_ant = self.entorno.obtener_posicion_agente(vid)
            self.entorno.mover_agente(vid, dest[0], dest[1])
            # Si entró en intersección, marcar en_interseccion; si salió a vía, en_cola
            if self._es_interseccion(dest[0], dest[1]):
                v.estado = "en_interseccion"
            else:
                v.estado = "en_cola"
            self.registrar_evento(f"Veh {vid} {pos_ant}->{dest}")

        en_cola = sum(1 for v in self.agentes.values() if getattr(v, "estado", "") == "en_cola")
        self.cola_por_tick.append(en_cola)
        self.flujo_por_tick.append(flujo_este_tick)
        self._intentar_spawn()