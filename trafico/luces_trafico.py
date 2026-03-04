"""
trafico/luces_trafico.py
------------------------
Controlador central de semáforos: verde / amarillo / rojo.

Regla: solo una fase verde a la vez.
Ciclo: verde NS → amarillo NS → (opcional) todo_rojo → verde EO → amarillo EO → todo_rojo → ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EstadoLuz = Literal["verde", "amarillo", "rojo"]
FaseSemáforo = Literal["norte_sur", "este_oeste"]


@dataclass
class ControladorSemaforos:
    """
    Control central: NS vs EO; solo una fase en verde.
    Amarillo = transición; todo_rojo = 1 tick de seguridad (opcional).
    """
    ticks_verde: int = 5
    ticks_amarillo: int = 2
    ticks_todo_rojo: int = 1
    fase_actual: FaseSemáforo = "norte_sur"
    # Estado dentro de la fase: "verde" | "amarillo" | "rojo" (todo_rojo)
    estado_actual: EstadoLuz = "verde"
    timer: int = 5

    def __post_init__(self) -> None:
        self.timer = self.ticks_verde

    def actualizar(self) -> None:
        """Avanza un tick; solo una fase verde a la vez."""
        self.timer -= 1
        if self.timer > 0:
            return

        if self.estado_actual == "verde":
            self.estado_actual = "amarillo"
            self.timer = self.ticks_amarillo
        elif self.estado_actual == "amarillo":
            self.estado_actual = "rojo"
            self.timer = self.ticks_todo_rojo
        else:
            # rojo (todo_rojo) -> cambio de fase
            self.fase_actual = "este_oeste" if self.fase_actual == "norte_sur" else "norte_sur"
            self.estado_actual = "verde"
            self.timer = self.ticks_verde

    def luz_verde_norte_sur(self) -> bool:
        return self.fase_actual == "norte_sur" and self.estado_actual == "verde"

    def luz_verde_este_oeste(self) -> bool:
        return self.fase_actual == "este_oeste" and self.estado_actual == "verde"

    def luz_amarillo_norte_sur(self) -> bool:
        return self.fase_actual == "norte_sur" and self.estado_actual == "amarillo"

    def luz_amarillo_este_oeste(self) -> bool:
        return self.fase_actual == "este_oeste" and self.estado_actual == "amarillo"

    def puede_pasar(self, direccion: str) -> bool:
        """Solo permite pasar con luz VERDE (no amarillo, no rojo)."""
        if direccion in ("norte", "sur"):
            return self.luz_verde_norte_sur()
        if direccion in ("este", "oeste"):
            return self.luz_verde_este_oeste()
        return False

    def esta_amarillo_para(self, direccion: str) -> bool:
        if direccion in ("norte", "sur"):
            return self.luz_amarillo_norte_sur()
        if direccion in ("este", "oeste"):
            return self.luz_amarillo_este_oeste()
        return False

    def esta_rojo_para(self, direccion: str) -> bool:
        """Rojo cuando no es verde ni amarillo."""
        return not self.puede_pasar(direccion) and not self.esta_amarillo_para(direccion)
