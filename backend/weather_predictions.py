from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.exceptions import NotFittedError
from weather_service import WeatherService

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeatherPredictions:
    def __init__(self, weather_service: WeatherService):
        """
        Inicializa el servicio de predicciones
        """
        if not isinstance(weather_service, WeatherService):
            raise ValueError("Se requiere una instancia válida de WeatherService")
            
        self.weather_service = weather_service
        self.dias_semana = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo"
        }

    def _calcular_tendencia(self, datos_historicos: List[float]) -> float:
        """
        Calcula la tendencia usando regresión lineal simple
        """
        try:
            if not datos_historicos or len(datos_historicos) < 2:
                logger.warning("Datos insuficientes para calcular tendencia")
                return 0.0

            # Convertir datos a float y limpiar valores no válidos
            datos_limpios = [float(x) for x in datos_historicos if x is not None and isinstance(x, (int, float))]
            
            if len(datos_limpios) < 2:
                logger.warning("Datos válidos insuficientes después de limpieza")
                return 0.0

            X = np.array(range(len(datos_limpios))).reshape(-1, 1)
            y = np.array(datos_limpios)
            
            modelo = LinearRegression()
            modelo.fit(X, y)
            
            return float(modelo.coef_[0])
            
        except (ValueError, NotFittedError) as e:
            logger.error(f"Error al calcular tendencia: {str(e)}")
            return 0.0
        except Exception as e:
            logger.error(f"Error inesperado al calcular tendencia: {str(e)}")
            return 0.0

    def analizar_patron_semanal(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Analiza los patrones del clima para la semana
        """
        try:
            # Validar coordenadas
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("Coordenadas geográficas no válidas")

            # Obtener datos del pronóstico
            pronostico = self.weather_service.get_forecast(lat, lon)
            datos_diarios = pronostico.get("pronostico", [])

            if not datos_diarios:
                raise ValueError("No se obtuvieron datos de pronóstico")

            # Inicializar diccionarios para almacenar análisis
            analisis_semanal = {
                "patrones_diarios": [],
                "recomendaciones": [],
                "alertas": []
            }

            # Procesar datos por día
            temperaturas = []
            humedades = []
            vientos = []

            for dia in datos_diarios:
                try:
                    temp = float(dia.get("temperatura", 0))
                    hum = float(dia.get("humedad", 0))
                    viento = float(dia.get("viento", 0))
                    
                    temperaturas.append(temp)
                    humedades.append(hum)
                    vientos.append(viento)

                    # Análisis diario
                    patron_diario = {
                        "dia": str(dia.get("dia", "")),
                        "fecha": str(dia.get("fecha", "")),
                        "condiciones": {
                            "temperatura": {
                                "valor": temp,
                                "categoria": self._categorizar_temperatura(temp)
                            },
                            "humedad": {
                                "valor": hum,
                                "categoria": self._categorizar_humedad(hum)
                            },
                            "viento": {
                                "valor": viento,
                                "categoria": self._categorizar_viento(viento)
                            }
                        },
                        "riesgo_cultivo": self._evaluar_riesgo_cultivo(temp, hum, viento)
                    }
                    
                    analisis_semanal["patrones_diarios"].append(patron_diario)
                except (ValueError, TypeError) as e:
                    logger.error(f"Error procesando día: {str(e)}")
                    continue

            if not analisis_semanal["patrones_diarios"]:
                raise ValueError("No se pudo procesar ningún día del pronóstico")

            # Análisis de tendencias
            tendencia_temp = self._calcular_tendencia(temperaturas)
            tendencia_hum = self._calcular_tendencia(humedades)

            # Generar recomendaciones y alertas
            self._generar_recomendaciones(analisis_semanal, temperaturas, humedades, vientos)

            # Añadir resumen semanal
            analisis_semanal["resumen"] = self._generar_resumen(
                temperaturas, humedades, vientos, tendencia_temp, tendencia_hum
            )

            return analisis_semanal

        except Exception as e:
            logger.error(f"Error en análisis semanal: {str(e)}")
            raise

    def _categorizar_temperatura(self, temp: float) -> str:
        """Categoriza la temperatura en rangos"""
        try:
            temp = float(temp)
            if temp < 15:
                return "fría"
            elif temp < 25:
                return "moderada"
            else:
                return "caliente"
        except (ValueError, TypeError):
            return "no disponible"

    def _categorizar_humedad(self, hum: float) -> str:
        """Categoriza la humedad en rangos"""
        try:
            hum = float(hum)
            if hum < 40:
                return "baja"
            elif hum < 70:
                return "moderada"
            else:
                return "alta"
        except (ValueError, TypeError):
            return "no disponible"

    def _categorizar_viento(self, viento: float) -> str:
        """Categoriza la velocidad del viento en rangos"""
        try:
            viento = float(viento)
            if viento < 10:
                return "suave"
            elif viento < 20:
                return "moderado"
            else:
                return "fuerte"
        except (ValueError, TypeError):
            return "no disponible"

    def _evaluar_riesgo_cultivo(self, temp: float, hum: float, viento: float) -> Dict[str, Any]:
        """Evalúa el riesgo para los cultivos basado en las condiciones climáticas"""
        try:
            riesgo = 0
            factores = []

            # Evaluar temperatura
            if temp > 30:
                riesgo += 2
                factores.append("temperatura alta")
            elif temp < 10:
                riesgo += 2
                factores.append("temperatura baja")

            # Evaluar humedad
            if hum > 80:
                riesgo += 2
                factores.append("humedad alta")
            elif hum < 30:
                riesgo += 1
                factores.append("humedad baja")

            # Evaluar viento
            if viento > 25:
                riesgo += 2
                factores.append("viento fuerte")

            nivel_riesgo = "bajo" if riesgo <= 1 else "medio" if riesgo <= 3 else "alto"

            return {
                "nivel": nivel_riesgo,
                "factores": factores,
                "valor": riesgo
            }
        except Exception as e:
            logger.error(f"Error al evaluar riesgo: {str(e)}")
            return {
                "nivel": "no disponible",
                "factores": [],
                "valor": 0
            }

    def _interpretar_tendencia(self, tendencia: float) -> str:
        """Interpreta la tendencia de una variable climática"""
        try:
            tendencia = float(tendencia)
            if abs(tendencia) < 0.1:
                return "estable"
            elif tendencia > 0:
                return "aumentando"
            else:
                return "disminuyendo"
        except (ValueError, TypeError):
            return "no disponible"

    def _generar_recomendaciones(self, analisis: Dict[str, Any], 
                                temperaturas: List[float], 
                                humedades: List[float], 
                                vientos: List[float]) -> None:
        """Genera recomendaciones basadas en las condiciones climáticas"""
        try:
            # Tendencias
            tendencia_temp = self._calcular_tendencia(temperaturas)
            if tendencia_temp > 0.5:
                analisis["recomendaciones"].append({
                    "tipo": "riego",
                    "mensaje": "Aumentar frecuencia de riego por tendencia al alza en temperaturas"
                })

            # Condiciones de humedad
            if any(h > 80 for h in humedades):
                analisis["alertas"].append({
                    "tipo": "hongos",
                    "nivel": "precaución",
                    "mensaje": "Riesgo de desarrollo de hongos por alta humedad"
                })

            # Condiciones de viento
            if any(v > 30 for v in vientos):
                analisis["alertas"].append({
                    "tipo": "viento",
                    "nivel": "advertencia",
                    "mensaje": "Vientos fuertes pueden afectar los cultivos"
                })

        except Exception as e:
            logger.error(f"Error al generar recomendaciones: {str(e)}")

    def _generar_resumen(self, temperaturas: List[float], 
                        humedades: List[float], 
                        vientos: List[float],
                        tendencia_temp: float,
                        tendencia_hum: float) -> Dict[str, Any]:
        """Genera el resumen semanal de las condiciones climáticas"""
        try:
            return {
                "temperatura_promedio": round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0,
                "humedad_promedio": round(sum(humedades) / len(humedades), 1) if humedades else 0,
                "viento_promedio": round(sum(vientos) / len(vientos), 1) if vientos else 0,
                "tendencias": {
                    "temperatura": self._interpretar_tendencia(tendencia_temp),
                    "humedad": self._interpretar_tendencia(tendencia_hum)
                }
            }
        except Exception as e:
            logger.error(f"Error al generar resumen: {str(e)}")
            return {
                "temperatura_promedio": 0,
                "humedad_promedio": 0,
                "viento_promedio": 0,
                "tendencias": {
                    "temperatura": "no disponible",
                    "humedad": "no disponible"
                }
            } 