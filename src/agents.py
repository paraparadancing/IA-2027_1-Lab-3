from collections import deque

class MotorDPLL:
    @staticmethod
    def simplificar_clausulas(clausulas, literal_asignado):
        nuevas_clausulas = []
        literal_negado = literal_asignado[1:] if literal_asignado.startswith('-') else '-' + literal_asignado
        
        for clausula in clausulas:
            if literal_asignado in clausula:
                continue
            if literal_negado in clausula:
                nueva_clausula = [l for l in clausula if l != literal_negado]
                if not nueva_clausula:
                    return "UNSAT"
                nuevas_clausulas.append(nueva_clausula)
            else:
                nuevas_clausulas.append(clausula)
        return nuevas_clausulas

    @classmethod
    def dpll(cls, clausulas):
        if clausulas == "UNSAT" or any(not c for c in clausulas):
            return False
        if not clausulas:
            return True

        for clausula in clausulas:
            if len(clausula) == 1:
                return cls.dpll(cls.simplificar_clausulas(clausulas, clausula[0]))

        literal = clausulas[0][0]
        literal_negado = literal[1:] if literal.startswith('-') else '-' + literal
        
        if cls.dpll(cls.simplificar_clausulas(clausulas, literal)): 
            return True
        return cls.dpll(cls.simplificar_clausulas(clausulas, literal_negado))


