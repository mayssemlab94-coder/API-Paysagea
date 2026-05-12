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

# 1. Le GPS accepte maintenant toutes les parties de l'adresse !
async def trouver_gps(rue: str = "", code_postal: str = "", ville: str = "", pays: str = ""):
    # On rassemble tous les morceaux proprement, séparés par une virgule
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
    return {"temp": -5.2, "zone": "8a", "precip": 120.5}

async def trouver_sol(lat: float, lon: float):
    return {"ph": 6.5, "cat": "Neutre"}

# 2. On crée 4 belles cases pour l'interface internet
@app.get("/api/v1/gis-profile", response_model=ReponseGIS)
async def obtenir_profil(
    rue: str = Query("", description="Numéro et nom de rue (ex: 10 Rue de la Paix)"),
    code_postal: str = Query("", description="Code postal (ex: 75002)"),
    ville: str = Query("", description="Ville (ex: Paris)"),
    pays: str = Query("", description="Pays (ex: France)")
):
    # On vérifie qu'au moins une case importante est remplie
    if not rue and not code_postal and not ville:
         raise HTTPException(status_code=400, detail="Veuillez fournir au moins une ville ou un code postal")
    
    lat, lon = await trouver_gps(rue, code_postal, ville, pays)
    climat, sol = await asyncio.gather(trouver_climat(lat, lon), trouver_sol(lat, lon))
    
    return ReponseGIS(
        latitude=lat, longitude=lon,
        temperature_min=climat["temp"], zone_usda=climat["zone"], precipitations_ete=climat["precip"],
        ph_sol=sol["ph"], categorie_sol=sol["cat"]
    )