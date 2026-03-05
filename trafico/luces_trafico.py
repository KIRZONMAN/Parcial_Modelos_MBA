"""
trafico/luces_trafico.py: este es el controlador central de semáforos: verde / amarillo / rojo.

Regla: solo una fase verde a la vez.
Ciclo: verde NS → amarillo NS → (opcional) todo_rojo → verde EO → amarillo EO → todo_rojo → etc...
"""

from __future__ import annotations  # compat tipos

from dataclasses import dataclass  # ControladorSemaforos
from typing import Literal  # EstadoLuz, FaseSemáforo

EstadoLuz = Literal["verde", "amarillo", "rojo"]  # estados de la luz
FaseSemáforo = Literal["norte_sur", "este_oeste"]  # fase actual (NS o EO)


@dataclass  # decorador
class ControladorSemaforos:  # control central semáforos
    ticks_verde: int = 5  # duración verde
    ticks_amarillo: int = 2  # duración amarillo
    ticks_todo_rojo: int = 1  # ticks todo rojo entre fases
    fase_actual: FaseSemáforo = "norte_sur"  # norte_sur o este_oeste
    estado_actual: EstadoLuz = "verde"  # verde/amarillo/rojo
    timer: int = 5  # cuenta atrás dentro de la fase

    def __post_init__(self) -> None:
        self.timer = self.ticks_verde  # arranca en verde

    def actualizar(self) -> None:
        self.timer -= 1  # un tick menos
        if self.timer > 0:  # sigue en la misma fase
            return
        if self.estado_actual == "verde":  # pasar a amarillo
            self.estado_actual = "amarillo"
            self.timer = self.ticks_amarillo
        elif self.estado_actual == "amarillo":  # pasar a rojo
            self.estado_actual = "rojo"
            self.timer = self.ticks_todo_rojo
        else:  # rojo -> cambiar fase y poner verde
            self.fase_actual = "este_oeste" if self.fase_actual == "norte_sur" else "norte_sur"
            self.estado_actual = "verde"
            self.timer = self.ticks_verde

    def luz_verde_norte_sur(self) -> bool:
        return self.fase_actual == "norte_sur" and self.estado_actual == "verde"  # NS en verde

    def luz_verde_este_oeste(self) -> bool:
        return self.fase_actual == "este_oeste" and self.estado_actual == "verde"  # EO en verde

    def luz_amarillo_norte_sur(self) -> bool:
        return self.fase_actual == "norte_sur" and self.estado_actual == "amarillo"  # NS en amarillo

    def luz_amarillo_este_oeste(self) -> bool:
        return self.fase_actual == "este_oeste" and self.estado_actual == "amarillo"  # EO en amarillo

    def puede_pasar(self, direccion: str) -> bool:
        if direccion in ("norte", "sur"):  # NS
            return self.luz_verde_norte_sur()
        if direccion in ("este", "oeste"):  # EO
            return self.luz_verde_este_oeste()
        return False  # dirección rara

    def esta_amarillo_para(self, direccion: str) -> bool:
        if direccion in ("norte", "sur"):
            return self.luz_amarillo_norte_sur()
        if direccion in ("este", "oeste"):
            return self.luz_amarillo_este_oeste()
        return False

    def esta_rojo_para(self, direccion: str) -> bool:
        return not self.puede_pasar(direccion) and not self.esta_amarillo_para(direccion)  # ni verde ni amarillo
