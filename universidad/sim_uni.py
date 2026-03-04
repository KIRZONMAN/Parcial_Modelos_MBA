"""
universidad/sim_uni.py
----------------------
Simulación MBA Universidad — paquete medio realista.

Reglas: hambre → prioridad cafetería; permanencia mínima; afinidad sesga elección;
aula saturada → salida según p_ir_cafeteria y afinidad.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from motor.grid import MundoCuadricula, TipoCelda
from motor.sim_base import SimulacionBase
from universidad.agentes_uni import Estudiante


class SimulacionUniversidad(SimulacionBase):
    def __init__(
        self,
        entorno: MundoCuadricula,
        n_estudiantes: int = 25,
        semilla: int = 123,
        cap_aula: int = 20,
        cap_biblio: int = 15,
        cap_cafe: int = 10,
        umbral_aula: int = 18,
        p_volver_aula: float = 0.10,
        enfriamiento_mov: int = 2,
        p_ir_cafeteria: float = 0.25,
        # Afinidades (perfiles)
        p_afinidad_cafe: float = 0.30,
        p_afinidad_biblio: float = 0.45,
        p_afinidad_aula: float = 0.25,
        # Permanencia mínima (ticks) por zona
        permanencia_min_aula: int = 3,
        permanencia_min_biblioteca: int = 2,
        permanencia_min_cafeteria: int = 2,
        permanencia_max_aula: int = 30,
        permanencia_max_biblioteca: int = 20,
        permanencia_max_cafeteria: int = 15,
        # Hambre
        hambre_max: int = 15,
        umbral_hambre: int = 10,
        delta_hambre_tick: int = 1,
        delta_hambre_cafe: int = 5,
        max_eventos: int = 5000,
    ) -> None:
        super().__init__(entorno=entorno, semilla=semilla, max_eventos=max_eventos)
        self.n_estudiantes = n_estudiantes
        self.cap_aula = cap_aula
        self.cap_biblio = cap_biblio
        self.cap_cafe = cap_cafe
        self.umbral_aula = umbral_aula
        self.p_volver_aula = p_volver_aula
        self.enfriamiento_mov = enfriamiento_mov
        self.p_ir_cafeteria = p_ir_cafeteria
        self.p_afinidad_cafe = p_afinidad_cafe
        self.p_afinidad_biblio = p_afinidad_biblio
        self.p_afinidad_aula = p_afinidad_aula
        self.permanencia_min_aula = permanencia_min_aula
        self.permanencia_min_biblioteca = permanencia_min_biblioteca
        self.permanencia_min_cafeteria = permanencia_min_cafeteria
        self.permanencia_max_aula = permanencia_max_aula
        self.permanencia_max_biblioteca = permanencia_max_biblioteca
        self.permanencia_max_cafeteria = permanencia_max_cafeteria
        self.hambre_max = hambre_max
        self.umbral_hambre = umbral_hambre
        self.delta_hambre_tick = delta_hambre_tick
        self.delta_hambre_cafe = delta_hambre_cafe

        self.celdas_aula = self.entorno.celdas_de_tipo(TipoCelda.AULA)
        self.celdas_biblioteca = self.entorno.celdas_de_tipo(TipoCelda.BIBLIOTECA)
        self.celdas_cafeteria = self.entorno.celdas_de_tipo(TipoCelda.CAFETERIA)
        # Validación: existen celdas de las 3 zonas (capacidades son límites lógicos, no físicos)
        assert len(self.celdas_aula) > 0, "Debe haber al menos una celda de tipo AULA"
        assert len(self.celdas_biblioteca) > 0, "Debe haber al menos una celda de tipo BIBLIOTECA"
        assert len(self.celdas_cafeteria) > 0, "Debe haber al menos una celda de tipo CAFETERIA"

        # Rango para umbral_hambre_personal (evita hambre sincronizada)
        self.umbral_hambre_min = max(1, int(umbral_hambre * 0.6))
        self.umbral_hambre_max = min(hambre_max - 1, int(umbral_hambre * 1.4))

        # Métricas extra
        self.intentos_bloqueados = 0
        self.intentos_totales = 0
        self.movimientos_este_tick: List[int] = []  # para movimientos_por_tick

        self._inicializar_agentes()

    def _escoger_afinidad(self) -> str:
        r = self.generador.random()
        if r < self.p_afinidad_cafe:
            return "cafeteria"
        if r < self.p_afinidad_cafe + self.p_afinidad_biblio:
            return "biblioteca"
        return "aula"

    def _ticks_permanencia(self, zona: str) -> int:
        vmin = getattr(self, f"permanencia_min_{zona}", 1)
        vmax = getattr(self, f"permanencia_max_{zona}", 10)
        return int(self.generador.integers(vmin, max(vmin, vmax) + 1))

    def _inicializar_agentes(self) -> None:
        for i in range(self.n_estudiantes):
            est = Estudiante(id_agente=i)
            est.afinidad_zona = self._escoger_afinidad()
            # Desincronizar hambre: umbral personal y metabolismo
            est.umbral_hambre_personal = float(self.generador.uniform(
                self.umbral_hambre_min, self.umbral_hambre_max
            ))
            est.metabolismo = float(self.generador.uniform(0.7, 1.3))
            # Micro-ajuste: biblioteca-lovers resisten un poco más antes de ir a cafetería
            if est.afinidad_zona == "biblioteca":
                est.umbral_hambre_personal += 2.5
                est.metabolismo *= 0.95

            pos = self._escoger_posicion_inicial()
            self.agregar_agente(est, pos[0], pos[1])

            est.zona_actual = self._zona_por_celda(pos)
            est.enfriamiento = int(self.generador.integers(0, self.enfriamiento_mov + 1))
            est.ticks_restantes_en_zona = self._ticks_permanencia(est.zona_actual)
            est.visitas_por_zona[est.zona_actual] = 1

            self.registrar_evento(
                f"[t={self.tiempo}] Estudiante {est.id_agente} creado en {est.zona_actual} pos={pos} afinidad={est.afinidad_zona}"
            )

    def _escoger_posicion_inicial(self) -> Tuple[int, int]:
        try:
            return self.entorno.celda_libre_aleatoria(self.generador, permitidas=self.celdas_aula)
        except RuntimeError:
            pass
        try:
            return self.entorno.celda_libre_aleatoria(self.generador, permitidas=self.celdas_biblioteca)
        except RuntimeError:
            pass
        return self.entorno.celda_libre_aleatoria(self.generador, permitidas=self.celdas_cafeteria)

    def _zona_por_celda(self, pos: Tuple[int, int]) -> str:
        x, y = pos
        tipo = self.entorno.obtener_tipo_celda(x, y)
        if tipo == TipoCelda.AULA:
            return "aula"
        if tipo == TipoCelda.BIBLIOTECA:
            return "biblioteca"
        if tipo == TipoCelda.CAFETERIA:
            return "cafeteria"
        return "otro"

    def _ocupacion_por_zona(self) -> Dict[str, int]:
        c = {"aula": 0, "biblioteca": 0, "cafeteria": 0, "otro": 0}
        for aid in self.agentes:
            pos = self.entorno.obtener_posicion_agente(aid)
            c[self._zona_por_celda(pos)] += 1
        return c

    def _intentar_mover_a_zona(self, id_agente: int, zona_objetivo: str) -> bool:
        if zona_objetivo == "aula":
            permitidas = self.celdas_aula
        elif zona_objetivo == "biblioteca":
            permitidas = self.celdas_biblioteca
        else:
            permitidas = self.celdas_cafeteria

        pos_ant = self.entorno.obtener_posicion_agente(id_agente)
        zona_ant = self._zona_por_celda(pos_ant)

        self.intentos_totales += 1
        try:
            nueva = self.entorno.celda_libre_aleatoria(self.generador, permitidas=permitidas)
        except RuntimeError:
            self.intentos_bloqueados += 1
            self.registrar_evento(
                f"[t={self.tiempo}] Estudiante {id_agente} destino bloqueado: {zona_objetivo} (sin celdas libres)"
            )
            return False

        est = self.agentes[id_agente]
        est.visitas_por_zona[zona_objetivo] = est.visitas_por_zona.get(zona_objetivo, 0) + 1

        self.entorno.mover_agente(id_agente, nueva[0], nueva[1])
        est.zona_actual = zona_objetivo
        est.ticks_restantes_en_zona = self._ticks_permanencia(zona_objetivo)

        self.registrar_evento(
            f"[t={self.tiempo}] Estudiante {id_agente} se movió: {zona_ant} {pos_ant} -> {zona_objetivo} {nueva}"
        )
        return True

    def _peso_afinidad_hacia(self, est: Estudiante, zona: str) -> float:
        """Peso para elegir zona según afinidad (1.0 base, más si coincide)."""
        if est.afinidad_zona == zona:
            return 1.5
        return 1.0

    def paso(self) -> None:
        # Ocupación inicial (se actualiza tras cada movimiento para evitar "foto vieja")
        occ = self._ocupacion_por_zona()
        self.registrar_metrica("ocup_aula", occ["aula"])
        self.registrar_metrica("ocup_biblioteca", occ["biblioteca"])
        self.registrar_metrica("ocup_cafeteria", occ["cafeteria"])
        self.movimientos_este_tick = []

        # Actualizar hambre de todos (con metabolismo por agente)
        hambre_acum = 0
        for est in self.agentes.values():
            if est.zona_actual == "cafeteria":
                est.hambre = max(0, est.hambre - self.delta_hambre_cafe)
            else:
                delta = max(1, int(round(self.delta_hambre_tick * est.metabolismo)))
                est.hambre = min(self.hambre_max, est.hambre + delta)
            hambre_acum += est.hambre
        if self.agentes:
            self.registrar_metrica("promedio_hambre", hambre_acum / len(self.agentes))

        # Orden aleatorio para evitar sesgo por orden de procesamiento
        orden = list(self.agentes.keys())
        self.generador.shuffle(orden)

        for aid in orden:
            est = self.agentes[aid]
            pos = self.entorno.obtener_posicion_agente(aid)
            zona = self._zona_por_celda(pos)
            est.zona_actual = zona

            if zona in est.tiempo_por_zona:
                est.tiempo_por_zona[zona] += 1

            # Permanencia mínima: no decidir si aún faltan ticks
            if est.ticks_restantes_en_zona > 0:
                est.ticks_restantes_en_zona -= 1
                est.enfriamiento = max(0, est.enfriamiento - 1)
                continue

            if est.enfriamiento > 0:
                est.enfriamiento -= 1
                continue
            est.enfriamiento = self.enfriamiento_mov

            # Recalcular ocupación actual (tras movimientos previos en este tick)
            occ = self._ocupacion_por_zona()

            # p_ir_cafe como inclinación: base + k*hambre_normalizada + sesgo afinidad
            hambre_norm = est.hambre / max(1, self.hambre_max)
            p_base = self.p_ir_cafeteria
            k_hambre = 0.3
            sesgo_cafe = 0.1 if est.afinidad_zona == "cafeteria" else 0.0
            sesgo_biblio = 0.1 if est.afinidad_zona == "biblioteca" else 0.0
            p_ir_cafe_efectiva = min(0.85, max(0.15, p_base + k_hambre * hambre_norm + sesgo_cafe - sesgo_biblio))

            # 1) Hambre alta (umbral personal) → inclinación a cafetería, no obligación
            if est.hambre >= est.umbral_hambre_personal and occ["cafeteria"] < self.cap_cafe:
                if self.generador.random() < p_ir_cafe_efectiva:
                    if self._intentar_mover_a_zona(aid, "cafeteria"):
                        occ = self._ocupacion_por_zona()
                        self.movimientos_este_tick.append(aid)
                        self.registrar_evento(
                            f"[t={self.tiempo}] Estudiante {aid} decisión: hambre -> cafeteria"
                        )
                        continue
                # Si no fue a cafetería, puede ir a biblioteca si hay cupo y afinidad
                if occ["biblioteca"] < self.cap_biblio and est.afinidad_zona == "biblioteca":
                    if self.generador.random() < 0.4 and self._intentar_mover_a_zona(aid, "biblioteca"):
                        occ = self._ocupacion_por_zona()
                        self.movimientos_este_tick.append(aid)
                        continue

            # 2) Aula saturada → salir (biblio o cafe según p_ir_cafe_efectiva y afinidad)
            if zona == "aula" and occ["aula"] >= self.umbral_aula:
                biblio_cupo = occ["biblioteca"] < self.cap_biblio
                cafe_cupo = occ["cafeteria"] < self.cap_cafe
                if biblio_cupo and cafe_cupo:
                    w_cafe = p_ir_cafe_efectiva * self._peso_afinidad_hacia(est, "cafeteria")
                    w_biblio = (1.0 - p_ir_cafe_efectiva) * self._peso_afinidad_hacia(est, "biblioteca")
                    total = w_cafe + w_biblio
                    if total <= 0:
                        total = 1.0
                    if self.generador.random() < w_cafe / total:
                        if self._intentar_mover_a_zona(aid, "cafeteria"):
                            occ = self._ocupacion_por_zona()
                            self.movimientos_este_tick.append(aid)
                            continue
                        self._intentar_mover_a_zona(aid, "biblioteca")
                    else:
                        if self._intentar_mover_a_zona(aid, "biblioteca"):
                            occ = self._ocupacion_por_zona()
                            self.movimientos_este_tick.append(aid)
                            continue
                        self._intentar_mover_a_zona(aid, "cafeteria")
                    occ = self._ocupacion_por_zona()
                    continue
                if biblio_cupo:
                    if self._intentar_mover_a_zona(aid, "biblioteca"):
                        occ = self._ocupacion_por_zona()
                        self.movimientos_este_tick.append(aid)
                    continue
                if cafe_cupo:
                    if self._intentar_mover_a_zona(aid, "cafeteria"):
                        occ = self._ocupacion_por_zona()
                        self.movimientos_este_tick.append(aid)
                continue

            # 3) Biblioteca-lovers: en aula sin hambre alta, probabilidad de ir a biblioteca
            if zona == "aula" and est.hambre < est.umbral_hambre_personal:
                if occ["biblioteca"] < self.cap_biblio and est.afinidad_zona == "biblioteca":
                    if self.generador.random() < 0.12:  # p_ir_biblioteca_por_afinidad
                        if self._intentar_mover_a_zona(aid, "biblioteca"):
                            occ = self._ocupacion_por_zona()
                            self.movimientos_este_tick.append(aid)
                            continue

            # 4) Biblioteca/cafetería → volver aula (p_volver_aula)
            if zona in ("biblioteca", "cafeteria"):
                if self.generador.random() < self.p_volver_aula and occ["aula"] < self.cap_aula:
                    if self._intentar_mover_a_zona(aid, "aula"):
                        occ = self._ocupacion_por_zona()
                        self.movimientos_este_tick.append(aid)

        self.registrar_metrica("movimientos_por_tick", len(self.movimientos_este_tick))
        self.verificar_invariantes()
