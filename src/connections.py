import requests

def timeout_handler(signum, frame):
    raise requests.Timeout("El servidor tardó demasiado en responder.")

class ClienteWumpusAPI:
    """Maneja la comunicación HTTP con el servidor del Wumpus World."""
    def __init__(self, base_url):
        self.BASE_URL = base_url
        self.game_id = None

    def iniciar_juego(self) -> dict[str, bool|int|str]:
        """Llama a /game/new e inicia la partida. Retorna la percepción inicial."""

        url = f"{self.BASE_URL}/game/new"

        try:
            respuesta = requests.post(url, timeout=(1, 2))
            respuesta.raise_for_status()
            datos = respuesta.json()
            self.game_id = datos.get("gameId")
            return datos.get("perception")
        except requests.exceptions.ConnectTimeout:
            print("No se pudo conectar al servidor en el tiempo límite.")
            return None
        except requests.exceptions.ReadTimeout:
            print("El servidor se conectó, pero tardó demasiado en responder.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión al iniciar juego: {e}")
            return None

    def enviar_accion(self, accion):
        """Llama a /game/{gameId}/action con el JSON de la acción."""

        if not self.game_id:
            print("Error: No hay un juego iniciado.")
            return None
            
        url = f"{self.BASE_URL}/game/{self.game_id}/action"
        payload = {"action": accion}

        try:
            respuesta = requests.post(url, json=payload, timeout=(1, 2))
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.exceptions.ConnectTimeout:
            print("No se pudo conectar al servidor en el tiempo límite.")
            return None
        except requests.exceptions.ReadTimeout:
            print("El servidor se conectó, pero tardó demasiado en responder.")
            return None            
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar acción '{accion}': {e}")
            return None

