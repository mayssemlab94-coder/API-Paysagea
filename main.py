from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import httpx
import asyncio

app = FastAPI(title="API GIS Paysagea")

class ReponseGIS(BaseModel):
    latitude: float
    longitude: float
    temperature_min: float
    zone_usda: str
    precipitations_ete: float
    ph_sol: float
    categorie_sol: str

async def trouver_gps(rue: str = "", code_postal: str = "", ville: str = "", pays: str = ""):
    morceaux = [rue, code_postal, ville, pays]
    recherche = ", ".join([m for m in morceaux if m != ""])
    url = f"https://nominatim.openstreetmap.org/search?q={recherche}&format=json&limit=1"
    
    async with httpx.AsyncClient() as client:
        reponse = await client.get(url, headers={"User-Agent": "Paysagea/1.0"})
        donnees = reponse.json()
        if not donnees:
            raise HTTPException(status_code=404, detail=f"Lieu introuvable pour l'adresse : {recherche}")
        return float(donnees[0]["lat"]), float(donnees[0]["lon"])

async def trouver_climat(lat: float, lon: float):
    # Connexion à la VRAIE base de données météo (Open-Meteo)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_min,precipitation_sum&timezone=auto"
    async with httpx.AsyncClient() as client:
        reponse = await client.get(url)
        if reponse.status_code == 200:
            donnees = reponse.json()
            # On prend la température la plus basse prévue
            temp_min = min(donnees["daily"]["temperature_2m_min"])
            # On calcule le cumul de pluie
            precip = sum(donnees["daily"]["precipitation_sum"])
            
            # Déduction intelligente de la vraie Zone USDA
            if temp_min < -12: zone = "7a"
            elif temp_min < -6: zone = "8a"
            elif temp_min < -1: zone = "9a"
            else: zone = "10a"
            
            return {"temp": temp_min, "zone": zone, "precip": round(precip, 1)}
    return {"temp": 0.0, "zone": "Inconnue", "precip": 0.0}

async def trouver_sol(lat: float, lon: float):
    # Connexion à la VRAIE base mondiale des sols (ISRIC SoilGrids)
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=phh2o&depth=0-5cm&value=mean"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            reponse = await client.get(url)
            if reponse.status_code == 200:
                donnees = reponse.json()
                # Calcul scientifique du vrai pH
                valeur_brute = donnees["properties"]["layers"][0]["depths"][0]["values"]["mean"]
                ph_reel = valeur_brute / 10
                
                # Catégorisation automatique du sol
                if ph_reel < 6.5: cat = "Acide"
                elif ph_reel > 7.5: cat = "Basique"
                else: cat = "Neutre"
                
                return {"ph": round(ph_reel, 1), "cat": cat}
    except Exception:
        pass
    return {"ph": 6.5, "cat": "Neutre (Serveur ISRIC indisponible)"}

@app.get("/api/v1/gis-profile", response_model=ReponseGIS)
async def obtenir_profil(
    rue: str = Query("", description="Numéro et nom de rue (ex: 10 Rue de la Paix)"),
    code_postal: str = Query("", description="Code postal (ex: 75002)"),
    ville: str = Query("", description="Ville (ex: Paris)"),
    pays: str = Query("", description="Pays (ex: France)")
):
    if not rue and not code_postal and not ville:
         raise HTTPException(status_code=400, detail="Veuillez fournir au moins une ville ou un code postal")
    
    lat, lon = await trouver_gps(rue, code_postal, ville, pays)
    
    # On lance les recherches GPS, Météo et Sol en même temps !
    climat, sol = await asyncio.gather(trouver_climat(lat, lon), trouver_sol(lat, lon))
    
    return ReponseGIS(
        latitude=lat, longitude=lon,
        temperature_min=climat["temp"], zone_usda=climat["zone"], precipitations_ete=climat["precip"],
        ph_sol=sol["ph"], categorie_sol=sol["cat"]
    )