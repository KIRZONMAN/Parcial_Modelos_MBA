"""
trafico/sim_trafico.py: Archivo de simulación MBA Tráfico: semáforos verde/amarillo/rojo, conductas de riesgo, accidentes causales.
Accidente solo por causa: violación (pasarse amarillo/rojo) y ocupación, o forzar en celda ocupada.
"""

from __future__ import annotations  # compat tipos

from typing import Dict, List, Tuple, Any  # anotaciones
from motor.grid import MundoCuadricula, TipoCelda  # grid y tipos
from motor.sim_base import SimulacionBase  # base simulación
from trafico.agentes_trafico import Vehiculo  # agente vehículo
from trafico.luces_trafico import ControladorSemaforos  # semáforos


def crear_mapa_trafico(
    ancho: int = 25,
    alto: int = 25,
    ancho_via: int = 3,
    tam_interseccion: int = 5,
    layout: str = "1x1",  # 1x1 o 2x2
) -> Tuple[MundoCuadricula, Dict[str, List[Tuple[int, int]]]]:
    ent = MundoCuadricula(ancho=ancho, alto=alto, celda_por_defecto=TipoCelda.VACIA)  # grid vacío
    half = ancho_via // 2  # mitad del ancho de vía
    r = tam_interseccion // 2  # radio intersección
    if layout == "2x2":  # dos cruces
        centros_x = [ancho // 4, 3 * ancho // 4]  # columnas centrales vías
        centros_y = [alto // 4, 3 * alto // 4]  # filas centrales vías
        for cx in centros_x:  # vías verticales
            x0, x1 = max(0, cx - half), min(ancho, cx + half + 1)
            for x in range(x0, x1):
                for y in range(alto):
                    ent.asignar_tipo_celda(x, y, TipoCelda.VIA)
        for cy in centros_y:  # vías horizontales
            y0, y1 = max(0, cy - half), min(alto, cy + half + 1)
            for y in range(y0, y1):
                for x in range(ancho):
                    ent.asignar_tipo_celda(x, y, TipoCelda.VIA)
        for cx in centros_x:  # intersecciones (sobrescriben cruces)
            for cy in centros_y:
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        x, y = cx + dx, cy + dy
                        if 0 <= x < ancho and 0 <= y < alto:
                            ent.asignar_tipo_celda(x, y, TipoCelda.INTERSECCION)
        for cx in centros_x:  # carril central intransitable (vertical)
            for y in range(alto):
                if ent.obtener_tipo_celda(cx, y) == TipoCelda.VIA:
                    ent.asignar_tipo_celda(cx, y, TipoCelda.VACIA)
        for cy in centros_y:  # carril central intransitable (horizontal)
            for x in range(ancho):
                if ent.obtener_tipo_celda(x, cy) == TipoCelda.VIA:
                    ent.asignar_tipo_celda(x, cy, TipoCelda.VACIA)
    else:  # 1x1: una cruz central
        cx, cy = ancho // 2, alto // 2
        x0_v, x1_v = max(0, cx - half), min(ancho, cx + half + 1)  # rango vía vertical
        y0_h, y1_h = max(0, cy - half), min(alto, cy + half + 1)  # rango vía horizontal
        for x in range(x0_v, x1_v):  # pinta vía vertical
            for y in range(alto):
                ent.asignar_tipo_celda(x, y, TipoCelda.VIA)
        for y in range(y0_h, y1_h):  # pinta vía horizontal
            for x in range(ancho):
                ent.asignar_tipo_celda(x, y, TipoCelda.VIA)
        for dy in range(-r, r + 1):  # intersección central
            for dx in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < ancho and 0 <= y < alto:
                    ent.asignar_tipo_celda(x, y, TipoCelda.INTERSECCION)
        for y in range(alto):  # carril central vertical vacío
            if ent.obtener_tipo_celda(cx, y) == TipoCelda.VIA:
                ent.asignar_tipo_celda(cx, y, TipoCelda.VACIA)
        for x in range(ancho):  # carril central horizontal vacío
            if ent.obtener_tipo_celda(x, cy) == TipoCelda.VIA:
                ent.asignar_tipo_celda(x, cy, TipoCelda.VACIA)

    spawns_por_direccion: Dict[str, List[Tuple[int, int]]] = {  # celdas spawn por dirección
        "norte": [], "sur": [], "este": [], "oeste": [],
    }
    for y in range(alto):  # detectar spawns en bordes
        for x in range(ancho):
            if ent.obtener_tipo_celda(x, y) != TipoCelda.VIA:
                continue
            if y == 0:  # borde sur (entran hacia norte)
                spawns_por_direccion["sur"].append((x, y))
            if y == alto - 1:  # borde norte
                spawns_por_direccion["norte"].append((x, y))
            if x == 0:  # borde este
                spawns_por_direccion["este"].append((x, y))
            if x == ancho - 1:  # borde oeste
                spawns_por_direccion["oeste"].append((x, y))

    return ent, spawns_por_direccion


class SimulacionTrafico(SimulacionBase):  # simulación tráfico con semáforos y giros
    _DESPLAZAMIENTO = {  # (dx, dy) por dirección (y crece hacia abajo)
        "norte": (0, -1),
        "sur": (0, 1),
        "este": (1, 0),
        "oeste": (-1, 0),
    }
    _GIRO_A_DIRECCION = {  # (direccion_actual, intencion_giro) -> direccion_salida
        "este": {"recto": "este", "izquierda": "norte", "derecha": "sur"},
        "oeste": {"recto": "oeste", "izquierda": "sur", "derecha": "norte"},
        "norte": {"recto": "norte", "izquierda": "oeste", "derecha": "este"},
        "sur": {"recto": "sur", "izquierda": "este", "derecha": "oeste"},
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
        cola_umbral: int = 12,
        factor_reduccion_spawn: float = 0.5,
        p_spawn_min: float = 0.05,
        p_giro_izq: float = 0.15,
        p_giro_der: float = 0.20,
    ) -> None:
        super().__init__(entorno=entorno, semilla=semilla, max_eventos=max_eventos)
        self.semaforo = ControladorSemaforos(  # controlador único
            ticks_verde=ticks_verde,
            ticks_amarillo=ticks_amarillo,
            ticks_todo_rojo=ticks_todo_rojo,
        )
        self.p_spawn = p_spawn
        self.prob_direccion = probabilidades_direccion or {  # prob por dirección al spawn
            "norte": 0.25, "sur": 0.25, "este": 0.25, "oeste": 0.25,
        }
        self.max_vehiculos = max_vehiculos
        self.p_pasarse_amarillo = p_pasarse_amarillo
        self.p_pasarse_rojo = p_pasarse_rojo
        self.ancho_via = ancho_via
        self.cola_umbral = cola_umbral
        self.factor_reduccion_spawn = factor_reduccion_spawn
        self.p_spawn_min = p_spawn_min
        self.p_spawn_efectivo_ultimo = self.p_spawn  # último usado (para debug/métricas)
        self.p_giro_izq = p_giro_izq
        self.p_giro_der = p_giro_der
        self._id_siguiente = 0  # próximo id de vehículo

        self._spawns_por_direccion: Dict[str, List[Tuple[int, int]]] = {
            "norte": [], "sur": [], "este": [], "oeste": [],
        }
        if spawns_por_direccion is not None:  # usar los que nos pasan
            self._spawns_por_direccion = dict(spawns_por_direccion)
        else:  # o detectar desde el mapa
            self._inicializar_spawns()

        self.vehiculos_salidos = 0
        self.tiempos_espera_salidos: List[int] = []  # espera de cada veh que salió
        self.cola_por_tick: List[int] = []
        self.flujo_por_tick: List[int] = []  # salidas por tick
        self.movimientos_por_tick: List[int] = []
        self.entradas_interseccion_ultimo_tick: List[Tuple[int, str, bool]] = []

        self.hubo_accidente = False
        self.info_accidente: Dict[str, Any] = {}
        self.contador_pasos_en_rojo = 0
        self.contador_pasos_en_amarillo = 0
        self.tick_accidente: int | None = None

        self._bboxes_interseccion: List[Tuple[int, int, int, int]] = []  # bbox por cluster
        self._inicializar_bboxes_interseccion()

    def _inicializar_bboxes_interseccion(self) -> None:  # precalcula bbox por cluster intersección
        terreno = self.entorno.terreno
        alto, ancho = terreno.shape
        visitado = set()
        self._bboxes_interseccion = []

        def vecinos(ix: int, iy: int):  # 4-vecinos que son INTERSECCION
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = ix + ddx, iy + ddy
                if 0 <= nx < ancho and 0 <= ny < alto and int(terreno[ny, nx]) == TipoCelda.INTERSECCION:
                    yield (nx, ny)

        for j in range(alto):
            for i in range(ancho):
                if (i, j) in visitado or int(terreno[j, i]) != TipoCelda.INTERSECCION:
                    continue
                stack = [(i, j)]  # flood-fill
                min_x, min_y, max_x, max_y = i, j, i, j
                while stack:
                    x, y = stack.pop()
                    if (x, y) in visitado:
                        continue
                    visitado.add((x, y))
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
                    for nn in vecinos(x, y):
                        if nn not in visitado:
                            stack.append(nn)
                self._bboxes_interseccion.append((min_x, min_y, max_x, max_y))

    def _es_transitable(self, x: int, y: int) -> bool:  # solo VÍA e INTERSECCION
        if not self.entorno.en_limites(x, y):
            return False
        t = self.entorno.obtener_tipo_celda(x, y)
        return t in (TipoCelda.VIA, TipoCelda.INTERSECCION)

    def _bbox_interseccion_de(self, x: int, y: int) -> Tuple[int, int, int, int] | None:  # bbox que contiene (x,y)
        for (min_x, min_y, max_x, max_y) in self._bboxes_interseccion:
            if min_x <= x <= max_x and min_y <= y <= max_y:
                return (min_x, min_y, max_x, max_y)
        return None

    def _centro_interseccion(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:  # (cx, cy) del bbox
        min_x, min_y, max_x, max_y = bbox
        return ((min_x + max_x) // 2, (min_y + max_y) // 2)

    def _carril_objetivo(self, direccion: str, cx: int, cy: int) -> Tuple[int | None, int | None]:  # carril (x o y) por dirección
        if direccion == "norte":
            return (cx + 1, None)
        if direccion == "sur":
            return (cx - 1, None)
        if direccion == "este":
            return (None, cy + 1)
        if direccion == "oeste":
            return (None, cy - 1)
        return (None, None)

    def _carril_valido(self, direccion: str, cx: int, cy: int, x: int, y: int) -> bool:  # (x,y) es el carril de esa dirección
        lane_x, lane_y = self._carril_objetivo(direccion, cx, cy)
        if lane_x is not None:
            return x == lane_x
        if lane_y is not None:
            return y == lane_y
        return False

    def _es_carril_valido_para_pos(self, x: int, y: int, direccion: str) -> bool:  # algún bbox lo tiene como carril válido
        for bbox in self._bboxes_interseccion:
            cx, cy = self._centro_interseccion(bbox)
            if self._carril_valido(direccion, cx, cy, x, y):
                return True
        return False

    def _es_centro_carril(self, x: int, y: int, direccion: str) -> bool:  # (x,y) es celda central (intransitable)
        for bbox in self._bboxes_interseccion:
            cx, cy = self._centro_interseccion(bbox)
            if direccion in ("norte", "sur") and x == cx:
                return True
            if direccion in ("este", "oeste") and y == cy:
                return True
        return False

    def _paso_en_interseccion(  # devuelve (dx, dy) para ir hacia dir_salida desde (x,y) en bbox
        self, x: int, y: int, dir_salida: str, bbox: Tuple[int, int, int, int]
    ) -> Tuple[int, int]:
        min_x, min_y, max_x, max_y = bbox
        cx = (min_x + max_x) // 2
        cy = (min_y + max_y) // 2
        if dir_salida == "norte":
            target_x = cx + 1
            if x < target_x:
                return (1, 0)
            if x > target_x:
                return (-1, 0)
            return (0, -1)
        if dir_salida == "sur":
            target_x = cx - 1
            if x < target_x:
                return (1, 0)
            if x > target_x:
                return (-1, 0)
            return (0, 1)
        if dir_salida == "este":
            target_y = cy + 1
            if y < target_y:
                return (0, 1)
            if y > target_y:
                return (0, -1)
            return (1, 0)
        if dir_salida == "oeste":
            target_y = cy - 1
            if y < target_y:
                return (0, 1)
            if y > target_y:
                return (0, -1)
            return (-1, 0)
        return (0, 0)

    def _snap_a_carril_si_hace_falta(self, vid: int) -> None:  # corrige veh en VÍA mal alineado al carril
        v = self.agentes.get(vid)
        if v is None or v.estado in ("accidentado", "fuera"):
            return
        px, py = self.entorno.obtener_posicion_agente(vid)
        if self.entorno.obtener_tipo_celda(px, py) != TipoCelda.VIA:  # solo en vía
            return
        if self._es_carril_valido_para_pos(px, py, v.direccion):  # ya está bien
            return
        tx, ty = None, None
        for bbox in self._bboxes_interseccion:
            cx, cy = self._centro_interseccion(bbox)
            if v.direccion in ("norte", "sur"):  # vertical: carril es cx+1 o cx-1
                if px in (cx - 1, cx + 1):
                    lane_x, _ = self._carril_objetivo(v.direccion, cx, cy)
                    tx, ty = lane_x, py
                    break
            else:  # horizontal
                if py in (cy - 1, cy + 1):
                    _, lane_y = self._carril_objetivo(v.direccion, cx, cy)
                    tx, ty = px, lane_y
                    break
        if tx is None or ty is None:
            return
        if (tx, ty) == (px, py):
            return
        if self.entorno.en_limites(tx, ty) and self.entorno.esta_libre(tx, ty) and self._es_transitable(tx, ty):
            self.entorno.mover_agente(vid, tx, ty)
            self.registrar_evento(f"[t={self.tiempo}] Veh {vid} snap a carril correcto ({px},{py})->({tx},{ty})")
        else:
            self.registrar_evento(f"[t={self.tiempo}] Veh {vid} mal alineado en ({px},{py}), carril objetivo ({tx},{ty}) ocupado")

    def _inicializar_spawns(self) -> None:  # detecta celdas VÍA en bordes
        ancho, alto = self.entorno.ancho, self.entorno.alto
        for y in range(alto):
            for x in range(ancho):
                if self.entorno.obtener_tipo_celda(x, y) != TipoCelda.VIA:
                    continue
                if y == 0:
                    self._spawns_por_direccion["sur"].append((x, y))
                if y == alto - 1:
                    self._spawns_por_direccion["norte"].append((x, y))
                if x == 0:
                    self._spawns_por_direccion["este"].append((x, y))
                if x == ancho - 1:
                    self._spawns_por_direccion["oeste"].append((x, y))

    def _intentar_spawn(self) -> None:  # anti-congestión: reduce p_spawn si cola alta
        if len(self.agentes) >= self.max_vehiculos:
            return
        cola_actual = sum(1 for v in self.agentes.values() if getattr(v, "estado", "") == "en_cola")
        niveles = max(0, (cola_actual - self.cola_umbral) // max(1, self.cola_umbral))
        if cola_actual >= self.cola_umbral:
            multiplicador = self.factor_reduccion_spawn ** (1 + niveles)
        else:
            multiplicador = 1.0
        factor_ocup = max(0.2, 1.0 - len(self.agentes) / max(1, self.max_vehiculos))  # menos spawn si muchos veh
        p_spawn_efectivo = max(self.p_spawn_min, self.p_spawn * multiplicador * factor_ocup)
        self.p_spawn_efectivo_ultimo = p_spawn_efectivo
        if self.generador.random() > p_spawn_efectivo:
            return
        dirs = list(self.prob_direccion.keys())
        probs = [self.prob_direccion[d] for d in dirs]
        probs = [p / sum(probs) for p in probs]  # normalizar
        direccion = str(self.generador.choice(dirs, p=probs))
        candidatas = [  # spawns de esa dirección libres y en carril válido
            p for p in self._spawns_por_direccion.get(direccion, [])
            if self.entorno.esta_libre(p[0], p[1]) and self._es_carril_valido_para_pos(p[0], p[1], direccion)
        ]
        if not candidatas:
            return
        pos = candidatas[self.generador.integers(0, len(candidatas))]
        vid = self._id_siguiente
        self._id_siguiente += 1
        perfil = 0.8 + 0.4 * self.generador.random()  # perfil riesgo aleatorio
        p_recto = max(0.0, 1.0 - self.p_giro_izq - self.p_giro_der)
        probs = [p_recto, self.p_giro_izq, self.p_giro_der]
        s = sum(probs)
        if s > 0:
            probs = [p / s for p in probs]
        intencion_giro = str(self.generador.choice(["recto", "izquierda", "derecha"], p=probs))
        kwargs = dict(  # args comunes Vehiculo
            id_agente=vid,
            direccion=direccion,
            estado="en_cola",
            espera_acumulada=0,
            perfil_riesgo=perfil,
        )
        try:
            v = Vehiculo(**kwargs, intencion_giro=intencion_giro)
        except TypeError:  # versión vieja sin intencion_giro
            v = Vehiculo(**kwargs, intencion=intencion_giro)
        if not hasattr(v, "intencion_giro"):
            setattr(v, "intencion_giro", intencion_giro)
        if not hasattr(v, "intencion"):
            setattr(v, "intencion", intencion_giro)
        self.agregar_agente(v, pos[0], pos[1])
        self.registrar_evento(f"[t={self.tiempo}] Veh {vid} spawneado en {pos} dir={direccion}")

    def _es_interseccion(self, x: int, y: int) -> bool:
        return self.entorno.obtener_tipo_celda(x, y) == TipoCelda.INTERSECCION

    def _puede_entrar_legal(self, direccion: str) -> bool:  # luz verde para esa dirección
        return self.semaforo.puede_pasar(direccion)

    def _registrar_accidente(  # wrapper con tipo violación (amarillo/rojo)
        self, vid: int, otro_id: int, dest_x: int, dest_y: int, tipo_violacion: str
    ) -> None:
        self._registrar_accidente_choque(vid, otro_id, dest_x, dest_y, causa=f"paso_en_{tipo_violacion}", tipo_violacion=tipo_violacion)

    def _registrar_accidente_choque(  # marca accidente, detiene sim, pone estado accidentado
        self,
        vid: int,
        otro_id: int,
        dest_x: int,
        dest_y: int,
        causa: str = "colision",
        tipo_violacion: str | None = None,
    ) -> None:
        v = self.agentes.get(vid)
        otro = self.agentes.get(otro_id)
        if v is None or otro is None:
            return
        self.hubo_accidente = True
        self.tick_accidente = self.tiempo
        self.info_accidente = {  # datos del accidente
            "vehiculos": [vid, otro_id],
            "posicion": (dest_x, dest_y),
            "causa": causa,
        }
        if tipo_violacion is not None:
            self.info_accidente["tipo_violacion"] = tipo_violacion
        v.estado = "accidentado"
        otro.estado = "accidentado"
        self.registrar_evento(
            f"[t={self.tiempo}] ACCIDENTE: Veh {vid} chocó con Veh {otro_id} en ({dest_x},{dest_y}) causa={causa}"
        )
        self.detener = True

    def paso(self) -> None:  # un tick: semáforo, snap, intentos, swap, intenciones, movimientos, spawn
        self.semaforo.actualizar()  # avanza timer semáforo
        self.entradas_interseccion_ultimo_tick = []
        flujo_este_tick = 0  # cuántos vehículos salen este tick
        intenciones: Dict[int, Tuple[int, int]] = {}  # vid -> (nx, ny) a aplicar
        orden = sorted(self.agentes.keys())

        for vid in list(orden):  # snap carril antes de calcular intentos
            self._snap_a_carril_si_hace_falta(vid)

        intentos: Dict[int, Tuple[int, int]] = {}  # destino previsto por vehículo
        for vid in orden:
            v = self.agentes.get(vid)
            if v is None or v.estado == "accidentado" or v.estado == "fuera":
                continue
            px, py = self.entorno.obtener_posicion_agente(vid)
            if getattr(v, "estado", "") == "en_interseccion":  # dentro de intersección: guiar hacia salida
                dir_salida = self._GIRO_A_DIRECCION.get(v.direccion, {}).get(
                    getattr(v, "intencion_giro", "recto"), v.direccion
                )
                bbox = self._bbox_interseccion_de(px, py)
                if bbox:
                    dx, dy = self._paso_en_interseccion(px, py, dir_salida, bbox)
                else:
                    dx, dy = self._DESPLAZAMIENTO[dir_salida]
            else:
                dx, dy = self._DESPLAZAMIENTO[v.direccion]
            nx, ny = px + dx, py + dy

            if not self.entorno.en_limites(nx, ny):  # se sale del mapa -> lo quitamos
                self.entorno.posicion_a_agente.pop((px, py), None)
                self.entorno.agente_a_posicion.pop(vid, None)
                del self.agentes[vid]
                self.vehiculos_salidos += 1
                self.tiempos_espera_salidos.append(v.espera_acumulada)
                flujo_este_tick += 1
                self.registrar_evento(f"[t={self.tiempo}] Veh {vid} salió dir={v.direccion} espera={v.espera_acumulada}")
                continue

            if getattr(v, "estado", "") in ("en_interseccion", "cruzando"):  # ya en intersección: destino fijo
                intentos[vid] = (nx, ny)
                continue
            if not self._es_interseccion(nx, ny):  # destino no es intersección
                if not self._es_transitable(nx, ny) or not self._es_carril_valido_para_pos(nx, ny, v.direccion):
                    continue
                intentos[vid] = (nx, ny)
                continue
            puede_legal = self._puede_entrar_legal(v.direccion)  # luz verde
            violacion_amarillo = self.semaforo.esta_amarillo_para(v.direccion)
            violacion_rojo = self.semaforo.esta_rojo_para(v.direccion)
            intenta_pasar = puede_legal
            if violacion_amarillo and self.generador.random() < min(1.0, self.p_pasarse_amarillo * v.perfil_riesgo):  # se pasa amarillo
                intenta_pasar = True
                self.contador_pasos_en_amarillo += 1
            if violacion_rojo and not intenta_pasar and self.generador.random() < min(1.0, self.p_pasarse_rojo * v.perfil_riesgo):  # se pasa rojo
                intenta_pasar = True
                self.contador_pasos_en_rojo += 1
            if not intenta_pasar:
                continue
            dir_salida = self._GIRO_A_DIRECCION.get(v.direccion, {}).get(getattr(v, "intencion_giro", "recto"), v.direccion)
            ddx, ddy = self._DESPLAZAMIENTO[dir_salida]
            sx, sy = nx + ddx, ny + ddy  # celda siguiente tras salir (evitar bloqueo)
            if self.entorno.en_limites(sx, sy) and not self.entorno.esta_libre(sx, sy):  # no entrar si salida bloqueada
                continue
            if self._es_transitable(nx, ny):
                intentos[vid] = (nx, ny)

        pos_por_vid = {vid: self.entorno.obtener_posicion_agente(vid) for vid in intentos if vid in self.agentes}  # pos actual para detectar swap
        for aid in list(intentos.keys()):  # detección swap: A->posB y B->posA
            if aid not in self.agentes or self.agentes[aid].estado == "accidentado":
                continue
            for bid in list(intentos.keys()):
                if aid >= bid or bid not in self.agentes or self.agentes[bid].estado == "accidentado":
                    continue
                if intentos[aid] == pos_por_vid.get(bid) and intentos[bid] == pos_por_vid.get(aid):
                    self._registrar_accidente_choque(aid, bid, intentos[aid][0], intentos[aid][1], causa="swap")
                    return

        for vid in orden:  # decidir quién puede moverse (intenciones)
            v = self.agentes.get(vid)
            if v is None or v.estado == "accidentado" or v.estado == "fuera":
                continue
            if vid not in intentos:  # no tiene destino este tick
                v.espera_acumulada += 1
                continue
            nx, ny = intentos[vid]
            px, py = self.entorno.obtener_posicion_agente(vid)
            if getattr(v, "estado", "") in ("en_interseccion", "cruzando"):  # ya dentro: comprobar destino libre
                if not self._es_transitable(nx, ny):
                    v.espera_acumulada += 1
                elif self.entorno.esta_libre(nx, ny):
                    intenciones[vid] = (nx, ny)
                else:
                    otro_id = self.entorno.posicion_a_agente.get((nx, ny))
                    if otro_id is not None:
                        vb = self.agentes.get(otro_id)
                        if vb and vb.direccion == v.direccion:
                            v.espera_acumulada += 1
                        else:
                            self._registrar_accidente_choque(vid, otro_id, nx, ny, causa="colision")
                            return
                    else:
                        v.espera_acumulada += 1
                continue
            if not self._es_interseccion(nx, ny):  # destino en vía (no intersección)
                if not self._es_transitable(nx, ny) or not self._es_carril_valido_para_pos(nx, ny, v.direccion):
                    v.espera_acumulada += 1
                elif self.entorno.esta_libre(nx, ny):
                    intenciones[vid] = (nx, ny)
                else:
                    otro_id = self.entorno.posicion_a_agente.get((nx, ny))
                    if otro_id is not None:
                        vb = self.agentes.get(otro_id)
                        if vb and vb.direccion == v.direccion:
                            v.espera_acumulada += 1
                        else:
                            self._registrar_accidente_choque(vid, otro_id, nx, ny, causa="colision")
                            return
                    else:
                        v.espera_acumulada += 1
                continue
            puede_legal = self._puede_entrar_legal(v.direccion)
            violacion_amarillo = self.semaforo.esta_amarillo_para(v.direccion)
            violacion_rojo = self.semaforo.esta_rojo_para(v.direccion)
            intenta_pasar = puede_legal
            es_violacion = False
            tipo_violacion = ""
            if violacion_amarillo:
                es_violacion = True
                tipo_violacion = "amarillo"
            if violacion_rojo and not intenta_pasar:
                es_violacion = True
                tipo_violacion = "rojo"
            if not intenta_pasar:  # no pasa: espera
                v.espera_acumulada += 1
                if v.espera_acumulada % 5 == 0:
                    self.registrar_evento(f"[t={self.tiempo}] Veh {vid} espera semáforo (espera={v.espera_acumulada})")
                continue
            dir_salida = self._GIRO_A_DIRECCION.get(v.direccion, {}).get(getattr(v, "intencion_giro", "recto"), v.direccion)
            ddx, ddy = self._DESPLAZAMIENTO[dir_salida]
            sx, sy = nx + ddx, ny + ddy
            if self.entorno.en_limites(sx, sy) and not self.entorno.esta_libre(sx, sy):  # salida bloqueada
                v.espera_acumulada += 1
                continue
            if not self._es_transitable(nx, ny):
                v.espera_acumulada += 1
                continue
            if self.entorno.esta_libre(nx, ny):
                intenciones[vid] = (nx, ny)
                self.entradas_interseccion_ultimo_tick.append((vid, "ok", puede_legal))
            else:  # destino ocupado: colisión o accidente por violación
                otro_id = self.entorno.posicion_a_agente.get((nx, ny))
                if otro_id is not None:
                    vb = self.agentes.get(otro_id)
                    if vb and vb.direccion == v.direccion:
                        v.espera_acumulada += 1
                    elif es_violacion and tipo_violacion:
                        self._registrar_accidente(vid, otro_id, nx, ny, tipo_violacion)
                        return
                    else:
                        self._registrar_accidente_choque(vid, otro_id, nx, ny, causa="colision")
                        return
                else:
                    v.espera_acumulada += 1

        movimientos_este_tick = 0
        for vid in orden:  # aplicar movimientos
            if vid not in intenciones:
                continue
            dest = intenciones[vid]
            v = self.agentes.get(vid)
            if v is None or v.estado == "accidentado":
                continue
            if not self._es_transitable(dest[0], dest[1]):
                v.espera_acumulada += 1
                continue
            if not self.entorno.esta_libre(dest[0], dest[1]):
                v.espera_acumulada += 1
                continue
            pos_ant = self.entorno.obtener_posicion_agente(vid)
            self.entorno.mover_agente(vid, dest[0], dest[1])
            movimientos_este_tick += 1
            if self._es_interseccion(dest[0], dest[1]):  # entró en intersección
                v.estado = "en_interseccion"
                giro = getattr(v, "intencion_giro", "recto")
                self.registrar_evento(f"[t={self.tiempo}] Veh {vid} entró intersección (giro={giro})")
            else:  # en vía
                v.estado = "en_cola"
                if self._es_interseccion(pos_ant[0], pos_ant[1]):  # salió de intersección: actualizar dirección e intención
                    dx, dy = dest[0] - pos_ant[0], dest[1] - pos_ant[1]
                    dir_salida = next((d for d, (ddx, ddy) in self._DESPLAZAMIENTO.items() if ddx == dx and ddy == dy), v.direccion)
                    v.direccion = dir_salida
                    self.registrar_evento(f"[t={self.tiempo}] Veh {vid} giró a {dir_salida}")
                    p_recto = max(0.0, 1.0 - self.p_giro_izq - self.p_giro_der)
                    probs = [p_recto, self.p_giro_izq, self.p_giro_der]
                    s = sum(probs)
                    if s > 0:
                        probs = [p / s for p in probs]
                    v.intencion_giro = str(self.generador.choice(["recto", "izquierda", "derecha"], p=probs))
            self.registrar_evento(f"[t={self.tiempo}] Veh {vid} {pos_ant}->{dest}")

        en_cola = sum(1 for v in self.agentes.values() if getattr(v, "estado", "") == "en_cola")
        self.cola_por_tick.append(en_cola)
        self.flujo_por_tick.append(flujo_este_tick)
        self.movimientos_por_tick.append(movimientos_este_tick)
        self._intentar_spawn()  # intentar spawnear un vehículo