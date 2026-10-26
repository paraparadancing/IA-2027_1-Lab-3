import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QGraphicsView, QGraphicsScene)
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtCore import Qt

class InterfazWumpus(QWidget):
    def __init__(self, api, agente, percepcion_inicial):
        # Asegurar que exista una instancia de QApplication antes de crear widgets
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
            
        super().__init__()
        
        self.api = api
        self.agente = agente
        self.percepcion_actual = percepcion_inicial
        self.juego_terminado = False
        
        self.setWindowTitle("Cliente Lógico Wumpus World")
        self.resize(600, 500)
        
        # Layout principal equivalente al uso de .pack()
        layout = QVBoxLayout(self)
        
        # Etiqueta de Memoria
        label = QLabel("Memoria del Agente (Grid Virtual)")
        label.setFont(QFont("Arial", 12, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Escena y vista (Equivalente al Canvas)
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 300, 300)
        
        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(302, 302)
        self.view.setStyleSheet("background-color: white;")
        layout.addWidget(self.view, alignment=Qt.AlignCenter)
        
        # Área de log de texto
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(120)
        layout.addWidget(self.log_text)
        
        # Botón de Siguiente Turno
        self.btn_siguiente = QPushButton("Siguiente Turno")
        self.btn_siguiente.setStyleSheet("background-color: rgb(44, 222, 133);")
        layout.addWidget(self.btn_siguiente)
        self.btn_siguiente.clicked.connect(self.ejecutar_turno)

        # Botón de turno automático
        self.btn_auto = QPushButton("Modo automático")
        self.btn_auto.setStyleSheet("background-color: rgb(44, 222, 133);")
        layout.addWidget(self.btn_auto)
        self.btn_siguiente.clicked.connect(self.auto)

        # Botón de nueva partida
        self.btn_nueva_partida = QPushButton("Nueva Partida")
        self.btn_nueva_partida.setStyleSheet("background-color: rgb(44, 222, 133);")
        layout.addWidget(self.btn_nueva_partida)
        self.btn_nueva_partida.clicked.connect(self.limpia_tablero)
        self.btn_nueva_partida.setEnabled(False)

        self.log(f"Juego iniciado. Percepción: {self.percepcion_actual}")
        self.dibujar_estado()

    def log(self, mensaje):
        # QTextEdit.append() añade el texto y hace scroll automáticamente
        self.log_text.append(mensaje)

    def dibujar_estado(self):
        self.scene.clear()
        
        cell_size = 50
        offset = 150 # Centro del canvas para acomodar coordenadas relativas
        
        pen = QPen(QColor("black"))
        brush_visited = QBrush(QColor("lightgreen"))
        brush_agent = QBrush(QColor("blue"))
        
        # Dibujar casillas visitadas
        for x, y in self.agente.visitados:
            cx = offset + x * cell_size
            cy = offset - y * cell_size # Y invertido para el canvas
            # addRect toma (x, y, ancho, alto)
            self.scene.addRect(cx, cy, cell_size, cell_size, pen, brush_visited)
            
        # Dibujar agente
        ax = offset + self.agente.x * cell_size
        ay = offset - self.agente.y * cell_size
        
        # addEllipse toma (x, y, ancho, alto)
        self.scene.addEllipse(ax+10, ay+10, 30, 30, pen, brush_agent)
        
        # Dibujar orientación del agente
        orientacion = self.agente.ORIENTACIONES[self.agente.orientacion_idx]
        text_item = self.scene.addText(orientacion[0], QFont("Arial", 10, QFont.Bold))
        text_item.setDefaultTextColor(QColor("white"))
        text_item.setPos(ax + 17, ay + 14) # Posicionamiento ajustado manualmente al centro

    def auto(self) -> None:
        self.btn_auto.setEnabled(False)
        self.btn_nueva_partida.setEnabled(False)
        self.btn_siguiente.setEnabled(False)
        while not self.juego_terminado:
            print("working...!")
            self.ejecutar_turno()

    def ejecutar_turno(self):
        if self.juego_terminado:
            self.log("El juego ya terminó.")
            return

        self.btn_siguiente.setEnabled(False)
        self.btn_auto.setEnabled(False)

        # 1. El agente decide su acción basado en la percepción
        accion = self.agente.procesar_percepcion_y_decidir(self.percepcion_actual)
        self.log(f"\n> Agente decide: {accion}")

        # 2. Enviar la acción al servidor
        self.log("Enviando al servidor...")
        nueva_percepcion = self.api.enviar_accion(accion)
        
        if nueva_percepcion:
            self.percepcion_actual = nueva_percepcion
            self.log(f"Recibido: {nueva_percepcion}")
            self.dibujar_estado()
            
            if nueva_percepcion.get("gameOver"):
                self.log("¡JUEGO TERMINADO!")
                self.juego_terminado = True
                self.btn_nueva_partida.setEnabled(True)
        else:
            self.log("Error de comunicación con el servidor.")

        if not self.juego_terminado:
            self.btn_siguiente.setEnabled(True)
            self.btn_auto.setEnabled(True)

    def limpia_tablero(self) -> None:
        self.scene.clear()
        self.juego_terminado = False
        self.btn_auto.setEnabled(True)
        self.btn_siguiente.setEnabled(True)
        self.btn_nueva_partida.setEnabled(False)

    def iniciar(self):
        self.show()
        # Iniciar el bucle de eventos principal (equivalente a mainloop)
        self.app.exec() 