class AgenteLogicoDPLL:
    """Encapsula la Base de Conocimiento, la Odometría y la toma de decisiones."""
    ORIENTACIONES = ["East", "North", "West", "South"]
    VECTORES = {"East": (1, 0), "North": (0, 1), "West": (-1, 0), "South": (0, -1)}

    def __init__(self):
        # Odometría y estado físico
        self.x = 0
        self.y = 0
        self.orientacion_idx = 0  # Inicia mirando al Este
        
        # Inventario y estado de juego
        self.tiene_oro = False
        self.tiene_flecha = True
        self.wumpus_vivo = True
        self.ultima_accion = None
        
        # Memoria del entorno
        self.clausulas = []
        self.casillas_seguras = set()
        self.visitados = set()
        self.ruta_pendiente = [] # Cola de comandos a ejecutar

    
    def restart(self):
        self.x = 0
        self.y = 0
        self.orientacion_idx = 0
        
        self.tiene_oro = False
        self.tiene_flecha = True
        self.wumpus_vivo = True
        self.ultima_accion = None
        
        self.clausulas.clear()
        self.casillas_seguras.clear()
        self.visitados.clear()
        self.ruta_pendiente.clear()

    def procesar_percepcion_y_decidir(self, percepcion):
        """Recibe la percepción, corrige odometría, actualiza KB y decide la acción."""
        
        # 1. Corregir odometría si el último movimiento chocó con la pared
        if percepcion.get('bump') and self.ultima_accion == "Forward":
            dx, dy = self.VECTORES[self.ORIENTACIONES[self.orientacion_idx]]
            self.x -= dx
            self.y -= dy
            
        # 2. Actualizar estado por grito de Wumpus
        if percepcion.get('scream'):
            self.wumpus_vivo = False

        # 3. Extraer percepciones
        breeze = percepcion.get('breeze', False)
        stench = percepcion.get('stench', False) if self.wumpus_vivo else False
        glitter = percepcion.get('glitter', False)

        # 4. Alimentar Base de Conocimiento
        self._agregar_percepcion_a_kb(self.x, self.y, breeze, stench)
        self.visitados.add((self.x, self.y))

        # 5. Jerarquía de toma de decisiones
        accion = self._decidir(glitter)
        
        # 6. Actualizar estado interno y guardar memoria de acción
        self.ultima_accion = accion
        self._actualizar_estado_interno(accion)
        return accion

    def _decidir(self, glitter):
        # Prioridad 1: Tomar el oro si brilla y aún no lo tenemos
        if glitter and not self.tiene_oro:
            self.tiene_oro = True
            self.ruta_pendiente = [] # Cancelamos exploraciones, es hora de huir
            return "Grab"
            
        # Prioridad 2: Si tenemos el oro y estamos en (0,0), salimos de la cueva
        if self.tiene_oro and self.x == 0 and self.y == 0:
            return "Climb"
            
        # Prioridad 3: Si tenemos el oro, trazar ruta a (0,0) y ejecutarla
        if self.tiene_oro and not self.ruta_pendiente:
            ruta_coords = self._calcular_ruta_bfs(0, 0)
            self.ruta_pendiente = self._traducir_ruta_a_acciones(ruta_coords)
            
        # Ejecutar pasos pendientes de cualquier ruta trazada previamente
        if self.ruta_pendiente:
            return self.ruta_pendiente.pop(0)

        # Prioridad 4: Explorar casilla segura más cercana
        destino = self._buscar_casilla_segura_no_visitada()
        if destino:
            ruta_coords = self._calcular_ruta_bfs(destino[0], destino[1])
            self.ruta_pendiente = self._traducir_ruta_a_acciones(ruta_coords)
            if self.ruta_pendiente:
                return self.ruta_pendiente.pop(0)

        # Prioridad 5: Si no hay casillas seguras, estamos rodeados de peligro.
        # Desesperación: disparar la flecha si tenemos una
        if self.tiene_flecha:
            self.tiene_flecha = False
            return "Shoot"

        # Prioridad 6: Si no hay opciones seguras y no tenemos flecha, RINDETE Y HUYE a (0,0)
        if self.x == 0 and self.y == 0:
            return "Climb" # Salir vivo sin oro es mejor que morir
            
        ruta_coords = self._calcular_ruta_bfs(0, 0)
        self.ruta_pendiente = self._traducir_ruta_a_acciones(ruta_coords)
        if self.ruta_pendiente:
            return self.ruta_pendiente.pop(0)
            
        # Fallback (no debería llegar aquí a menos que empiece encerrado)
        return "TurnLeft" 

    def _agregar_percepcion_a_kb(self, x, y, breeze, stench):
        self.clausulas.append([f"-P{x}_{y}"])
        self.clausulas.append([f"-W{x}_{y}"])
        self.casillas_seguras.add((x, y))

        adyacentes = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        adyacentes = [(nx, ny) for nx, ny in adyacentes if nx >= 0 and ny >= 0]

        if not breeze:
            for nx, ny in adyacentes:
                self.clausulas.append([f"-P{nx}_{ny}"])
        else:
            self.clausulas.append([f"P{nx}_{ny}" for nx, ny in adyacentes])

        if not stench:
            for nx, ny in adyacentes:
                self.clausulas.append([f"-W{nx}_{ny}"])
        else:
            self.clausulas.append([f"W{nx}_{ny}" for nx, ny in adyacentes])

    def _es_casilla_segura(self, x, y):
        if (x, y) in self.casillas_seguras:
            return True
            
        hipotesis_pozo = self.clausulas + [[f"P{x}_{y}"]]
        pozo_posible = MotorDPLL.dpll(hipotesis_pozo)

        hipotesis_wumpus = self.clausulas + [[f"W{x}_{y}"]]
        wumpus_posible = MotorDPLL.dpll(hipotesis_wumpus)

        if not pozo_posible and not wumpus_posible:
            self.casillas_seguras.add((x, y))
            return True
        return False

    def _buscar_casilla_segura_no_visitada(self):
        candidatas = set()
        for vx, vy in self.visitados:
            for nx, ny in [(vx+1, vy), (vx-1, vy), (vx, vy+1), (vx, vy-1)]:
                if nx >= 0 and ny >= 0 and (nx, ny) not in self.visitados:
                    candidatas.add((nx, ny))
                    
        for cx, cy in candidatas:
            if self._es_casilla_segura(cx, cy):
                return (cx, cy)
        return None

    def _calcular_ruta_bfs(self, dest_x, dest_y):
        cola = deque([((self.x, self.y), [])])
        visitados_bfs = set([(self.x, self.y)])

        while cola:
            (cx, cy), camino = cola.popleft()
            if cx == dest_x and cy == dest_y:
                return camino

            for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                if (nx, ny) in self.casillas_seguras and (nx, ny) not in visitados_bfs:
                    visitados_bfs.add((nx, ny))
                    cola.append(((nx, ny), camino + [(nx, ny)]))
        return []

    def _traducir_ruta_a_acciones(self, ruta_coordenadas):
        acciones = []
        temp_x, temp_y = self.x, self.y
        temp_ori = self.orientacion_idx

        for nx, ny in ruta_coordenadas:
            dx, dy = nx - temp_x, ny - temp_y
            target_ori_name = [k for k, v in self.VECTORES.items() if v == (dx, dy)][0]
            target_ori = self.ORIENTACIONES.index(target_ori_name)

            diff = (target_ori - temp_ori) % 4
            if diff == 1:
                acciones.append("TurnLeft")
            elif diff == 2:
                acciones.extend(["TurnLeft", "TurnLeft"])
            elif diff == 3:
                acciones.append("TurnRight")
            
            acciones.append("Forward")
            temp_x, temp_y = nx, ny
            temp_ori = target_ori

        return acciones

    def _actualizar_estado_interno(self, accion):
        if accion == "TurnLeft":
            self.orientacion_idx = (self.orientacion_idx + 1) % 4
        elif accion == "TurnRight":
            self.orientacion_idx = (self.orientacion_idx - 1) % 4
        elif accion == "Forward":
            dx, dy = self.VECTORES[self.ORIENTACIONES[self.orientacion_idx]]
            self.x += dx
            self.y += dy