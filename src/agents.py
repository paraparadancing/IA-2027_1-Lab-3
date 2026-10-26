
from collections import deque


class MotorDPLL:
    @staticmethod
    def simplificar_clausulas(clausulas, literal):
        negado = (
            literal[1:]
            if literal.startswith("-")
            else "-" + literal
        )

        resultado = []

        for clausula in clausulas:
            if literal in clausula:
                continue

            nueva = [
                x for x in clausula
                if x != negado
            ]

            if not nueva:
                return "UNSAT"

            resultado.append(nueva)

        return resultado

    @classmethod
    def dpll(cls, clausulas):
        if clausulas == "UNSAT":
            return False

        if any(not c for c in clausulas):
            return False

        if not clausulas:
            return True

        for clausula in clausulas:
            if len(clausula) == 1:
                simplificadas = cls.simplificar_clausulas(
                    clausulas, clausula[0]
                )
                return cls.dpll(simplificadas)

        literal = clausulas[0][0]

        negado = (
            literal[1:]
            if literal.startswith("-")
            else "-" + literal
        )

        return (
            cls.dpll(
                cls.simplificar_clausulas(
                    clausulas, literal
                )
            )
            or
            cls.dpll(
                cls.simplificar_clausulas(
                    clausulas, negado
                )
            )
        )


