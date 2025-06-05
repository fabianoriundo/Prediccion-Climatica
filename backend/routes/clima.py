from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime
from typing import List, Optional

router = APIRouter()

# Modelo para las coordenadas
class Coordenadas(BaseModel):
    lat: float
    lon: float

# Modelo para el pronóstico por hora
class PronosticoHora(BaseModel):
    hora: str
    temperatura: float
    condicion: str
    condicion_id: int
    humedad: float
    viento: float

# Configuración de OpenWeather
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "28be46c978f79172e0ef18567a6531cb")
BASE_URL = "https://api.openweathermap.org/data/2.5"

@router.post("/actual")
async def obtener_clima_actual(coords: Coordenadas):
    try:
        response = requests.get(
            f"{BASE_URL}/weather",
            params={
                "lat": coords.lat,
                "lon": coords.lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "es"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error al obtener datos del clima")
        
        data = response.json()
        
        return {
            "temperatura": data["main"]["temp"],
            "humedad": data["main"]["humidity"],
            "condicion": data["weather"][0]["description"],
            "condicion_id": data["weather"][0]["id"],
            "viento": data["wind"]["speed"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pronostico-horas")
async def obtener_pronostico_horas(coords: Coordenadas):
    try:
        response = requests.get(
            f"{BASE_URL}/forecast",
            params={
                "lat": coords.lat,
                "lon": coords.lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "es"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error al obtener pronóstico")
        
        data = response.json()
        pronostico = []
        
        # Obtener próximas 24 horas (8 periodos de 3 horas)
        for item in data["list"][:8]:
            hora = datetime.fromtimestamp(item["dt"]).strftime("%H:00")
            pronostico.append({
                "hora": hora,
                "temperatura": item["main"]["temp"],
                "condicion": item["weather"][0]["description"],
                "condicion_id": item["weather"][0]["id"],
                "humedad": item["main"]["humidity"],
                "viento": item["wind"]["speed"]
            })
        
        return {"pronostico": pronostico}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 