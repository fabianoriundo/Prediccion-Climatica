import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from requests.exceptions import RequestException, Timeout
import time

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.max_retries = 3
        self.retry_delay = 1  # segundos

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Realiza una petición a la API con reintentos
        """
        url = f"{self.base_url}/{endpoint}"
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=10,
                    verify=True
                )
                response.raise_for_status()
                return response.json()
            except Timeout:
                logger.warning(f"Timeout en intento {attempts + 1} de {self.max_retries}")
                last_error = "Timeout al conectar con el servicio"
            except RequestException as e:
                logger.error(f"Error en la petición (intento {attempts + 1}): {str(e)}")
                last_error = str(e)
            
            attempts += 1
            if attempts < self.max_retries:
                time.sleep(self.retry_delay)

        raise RequestException(f"Error después de {self.max_retries} intentos: {last_error}")

    def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Obtiene el clima actual para una ubicación específica
        """
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "es"
            }
            
            data = self._make_request("weather", params)
            
            # Validar que los datos necesarios estén presentes
            if not all(key in data.get("main", {}) for key in ["temp", "humidity"]):
                raise ValueError("Datos incompletos en la respuesta de la API")

            return {
                "temperatura": round(float(data["main"]["temp"]), 1),
                "humedad": int(data["main"]["humidity"]),
                "viento": round(float(data["wind"].get("speed", 0)) * 3.6, 1),
                "lluvia": float(data.get("rain", {}).get("1h", 0)),
                "condicion": str(data["weather"][0]["description"]) if data.get("weather") else "desconocido",
                "condicion_id": int(data["weather"][0]["id"]) if data.get("weather") else 800,
                "timestamp": datetime.now().isoformat()
            }
        
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error al procesar datos del clima: {str(e)}")
            raise ValueError(f"Error al procesar datos del clima: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al obtener clima: {str(e)}")
            raise

    def get_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Obtiene el pronóstico del clima para los próximos 5 días
        """
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "es"
            }
            
            data = self._make_request("forecast", params)
            
            if "list" not in data or not data["list"]:
                raise ValueError("No se encontraron datos de pronóstico")

            # Filtrar pronósticos para obtener uno por día a las 12:00
            daily_forecasts = []
            seen_dates = set()

            for item in data["list"]:
                try:
                    dt = datetime.fromtimestamp(item["dt"])
                    date_str = dt.strftime("%Y-%m-%d")
                    
                    # Solo tomar un pronóstico por día y evitar duplicados
                    if dt.hour in [11, 12, 13] and date_str not in seen_dates:
                        seen_dates.add(date_str)
                        
                        forecast = {
                            "fecha": date_str,
                            "dia": self._get_day_name(dt.weekday()),
                            "temperatura": round(float(item["main"]["temp"]), 1),
                            "humedad": int(item["main"]["humidity"]),
                            "viento": round(float(item["wind"].get("speed", 0)) * 3.6, 1),
                            "lluvia": float(item.get("rain", {}).get("3h", 0)) / 3,
                            "condicion": str(item["weather"][0]["description"]) if item.get("weather") else "desconocido",
                            "condicion_id": int(item["weather"][0]["id"]) if item.get("weather") else 800
                        }
                        daily_forecasts.append(forecast)

                        # Solo necesitamos 5 días
                        if len(daily_forecasts) >= 5:
                            break
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error procesando pronóstico individual: {str(e)}")
                    continue

            if not daily_forecasts:
                raise ValueError("No se pudieron procesar los datos del pronóstico")

            return {"pronostico": daily_forecasts}
            
        except Exception as e:
            logger.error(f"Error al obtener pronóstico: {str(e)}")
            raise

    def _get_day_name(self, weekday: int) -> str:
        """
        Convierte el número de día de la semana a nombre en español
        """
        dias = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo"
        }
        return dias.get(weekday, "Desconocido") 