class AgenteLogicoDPLL:
    TAM = 4

    ORIENTACIONES = [
        "East", "North", "West", "South"
    ]

    VECTORES = {
        "East": (1, 0),
        "North": (0, 1),
        "West": (-1, 0),
        "South": (0, -1),
    }

    def __init__(self):
        self.restart()

    def restart(self):
        self.x = 0
        self.y = 0
        self.orientacion_idx = 0

        self.tiene_oro = False
        self.tiene_flecha = True
        self.wumpus_vivo = True

        self.ultima_accion = None
        self.ultimo_origen = (0, 0)

        self.clausulas = []
        self.casillas_seguras = {(0, 0)}
        self.visitados = set()
        self.ruta_pendiente = []

        self.paredes_detectadas = set()
        self.casillas_riesgo_intentadas = set()

    # ======================================
    # MAPA
    # ======================================

    def dentro_tablero(self, x, y):
        return (
            0 <= x < self.TAM
            and 0 <= y < self.TAM
        )

    def vecinos(self, x, y):
        posibles = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        return [
            (nx, ny)
            for nx, ny in posibles
            if self.dentro_tablero(nx, ny)
            and (nx, ny) not in self.paredes_detectadas
        ]

    # ======================================
    # PERCEPCIONES
    # ======================================

    def procesar_percepcion_y_decidir(self, percepcion):
        if not isinstance(percepcion, dict):
            percepcion = {}

        # Corregir movimiento anterior
        if (
            percepcion.get("bump", False)
            and self.ultima_accion == "Forward"
        ):
            destino_fallido = (self.x, self.y)

            self.x, self.y = self.ultimo_origen

            if self.dentro_tablero(*destino_fallido):
                self.paredes_detectadas.add(
                    destino_fallido
                )

            self.ruta_pendiente.clear()

        # Proteccion adicional
        if not self.dentro_tablero(self.x, self.y):
            self.x, self.y = self.ultimo_origen
            self.ruta_pendiente.clear()

        if percepcion.get("scream", False):
            self.wumpus_vivo = False

        breeze = bool(
            percepcion.get("breeze", False)
        )

        stench = (
            bool(percepcion.get("stench", False))
            if self.wumpus_vivo
            else False
        )

        glitter = bool(
            percepcion.get("glitter", False)
        )

        self._agregar_percepcion_a_kb(
            self.x, self.y, breeze, stench
        )

        self.visitados.add((self.x, self.y))

        accion = self._decidir(glitter)

        self.ultima_accion = accion
        self._actualizar_estado_interno(accion)

        return accion

    # ======================================
    # DECISIONES
    # ======================================

    def _decidir(self, glitter):
        # 1. Recoger oro
        if glitter and not self.tiene_oro:
            self.tiene_oro = True
            self.ruta_pendiente.clear()
            return "Grab"

        # 2. Volver a la salida con oro
        if self.tiene_oro:
            if (self.x, self.y) == (0, 0):
                return "Climb"

            if not self.ruta_pendiente:
                ruta = self._calcular_ruta_bfs(0, 0)
                self.ruta_pendiente = (
                    self._traducir_ruta_a_acciones(ruta)
                )

            if self.ruta_pendiente:
                return self.ruta_pendiente.pop(0)

            # Si no encuentra ruta, evita un giro infinito.
            return self._accion_hacia_origen()

        # 3. Ejecutar ruta planeada
        if self.ruta_pendiente:
            return self.ruta_pendiente.pop(0)

        # 4. Buscar casillas seguras con DPLL
        destino = (
            self._buscar_casilla_segura_no_visitada()
        )

        if destino is not None:
            ruta = self._calcular_ruta_bfs(
                destino[0], destino[1]
            )

            self.ruta_pendiente = (
                self._traducir_ruta_a_acciones(ruta)
            )

            if self.ruta_pendiente:
                return self.ruta_pendiente.pop(0)

        # 5. Disparar una sola vez si no hay
        # rutas seguras disponibles
        if self.tiene_flecha:
            self.tiene_flecha = False
            return "Shoot"

        # 6. Explorar una frontera de riesgo.
        # No se considera segura: es una decision
        # deliberada para continuar explorando.
        destino_riesgoso = (
            self._buscar_frontera_riesgosa()
        )

        if destino_riesgoso is not None:
            self.casillas_riesgo_intentadas.add(
                destino_riesgoso
            )

            ruta = self._ruta_hacia_frontera(
                destino_riesgoso
            )

            self.ruta_pendiente = (
                self._traducir_ruta_a_acciones(ruta)
            )

            if self.ruta_pendiente:
                return self.ruta_pendiente.pop(0)

        # 7. Sin fronteras disponibles:
        # regresar al origen en lugar de girar
        # indefinidamente.
        return self._accion_hacia_origen()

    def _accion_hacia_origen(self):
        if (self.x, self.y) == (0, 0):
            return "Climb"

        ruta = self._calcular_ruta_bfs(0, 0)

        self.ruta_pendiente = (
            self._traducir_ruta_a_acciones(ruta)
        )

        if self.ruta_pendiente:
            return self.ruta_pendiente.pop(0)

        # No existe camino conocido.
        # Se evita generar movimientos falsos.
        return "Climb"

    # ======================================
    # BASE DE CONOCIMIENTO
    # ======================================

    def _agregar_percepcion_a_kb(
        self, x, y, breeze, stench
    ):
        if not self.dentro_tablero(x, y):
            return

        self.clausulas.append([f"-P{x}_{y}"])
        self.clausulas.append([f"-W{x}_{y}"])

        self.casillas_seguras.add((x, y))

        adyacentes = self.vecinos(x, y)

        if not breeze:
            for nx, ny in adyacentes:
                self.clausulas.append(
                    [f"-P{nx}_{ny}"]
                )
        elif adyacentes:
            self.clausulas.append([
                f"P{nx}_{ny}"
                for nx, ny in adyacentes
            ])

        if not stench:
            for nx, ny in adyacentes:
                self.clausulas.append(
                    [f"-W{nx}_{ny}"]
                )
        elif adyacentes:
            self.clausulas.append([
                f"W{nx}_{ny}"
                for nx, ny in adyacentes
            ])

    def _es_casilla_segura(self, x, y):
        if not self.dentro_tablero(x, y):
            return False

        if (x, y) in self.paredes_detectadas:
            return False

        if (x, y) in self.casillas_seguras:
            return True

        pozo_posible = MotorDPLL.dpll(
            self.clausulas + [[f"P{x}_{y}"]]
        )

        wumpus_posible = (
            self.wumpus_vivo
            and MotorDPLL.dpll(
                self.clausulas + [[f"W{x}_{y}"]]
            )
        )

        if not pozo_posible and not wumpus_posible:
            self.casillas_seguras.add((x, y))
            return True

        return False

    def _buscar_casilla_segura_no_visitada(self):
        candidatas = set()

        for vx, vy in self.visitados:
            for vecino in self.vecinos(vx, vy):
                if vecino not in self.visitados:
                    candidatas.add(vecino)

        # Orden estable y cercano
        ordenadas = sorted(
            candidatas,
            key=lambda p: (
                abs(p[0] - self.x)
                + abs(p[1] - self.y),
                p[1],
                p[0],
            )
        )

        for cx, cy in ordenadas:
            if not self._es_casilla_segura(cx, cy):
                continue

            ruta = self._calcular_ruta_bfs(cx, cy)

            if ruta:
                return (cx, cy)

        return None

    # ======================================
    # EXPLORACION DE RIESGO
    # ======================================

    def _buscar_frontera_riesgosa(self):
        candidatas = set()

        for vx, vy in self.visitados:
            for vecino in self.vecinos(vx, vy):
                if vecino in self.visitados:
                    continue

                if vecino in self.casillas_riesgo_intentadas:
                    continue

                candidatas.add(vecino)

        ordenadas = sorted(
            candidatas,
            key=lambda p: (
                abs(p[0] - self.x)
                + abs(p[1] - self.y),
                p[1],
                p[0],
            )
        )

        for destino in ordenadas:
            if self._ruta_hacia_frontera(destino):
                return destino

        return None

    def _ruta_hacia_frontera(self, destino):
        # Se permite que la ultima casilla sea
        # desconocida, pero el resto del camino
        # debe recorrer casillas conocidas.
        for vecino in self.vecinos(*destino):
            if vecino not in self.visitados:
                continue

            ruta = self._calcular_ruta_bfs(
                vecino[0], vecino[1]
            )

            if (
                vecino == (self.x, self.y)
                or ruta
            ):
                return ruta + [destino]

        return []

    # ======================================
    # BUSQUEDA DE RUTAS
    # ======================================

    def _calcular_ruta_bfs(self, dest_x, dest_y):
        if not self.dentro_tablero(dest_x, dest_y):
            return []

        inicio = (self.x, self.y)
        destino = (dest_x, dest_y)

        if inicio == destino:
            return []

        cola = deque([(inicio, [])])
        exploradas = {inicio}

        while cola:
            (cx, cy), camino = cola.popleft()

            for nx, ny in self.vecinos(cx, cy):
                siguiente = (nx, ny)

                if siguiente in exploradas:
                    continue

                if siguiente not in self.casillas_seguras:
                    continue

                nuevo_camino = camino + [siguiente]

                if siguiente == destino:
                    return nuevo_camino

                exploradas.add(siguiente)
                cola.append(
                    (siguiente, nuevo_camino)
                )

        return []

    def _traducir_ruta_a_acciones(
        self, ruta_coordenadas
    ):
        acciones = []

        temp_x, temp_y = self.x, self.y
        temp_ori = self.orientacion_idx

        for nx, ny in ruta_coordenadas:
            if not self.dentro_tablero(nx, ny):
                return []

            dx = nx - temp_x
            dy = ny - temp_y

            if abs(dx) + abs(dy) != 1:
                return []

            direccion = None

            for nombre, vector in self.VECTORES.items():
                if vector == (dx, dy):
                    direccion = nombre
                    break

            if direccion is None:
                return []

            objetivo = self.ORIENTACIONES.index(
                direccion
            )

            diferencia = (objetivo - temp_ori) % 4

            if diferencia == 1:
                acciones.append("TurnLeft")
            elif diferencia == 2:
                acciones.extend([
                    "TurnLeft", "TurnLeft"
                ])
            elif diferencia == 3:
                acciones.append("TurnRight")

            acciones.append("Forward")

            temp_x, temp_y = nx, ny
            temp_ori = objetivo

        return acciones

    # ======================================
    # ODOMETRIA
    # ======================================

    def _actualizar_estado_interno(self, accion):
        if accion == "TurnLeft":
            self.orientacion_idx = (
                self.orientacion_idx + 1
            ) % 4

        elif accion == "TurnRight":
            self.orientacion_idx = (
                self.orientacion_idx - 1
            ) % 4

        elif accion == "Forward":
            dx, dy = self.VECTORES[
                self.ORIENTACIONES[
                    self.orientacion_idx
                ]
            ]

            nx = self.x + dx
            ny = self.y + dy

            self.ultimo_origen = (self.x, self.y)

            if self.dentro_tablero(nx, ny):
                self.x = nx
                self.y = ny
            else:
                # No permitir odometria fuera
                # de los limites del tablero.
                self.ruta_pendiente.clear()
