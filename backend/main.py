# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List
from weather_service import WeatherService
from weather_predictions import WeatherPredictions
import os
from dotenv import load_dotenv
import logging
from requests.exceptions import RequestException
import pandas as pd
from pathlib import Path
from routes import clima
import uvicorn

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="API de Clima para Agricultura",
    description="API para obtener datos meteorológicos para agricultura",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obtener API key
api_key = os.getenv("OPENWEATHER_API_KEY", "28be46c978f79172e0ef18567a6531cb")
if not api_key:
    logger.error("API key no encontrada")
    raise ValueError("API key no configurada")

# Inicializar servicios
try:
    weather_service = WeatherService(api_key=api_key)
    weather_predictions = WeatherPredictions(weather_service=weather_service)
except Exception as e:
    logger.error(f"Error al inicializar servicios: {str(e)}")
    raise

class LocationRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitud entre -90 y 90")
    lon: float = Field(..., ge=-180, le=180, description="Longitud entre -180 y 180")

    @validator('lat')
    def validate_lat(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("La latitud debe ser un número")
        return float(v)

    @validator('lon')
    def validate_lon(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("La longitud debe ser un número")
        return float(v)

@app.get("/")
async def root():
    """
    Endpoint de bienvenida
    """
    return {"mensaje": "API de Clima para Agricultura v1.0"}

@app.post("/clima/actual")
async def get_current_weather(location: LocationRequest) -> Dict[str, Any]:
    """
    Obtiene el clima actual para una ubicación específica
    """
    try:
        logger.info(f"Obteniendo clima actual para lat={location.lat}, lon={location.lon}")
        return weather_service.get_current_weather(location.lat, location.lon)
    except RequestException as e:
        logger.error(f"Error de conexión: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Error al conectar con el servicio de clima"
        )
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@app.post("/clima/pronostico")
async def get_weather_forecast(location: LocationRequest) -> Dict[str, Any]:
    """
    Obtiene el pronóstico del clima para una ubicación específica
    """
    try:
        logger.info(f"Obteniendo pronóstico para lat={location.lat}, lon={location.lon}")
        return weather_service.get_forecast(location.lat, location.lon)
    except RequestException as e:
        logger.error(f"Error de conexión: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Error al conectar con el servicio de pronóstico"
        )
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@app.post("/clima/analisis-semanal")
async def get_weekly_analysis(location: LocationRequest) -> Dict[str, Any]:
    """
    Obtiene un análisis detallado del clima semanal con predicciones y recomendaciones
    """
    try:
        logger.info(f"Generando análisis semanal para lat={location.lat}, lon={location.lon}")
        return weather_predictions.analizar_patron_semanal(location.lat, location.lon)
    except RequestException as e:
        logger.error(f"Error de conexión: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Error al conectar con el servicio de clima"
        )
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@app.get("/cultivos/riego/{cultivo}")
async def get_irrigation_needs(cultivo: str) -> List[Dict[str, Any]]:
    """
    Obtiene las necesidades de riego para un cultivo específico
    """
    try:
        logger.info(f"Obteniendo necesidades de riego para el cultivo: {cultivo}")
        
        # Leer el archivo CSV
        csv_path = Path("cultivos_condiciones.csv")
        if not csv_path.exists():
            raise FileNotFoundError("Archivo de datos de cultivos no encontrado")
        
        df = pd.read_csv(csv_path)
        
        # Filtrar por cultivo y obtener los datos necesarios
        cultivo_data = df[df['Nombre'] == cultivo][['Día', 'Necesidad_Riego']]
        
        if cultivo_data.empty:
            raise ValueError(f"No se encontraron datos para el cultivo: {cultivo}")
        
        # Convertir a lista de diccionarios
        resultado = [
            {"dia": row['Día'], "necesidad_riego": row['Necesidad_Riego']}
            for _, row in cultivo_data.iterrows()
        ]
        
        return resultado
        
    except FileNotFoundError as e:
        logger.error(f"Error de archivo: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail="Datos de cultivos no disponibles"
        )
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@app.get("/cultivos/estado/{cultivo}")
async def get_crop_status(cultivo: str) -> Dict[str, Any]:
    """
    Obtiene el estado del cultivo específico y sus datos semanales
    """
    try:
        logger.info(f"Obteniendo estado del cultivo: {cultivo}")
        
        # Leer el archivo CSV
        df = pd.read_csv('cultivos_condiciones.csv')
        
        # Filtrar por el cultivo seleccionado
        cultivo_df = df[df['Nombre'] == cultivo]
        
        if cultivo_df.empty:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para el cultivo: {cultivo}")
        
        # Contar los diferentes estados
        estados = cultivo_df['Estado_Cultivo'].value_counts().to_dict()
        
        # Obtener los datos semanales
        datos_semanales = []
        for _, row in cultivo_df.iterrows():
            datos_semanales.append({
                'Día': row['Día'],
                'Estado_Cultivo': row['Estado_Cultivo'],
                'Riesgo_Insectos': row['Riesgo_Insectos'],
                'Riesgo_Hongos': row['Riesgo_Hongos'],
                'Riesgo_Bacterias': row['Riesgo_Bacterias'],
                'Riesgo_Virus': row['Riesgo_Virus'],
                'Riesgo_Malezas': row['Riesgo_Malezas']
            })
        
        return {
            "estados": estados,
            "total_registros": len(cultivo_df),
            "datos_semanales": datos_semanales
        }
        
    except Exception as e:
        logger.error(f"Error al obtener estado del cultivo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cultivos/riesgo-plagas/{cultivo}")
async def get_pest_risk(cultivo: str) -> Dict[str, Any]:
    """
    Obtiene el riesgo de plagas para un cultivo específico
    """
    try:
        logger.info(f"Obteniendo riesgo de plagas para el cultivo: {cultivo}")
        
        # Leer el archivo CSV
        df = pd.read_csv('cultivos_condiciones.csv')
        
        # Filtrar por el cultivo seleccionado
        cultivo_df = df[df['Nombre'] == cultivo]
        
        if cultivo_df.empty:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para el cultivo: {cultivo}")
        
        # Calcular el promedio de riesgo por tipo de plaga
        riesgos = {
            'Riesgo_Insectos': round(cultivo_df['Riesgo_Insectos'].mean()),
            'Riesgo_Hongos': round(cultivo_df['Riesgo_Hongos'].mean()),
            'Riesgo_Bacterias': round(cultivo_df['Riesgo_Bacterias'].mean()),
            'Riesgo_Virus': round(cultivo_df['Riesgo_Virus'].mean()),
            'Riesgo_Malezas': round(cultivo_df['Riesgo_Malezas'].mean())
        }
        
        # Determinar el nivel de riesgo general basado en el promedio de todos los riesgos
        promedio_general = sum(riesgos.values()) / len(riesgos)
        nivel_riesgo = 'Bajo' if promedio_general < 2.5 else 'Medio' if promedio_general < 3.5 else 'Alto'
        
        return {
            "riesgos": riesgos,
            "nivel_riesgo": nivel_riesgo
        }
        
    except Exception as e:
        logger.error(f"Error al obtener riesgo de plagas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cultivos/ahorro-agua/{cultivo}")
async def get_water_savings(cultivo: str) -> Dict[str, Any]:
    """
    Obtiene los datos de ahorro de agua para un cultivo específico
    """
    try:
        logger.info(f"Obteniendo datos de ahorro de agua para el cultivo: {cultivo}")
        
        # Leer el archivo CSV
        df = pd.read_csv('cultivos_condiciones.csv')
        
        # Filtrar por el cultivo seleccionado
        cultivo_df = df[df['Nombre'] == cultivo]
        
        if cultivo_df.empty:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para el cultivo: {cultivo}")
        
        # Calcular el ahorro de agua basado en la necesidad de riego
        # Un menor valor de necesidad de riego implica mayor ahorro
        max_riego = cultivo_df['Necesidad_Riego'].max()
        ahorro_agua = cultivo_df.apply(lambda row: {
            'dia': row['Día'],
            'ahorro': round(((max_riego - row['Necesidad_Riego']) / max_riego) * 100, 1)
        }, axis=1).tolist()
        
        return {
            "ahorro_diario": ahorro_agua,
            "promedio_ahorro": round(sum(item['ahorro'] for item in ahorro_agua) / len(ahorro_agua), 1)
        }
        
    except Exception as e:
        logger.error(f"Error al obtener datos de ahorro de agua: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Manejador general de excepciones
    """
    logger.error(f"Error no manejado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "type": type(exc).__name__
        }
    )

# Incluir las rutas del clima
app.include_router(clima.router, prefix="/clima", tags=["clima"])

if __name__ == "__main__":
    logger.info("Iniciando servidor...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
