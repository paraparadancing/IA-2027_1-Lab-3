
import sys
import math

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QColor, QBrush, QPen, QFont,
    QPolygonF, QPainterPath, QPainter
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGraphicsScene,
    QGraphicsView, QFrame
)


class InterfazWumpus(QWidget):
    TAM = 4
    CELDA = 88

    def __init__(self, api, agente, percepcion_inicial):
        self.app = QApplication.instance() or QApplication(sys.argv)
        super().__init__()

        self.api = api
        self.agente = agente
        self.percepcion_actual = percepcion_inicial or {}

        self.numero_partida = 1
        self.juego_terminado = False
        self.modo_automatico = False
        self.ultima_accion = "Waiting"
        self.score = 0

        # Memoria exclusiva de la interfaz
        self.historial = {}
        self.gold_descubierto = None
        self.pits_confirmados = set()
        self.wumpus_confirmados = set()
        self.wumpus_eliminado = False

        # Posicion visual separada de la odometria del agente.
        # Esto permite mostrar correctamente un Bump.
        self.posicion_visual = (0, 0)

        self.registrar_percepcion((0, 0))

        self.setWindowTitle("Wumpus World - DPLL Agent")
        self.resize(620, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #22252b;
                color: #f3f4f6;
                font-family: Arial;
            }

            QLabel#titulo {
                font-size: 23px;
                font-weight: bold;
                color: #ffffff;
            }

            QLabel#subtitulo {
                color: #b8c3d2;
                font-size: 13px;
            }

            QPushButton {
                background-color: #53dfcb;
                color: #142127;
                border: none;
                border-radius: 7px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px;
            }

            QPushButton:hover {
                background-color: #75f2e1;
            }

            QPushButton:disabled {
                background-color: #56616a;
                color: #bdc3c7;
            }

            QFrame#panel {
                background-color: #303640;
                border-radius: 10px;
            }
        """)

        self.timer = QTimer(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.ejecutar_turno)

        self.timer_reinicio = QTimer(self)
        self.timer_reinicio.setSingleShot(True)
        self.timer_reinicio.setInterval(1700)
        self.timer_reinicio.timeout.connect(
            self.reiniciar_automaticamente
        )

        principal = QVBoxLayout(self)
        principal.setContentsMargins(16, 15, 16, 15)
        principal.setSpacing(12)

        titulo = QLabel("WUMPUS WORLD")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        principal.addWidget(titulo)

        subtitulo = QLabel("DPLL Logical Agent | Exploration Mode")
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignCenter)
        principal.addWidget(subtitulo)

        self.info = QLabel("Game 1 | Position (0, 0) | East")
        self.info.setAlignment(Qt.AlignCenter)
        principal.addWidget(self.info)

        contenido = QHBoxLayout()
        contenido.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(145)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(9)

        estado = QLabel("PERCEPTIONS")
        estado.setAlignment(Qt.AlignCenter)
        estado.setStyleSheet("font-weight: bold;")
        panel_layout.addWidget(estado)

        self.indicadores = {}

        for clave, nombre in [
            ("breeze", "Breeze"),
            ("stench", "Stench"),
            ("glitter", "Glitter"),
            ("bump", "Bump"),
        ]:
            etiqueta = QLabel(nombre)
            etiqueta.setAlignment(Qt.AlignCenter)
            etiqueta.setFixedHeight(37)

            self.indicadores[clave] = etiqueta
            panel_layout.addWidget(etiqueta)

        panel_layout.addStretch()

        score_titulo = QLabel("SCORE")
        score_titulo.setAlignment(Qt.AlignCenter)
        score_titulo.setStyleSheet("font-weight: bold;")
        panel_layout.addWidget(score_titulo)

        self.score_label = QLabel("0")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("""
            background-color: #f5f7fa;
            color: #15232d;
            font-size: 23px;
            font-weight: bold;
            border-radius: 6px;
            padding: 10px;
        """)
        panel_layout.addWidget(self.score_label)

        contenido.addWidget(panel)

        lado = self.TAM * self.CELDA

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, lado, lado)

        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(lado + 4, lado + 4)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.view.setStyleSheet(
            "background: white; border: none;"
        )

        contenido.addWidget(self.view)
        principal.addLayout(contenido)

        leyenda = QLabel(
            "Green: Visited   |   Blue: Safe   |   White: Unknown"
        )
        leyenda.setAlignment(Qt.AlignCenter)
        leyenda.setWordWrap(True)
        leyenda.setStyleSheet("color: #b8c3d2;")
        principal.addWidget(leyenda)

        self.accion_label = QLabel("Last action: Waiting")
        self.accion_label.setAlignment(Qt.AlignCenter)
        self.accion_label.setMinimumHeight(48)
        self.accion_label.setStyleSheet("""
            background-color: #f5f7fa;
            color: #15232d;
            font-size: 16px;
            font-weight: bold;
            border-radius: 7px;
            padding: 10px;
        """)
        principal.addWidget(self.accion_label)

        self.btn_siguiente = QPushButton("Next step")
        self.btn_auto = QPushButton("Auto mode")
        self.btn_nueva = QPushButton("New game")

        principal.addWidget(self.btn_siguiente)
        principal.addWidget(self.btn_auto)
        principal.addWidget(self.btn_nueva)

        self.btn_siguiente.clicked.connect(self.ejecutar_turno)
        self.btn_auto.clicked.connect(self.alternar_auto)
        self.btn_nueva.clicked.connect(self.nueva_partida_manual)

        self.actualizar_interfaz()

    # =========================================
    # PERCEPTIONS
    # =========================================

    def obtener_percepcion(self):
        datos = self.percepcion_actual

        if not isinstance(datos, dict):
            return {}

        percepcion = datos.get("perception")

        if isinstance(percepcion, dict):
            return {**datos, **percepcion}

        return datos

    def dentro_tablero(self, x, y):
        return 0 <= x < self.TAM and 0 <= y < self.TAM

    def vecinos(self, x, y):
        candidatos = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        return [
            p for p in candidatos
            if self.dentro_tablero(*p)
        ]

    def registrar_percepcion(self, posicion):
        if not self.dentro_tablero(*posicion):
            return

        p = self.obtener_percepcion()

        # Guardamos los datos observados, sin
        # modificar la base de conocimiento DPLL.
        self.historial[posicion] = {
            "breeze": bool(p.get("breeze", False)),
            "stench": bool(p.get("stench", False)),
            "glitter": bool(p.get("glitter", False)),
        }

        if p.get("glitter", False):
            self.gold_descubierto = posicion

    # =========================================
    # VISUAL INFERENCE
    # =========================================

    def actualizar_peligros(self):
        self.pits_confirmados.clear()
        self.wumpus_confirmados.clear()

        visitados = set(self.historial)

        sin_pit = set(visitados)
        sin_wumpus = set(visitados)

        for (x, y), datos in self.historial.items():
            vecinos = self.vecinos(x, y)

            if not datos["breeze"]:
                sin_pit.update(vecinos)

            if not datos["stench"]:
                sin_wumpus.update(vecinos)

        # Deducciones simples a partir de
        # las percepciones ya descubiertas.
        for (x, y), datos in self.historial.items():
            vecinos = set(self.vecinos(x, y))

            if datos["breeze"]:
                candidatos = vecinos - sin_pit

                if len(candidatos) == 1:
                    self.pits_confirmados.update(
                        candidatos
                    )

            if datos["stench"] and not self.wumpus_eliminado:
                candidatos = vecinos - sin_wumpus

                if len(candidatos) == 1:
                    self.wumpus_confirmados.update(
                        candidatos
                    )

        if self.wumpus_eliminado:
            self.wumpus_confirmados.clear()

    # =========================================
    # DRAWING HELPERS
    # =========================================

    def posicion_pantalla(self, x, y):
        return (
            x * self.CELDA,
            (self.TAM - 1 - y) * self.CELDA,
        )

    def centro(self, x, y):
        px, py = self.posicion_pantalla(x, y)

        return (
            px + self.CELDA / 2,
            py + self.CELDA / 2,
        )

    def dibujar_pit(self, x, y):
        cx, cy = self.centro(x, y)

        self.scene.addEllipse(
            cx - 24, cy - 24, 48, 48,
            QPen(QColor("#111111"), 2),
            QBrush(QColor("#090909")),
        )

        self.agregar_texto(
            "PIT", cx - 12, cy - 9,
            "#ffffff", 10, True
        )

    def dibujar_wumpus(self, x, y):
        cx, cy = self.centro(x, y)

        verde = QColor("#50ae61")
        borde = QColor("#20642e")

        # Body
        self.scene.addEllipse(
            cx - 25, cy - 22, 50, 50,
            QPen(borde, 2),
            QBrush(verde),
        )

        # Horns
        for lado in (-1, 1):
            puntos = QPolygonF([
                QPointF(cx + lado * 12, cy - 17),
                QPointF(cx + lado * 25, cy - 36),
                QPointF(cx + lado * 24, cy - 7),
            ])

            self.scene.addPolygon(
                puntos, QPen(borde), QBrush(verde)
            )

        # Eyes
        for desplazamiento in (-11, 11):
            self.scene.addEllipse(
                cx + desplazamiento - 7,
                cy - 10,
                14, 16,
                QPen(QColor("#ffffff")),
                QBrush(QColor("#ffffff")),
            )

            self.scene.addEllipse(
                cx + desplazamiento - 2,
                cy - 4,
                5, 6,
                QPen(QColor("#151515")),
                QBrush(QColor("#151515")),
            )

        # Mouth
        self.scene.addLine(
            cx - 12, cy + 15,
            cx + 12, cy + 15,
            QPen(QColor("#22562d"), 3),
        )

    def dibujar_gold(self, x, y):
        cx, cy = self.centro(x, y)

        oscuro = QColor("#986514")

        # Treasure chest
        self.scene.addRect(
            cx - 25, cy - 5,
            50, 29,
            QPen(oscuro, 2),
            QBrush(QColor("#e9aa24")),
        )

        self.scene.addRect(
            cx - 25, cy - 19,
            50, 17,
            QPen(oscuro, 2),
            QBrush(QColor("#ffda54")),
        )

        self.scene.addRect(
            cx - 5, cy + 3,
            10, 12,
            QPen(oscuro),
            QBrush(QColor("#fff1a3")),
        )

    def dibujar_ondas(self, x, y, tipo):
        px, py = self.posicion_pantalla(x, y)

        if tipo == "breeze":
            color = QColor("#168dd8")
            base_y = py + 13
        else:
            color = QColor("#2c9a45")
            base_y = py + 31

        for fila in range(2):
            path = QPainterPath()

            for i in range(3):
                bx = px + 11 + i * 23
                by = base_y + fila * 8

                path.moveTo(bx, by)
                path.cubicTo(
                    bx + 5, by - 7,
                    bx + 11, by + 7,
                    bx + 18, by,
                )

            self.scene.addPath(
                path, QPen(color, 2)
            )

    def dibujar_glitter(self, x, y):
        cx, cy = self.centro(x, y)

        puntos = []

        for i in range(10):
            angulo = math.pi * i / 5 - math.pi / 2
            radio = 20 if i % 2 == 0 else 8

            puntos.append(
                QPointF(
                    cx + math.cos(angulo) * radio,
                    cy + math.sin(angulo) * radio,
                )
            )

        self.scene.addPolygon(
            QPolygonF(puntos),
            QPen(QColor("#a66b00"), 2),
            QBrush(QColor("#ffdc31")),
        )

    def agregar_texto(
        self, texto, x, y,
        color="#333333", tam=10, negrita=False
    ):
        fuente = QFont("Arial", tam)
        fuente.setBold(negrita)

        item = self.scene.addText(texto, fuente)
        item.setDefaultTextColor(QColor(color))
        item.setPos(x, y)
        return item

    def dibujar_agente(self):
        x, y = self.posicion_visual

        if not self.dentro_tablero(x, y):
            return

        cx, cy = self.centro(x, y)

        orientacion = self.agente.ORIENTACIONES[
            self.agente.orientacion_idx
        ]

        # La pantalla tiene el eje Y invertido.
        vectores = {
            "East": (1, 0),
            "North": (0, -1),
            "West": (-1, 0),
            "South": (0, 1),
        }

        dx, dy = vectores[orientacion]
        lx, ly = -dy, dx

        puntos = QPolygonF([
            QPointF(
                cx + dx * 26,
                cy + dy * 26
            ),
            QPointF(
                cx - dx * 15 + lx * 16,
                cy - dy * 15 + ly * 16
            ),
            QPointF(
                cx - dx * 15 - lx * 16,
                cy - dy * 15 - ly * 16
            ),
        ])

        self.scene.addPolygon(
            puntos,
            QPen(QColor("#1b2384"), 2),
            QBrush(QColor("#3b4ce5")),
        )

    # =========================================
    # BOARD
    # =========================================

    def dibujar_tablero(self):
        self.scene.clear()

        visitados = set(
            getattr(self.agente, "visitados", set())
        )
        visitados.update(self.historial)

        seguros = set(
            getattr(self.agente, "casillas_seguras", set())
        )

        borde = QPen(QColor("#3d4752"), 1.5)

        for y in range(self.TAM):
            for x in range(self.TAM):
                px, py = self.posicion_pantalla(x, y)
                posicion = (x, y)

                if posicion in visitados:
                    fondo = "#c8f0da"
                elif posicion in seguros:
                    fondo = "#e0f1ff"
                else:
                    fondo = "#ffffff"

                self.scene.addRect(
                    px, py,
                    self.CELDA,
                    self.CELDA,
                    borde,
                    QBrush(QColor(fondo)),
                )

                self.agregar_texto(
                    f"{x},{y}",
                    px + 4,
                    py + self.CELDA - 22,
                    "#83919c",
                    8,
                )

        # Known perceptions
        for (x, y), datos in self.historial.items():
            if datos["breeze"]:
                self.dibujar_ondas(x, y, "breeze")

            if datos["stench"]:
                self.dibujar_ondas(x, y, "stench")

        # Confirmed hazards
        for x, y in self.pits_confirmados:
            self.dibujar_pit(x, y)

        for x, y in self.wumpus_confirmados:
            self.dibujar_wumpus(x, y)

        # Discovered treasure
        if (
            self.gold_descubierto is not None
            and not self.agente.tiene_oro
        ):
            self.dibujar_gold(*self.gold_descubierto)

        # Agent always on top
        self.dibujar_agente()

    # =========================================
    # INTERFACE
    # =========================================

    def actualizar_indicadores(self):
        p = self.obtener_percepcion()

        for clave, etiqueta in self.indicadores.items():
            activo = bool(p.get(clave, False))

            if activo:
                color = "#5ae6a0"
            else:
                color = "#e76c73"

            etiqueta.setStyleSheet(
                f"background-color: {color};"
                "color: #142127;"
                "border-radius: 6px;"
                "font-size: 15px;"
                "font-weight: bold;"
            )

        self.score_label.setText(str(self.score))

    def actualizar_interfaz(self):
        self.actualizar_peligros()
        self.actualizar_indicadores()
        self.dibujar_tablero()

        x, y = self.posicion_visual

        orientacion = self.agente.ORIENTACIONES[
            self.agente.orientacion_idx
        ]

        self.info.setText(
            f"Game {self.numero_partida} | "
            f"Position ({x}, {y}) | {orientacion}"
        )

        self.accion_label.setText(
            f"Last action: {self.ultima_accion}"
        )

    # =========================================
    # GAME LOGIC
    # =========================================

    def alternar_auto(self):
        if self.modo_automatico:
            self.detener_auto()
            return

        if self.juego_terminado:
            self.nueva_partida(continuar_auto=True)
            return

        self.modo_automatico = True
        self.btn_auto.setText("Pause auto")
        self.btn_siguiente.setEnabled(False)
        self.timer.start()

    def detener_auto(self):
        self.modo_automatico = False

        self.timer.stop()
        self.timer_reinicio.stop()

        self.btn_auto.setText("Auto mode")
        self.btn_siguiente.setEnabled(
            not self.juego_terminado
        )

    def ejecutar_turno(self):
        if self.juego_terminado:
            return

        self.timer.stop()

        try:
            # The agent receives the actual perception.
            percepcion = self.obtener_percepcion()

            posicion_anterior = (
                self.agente.x,
                self.agente.y
            )

            # ORIGINAL DPLL AGENT.
            # No decision rules are modified.
            accion = (
                self.agente.procesar_percepcion_y_decidir(
                    percepcion
                )
            )

            self.ultima_accion = accion

            # Send the original action to the server.
            respuesta = self.api.enviar_accion(accion)

            if not isinstance(respuesta, dict):
                self.detener_auto()
                self.accion_label.setText(
                    "Connection error"
                )
                return

            # Preserve complete server response.
            self.percepcion_actual = respuesta

            nueva_percepcion = self.obtener_percepcion()

            # Score may be present in the outer response
            # or inside the perception.
            if "score" in nueva_percepcion:
                self.score = nueva_percepcion["score"]

            # Determine the actual visual position.
            if accion == "Forward":
                if nueva_percepcion.get("bump", False):
                    self.posicion_visual = posicion_anterior
                else:
                    self.posicion_visual = (
                        self.agente.x,
                        self.agente.y
                    )
            else:
                self.posicion_visual = (
                    self.agente.x,
                    self.agente.y
                )

            if nueva_percepcion.get("scream", False):
                self.wumpus_eliminado = True

            # Avoid registering a terminal perception
            # as if it were a new visited room.
            terminado = bool(
                nueva_percepcion.get("gameOver", False)
            )

            if not terminado:
                self.registrar_percepcion(
                    self.posicion_visual
                )

            self.actualizar_interfaz()

            if terminado:
                self.juego_terminado = True
                self.btn_siguiente.setEnabled(False)

                self.accion_label.setText(
                    f"Game Over | Last action: {accion}"
                )

                if self.modo_automatico:
                    self.timer_reinicio.start()

                return

            if self.modo_automatico:
                self.timer.start()

        except Exception as error:
            self.detener_auto()

            self.accion_label.setText(
                f"Error: {error}"
            )

            print("Game error:", error)

    # =========================================
    # NEW GAME
    # =========================================

    def reiniciar_automaticamente(self):
        self.nueva_partida(continuar_auto=True)

    def nueva_partida_manual(self):
        self.detener_auto()
        self.nueva_partida(continuar_auto=False)

    def nueva_partida(self, continuar_auto=False):
        self.timer.stop()
        self.timer_reinicio.stop()

        try:
            nueva_percepcion = self.api.iniciar_juego()

            if not isinstance(nueva_percepcion, dict):
                raise ValueError(
                    "The server did not start a new game"
                )

            # Reset original DPLL agent
            self.agente.restart()

            # Reset visual state
            self.historial.clear()
            self.gold_descubierto = None
            self.pits_confirmados.clear()
            self.wumpus_confirmados.clear()

            self.wumpus_eliminado = False
            self.posicion_visual = (0, 0)

            self.percepcion_actual = nueva_percepcion
            self.juego_terminado = False
            self.numero_partida += 1

            self.score = nueva_percepcion.get("score", 0)
            self.ultima_accion = "New game"

            self.registrar_percepcion((0, 0))
            self.actualizar_interfaz()

            if continuar_auto:
                self.modo_automatico = True
                self.btn_auto.setText("Pause auto")
                self.btn_siguiente.setEnabled(False)
                self.timer.start()
            else:
                self.modo_automatico = False
                self.btn_auto.setText("Auto mode")
                self.btn_siguiente.setEnabled(True)

        except Exception as error:
            self.detener_auto()

            self.accion_label.setText(
                f"Restart error: {error}"
            )

            print("Restart error:", error)

    # =========================================
    # APPLICATION
    # =========================================

    def iniciar(self):
        self.show()
        self.app.exec()

    def closeEvent(self, event):
        self.timer.stop()
        self.timer_reinicio.stop()
        event.accept()
