import connections
import agents
import gui
import writer
from sys import argv

def main():
    print("Iniciando cliente Wumpus World...")
    
    # 1. Inicializar conexión al servidor
    BASE_URL = "https://wumpus-world-cipl.onrender.com"
    api = connections.ClienteWumpusAPI(BASE_URL)

    # 2. Iniciar el juego
    percepcion_inicial = api.iniciar_juego()
    if not percepcion_inicial:
        print("No se pudo conectar al servidor. Saliendo...")
        return

    # 3. Inicializar el agente lógico
    agente_logico = agents.AgenteLogicoDPLL()
    
    # Modos de juego
    if len(argv) == 1: #Modo interactivo
        # 4. Inicializar y lanzar la interfaz gráfica (esto bloquea hasta que se cierre la ventana)
        # Le pasamos la API, el agente y la percepción inicial para que controle el bucle de juego
        interfaz = gui.InterfazWumpus(api, agente_logico, percepcion_inicial)
        interfaz.iniciar()
    elif argv[1] == '-h' or argv[1] == "--headless": # Modo headless
        if len(argv) == 3 and argv[2].isnumeric() and int(argv[2]) >= 1:
            times = int(argv[2])
        else:
            times = 1

        writer.get_results(times, api, agente_logico, percepcion_inicial)
    else:
        print("Error de sintaxis.")

if __name__ == "__main__":
    main() 