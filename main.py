import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import httpx
import asyncio
from datetime import datetime, timedelta

# --- CONFIGURATION PRO ---
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title="API GIS Paysagea - Production")

# Cache mémoire pour aller plus vite
CACHE_CLIMAT = {}
CACHE_SOL = {}

class ReponseGIS(BaseModel):
    latitude: float
    longitude: float
    temperature_min: float
    zone_usda: str
    precipitations_ete: float
    ph_sol: float
    categorie_sol: str

# --- FONCTION 1 : Calcul de la vraie Zone USDA (26 zones) ---
def calculer_zone_usda(temp_min: float) -> str:
    if temp_min < -45.6: return "1a"
    elif temp_min < -42.8: return "1b"
    elif temp_min < -40.0: return "2a"
    elif temp_min < -37.2: return "2b"
    elif temp_min < -34.4: return "3a"
    elif temp_min < -31.7: return "3b"
    elif temp_min < -28.9: return "4a"
    elif temp_min < -26.1: return "4b"
    elif temp_min < -23.3: return "5a"
    elif temp_min < -20.6: return "5b"
    elif temp_min < -17.8: return "6a"
    elif temp_min < -15.0: return "6b"
    elif temp_min < -12.2: return "7a"
    elif temp_min < -9.4: return "7b"
    elif temp_min < -6.7: return "8a"
    elif temp_min < -3.9: return "8b"
    elif temp_min < -1.1: return "9a"
    elif temp_min < 1.7: return "9b"
    elif temp_min < 4.4: return "10a"
    elif temp_min < 7.2: return "10b"
    elif temp_min < 10.0: return "11a"
    elif temp_min < 12.8: return "11b"
    else: return "12+"

# --- FONCTION 2 : Trouver les coordonnées GPS ---
async def trouver_gps(rue: str, code_postal: str, ville: str, pays: str):
    morceaux = [rue, code_postal, ville, pays]
    recherche = ", ".join([m for m in morceaux if m != ""])
    url = f"https://nominatim.openstreetmap.org/search?q={recherche}&format=json&limit=1"
    
    async with httpx.AsyncClient() as client:
        reponse = await client.get(url, headers={"User-Agent": "Paysagea/1.0_Production"})
        donnees = reponse.json()
        if not donnees:
            raise HTTPException(status_code=404, detail=f"Lieu introuvable pour l'adresse : {recherche}")
        return float(donnees[0]["lat"]), float(donnees[0]["lon"])

# --- FONCTION 3 : Trouver le climat sur 10 ans ---
async def trouver_climat(lat: float, lon: float):
    cle_cache = f"{round(lat, 2)}_{round(lon, 2)}"
    if cle_cache in CACHE_CLIMAT:
        return CACHE_CLIMAT[cle_cache]

    date_fin = datetime.now() - timedelta(days=365)
    date_debut = date_fin - timedelta(days=3650) # Remonte 10 ans en arrière
    
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={date_debut.strftime('%Y-%m-%d')}&end_date={date_fin.strftime('%Y-%m-%d')}&daily=temperature_2m_min,precipitation_sum&timezone=auto"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            reponse = await client.get(url)
            reponse.raise_for_status()
            donnees = reponse.json()
            
            temps = [t for t in donnees["daily"]["temperature_2m_min"] if t is not None]
            precips = [p for p in donnees["daily"]["precipitation_sum"] if p is not None]
            
            temp_min_extreme = min(temps) if temps else 0.0
            precip_moyenne = (sum(precips) / 10) if precips else 0.0
            
            resultat = {
                "temp": round(temp_min_extreme, 1), 
                "zone": calculer_zone_usda(temp_min_extreme), 
                "precip": round(precip_moyenne, 1)
            }
            CACHE_CLIMAT[cle_cache] = resultat
            return resultat
    except Exception as e:
        logger.error(f"Erreur API Climat : {str(e)}")
        return {"temp": 0.0, "zone": "Erreur", "precip": 0.0}

# --- FONCTION 4 : Trouver le pH du sol ---
async def trouver_sol(lat: float, lon: float):
    cle_cache = f"{round(lat, 2)}_{round(lon, 2)}"
    if cle_cache in CACHE_SOL:
        return CACHE_SOL[cle_cache]

    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=phh2o&depth=0-5cm&value=mean"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            reponse = await client.get(url)
            reponse.raise_for_status()
            donnees = reponse.json()
            
            valeur_brute = donnees["properties"]["layers"][0]["depths"][0]["values"]["mean"]
            ph_reel = valeur_brute / 10
            
            if ph_reel < 6.5: cat = "Acide"
            elif ph_reel > 7.5: cat = "Basique"
            else: cat = "Neutre"
            
            resultat = {"ph": round(ph_reel, 1), "cat": cat}
            CACHE_SOL[cle_cache] = resultat
            return resultat
    except Exception as e:
        logger.error(f"Erreur API Sol ISRIC : {str(e)}")
        return {"ph": 0.0, "cat": "Erreur de connexion ISRIC"}

# --- L'API PRINCIPALE ---
@app.get("/api/v1/gis-profile", response_model=ReponseGIS)
async def obtenir_profil(
    rue: str = Query("", description="Numéro et nom de rue"),
    code_postal: str = Query("", description="Code postal"),
    ville: str = Query("", description="Ville"),
    pays: str = Query("", description="Pays")
):
    if not rue and not code_postal and not ville:
         raise HTTPException(status_code=400, detail="Veuillez fournir au moins une ville ou un code postal")
    
    lat, lon = await trouver_gps(rue, code_postal, ville, pays)
    climat, sol = await asyncio.gather(trouver_climat(lat, lon), trouver_sol(lat, lon))
    
    return ReponseGIS(
        latitude=lat, longitude=lon,
        temperature_min=climat["temp"], zone_usda=climat["zone"], precipitations_ete=climat["precip"],
        ph_sol=sol["ph"], categorie_sol=sol["cat"]
    )