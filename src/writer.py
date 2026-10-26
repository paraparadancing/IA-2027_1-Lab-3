import csv
from agents import AgenteLogicoDPLL
from connections import ClienteWumpusAPI
import signal

class TimeoutException(Exception):
    ...

def timeout_handler(signum, frame):
    raise TimeoutException("El agente tardo demasiado en completar el juego.")

def get_results(times: int, api: ClienteWumpusAPI, agente: AgenteLogicoDPLL, initial_perception: dict[str, bool|int|str]) -> None:
    with open('results.csv', 'a', newline='\n') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(("Trial", "Score", "Game Over", "Wumpus Alive"))
        last_score: int
        reason: str
        current_perception = initial_perception
        while times > 0:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)

            print(f"Juego iniciado. ID: {api.game_id}")
            try:
                while not current_perception["gameOver"]:
                    action = agente.procesar_percepcion_y_decidir(current_perception)
                    current_perception = api.enviar_accion(action)
            except TimeoutException:
                print("Timeout forzado por el cliente.")
                current_perception = restart_game(api, agente)
                continue
            except TypeError:
                print(f"Failed to reach server from {api.game_id}")
                current_perception = restart_game(api, agente)
                continue
            finally:
                signal.alarm(0)

            last_score = current_perception["score"]
            if "died" in current_perception["message"].lower():
                reason = "died"
            elif "empty" in current_perception["message"].lower():
                reason = "empty"
            else:
                reason = "gold"
            csv_writer.writerow((times + 1, last_score, reason, agente.wumpus_vivo))
            current_perception = restart_game(api, agente)
            times -= 1

def restart_game(api: ClienteWumpusAPI, agente: AgenteLogicoDPLL) -> dict[str, bool | int | str]:
    current_perception = api.iniciar_juego()
    agente.restart()

    return current_perception
