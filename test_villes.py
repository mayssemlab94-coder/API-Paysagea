import httpx
import time

# La liste des 20 villes mondiales exigées par Antonin
villes_a_tester = [
    "Paris, France", "Tunis, Tunisie", "Tokyo, Japon", "New York, USA",
    "Sydney, Australie", "Dakar, Sénégal", "Oslo, Norvège", "Rio de Janeiro, Brésil",
    "Pékin, Chine", "Moscou, Russie", "Nairobi, Kenya", "Lima, Pérou",
    "Montréal, Canada", "Berlin, Allemagne", "Le Caire, Égypte", "Séoul, Corée du Sud",
    "Reykjavik, Islande", "Bangkok, Thaïlande", "Bogota, Colombie", "Athènes, Grèce"
]

print("🚀 Lancement des tests automatisés sur 20 villes mondiales...\n")

for lieu in villes_a_tester:
    ville, pays = lieu.split(", ")
    
    # On appelle ton API locale (qui tourne en arrière-plan)
    url = f"http://127.0.0.1:8000/api/v1/gis-profile?ville={ville}&pays={pays}"
    
    try:
        # On laisse 20 secondes max au serveur pour répondre
        reponse = httpx.get(url, timeout=20.0)
        
        if reponse.status_code == 200:
            donnees = reponse.json()
            print(f"✅ {lieu} : Temp {donnees['temperature_min']}°C | Zone {donnees['zone_usda']} | Sol {donnees['categorie_sol']}")
        else:
            print(f"❌ {lieu} : Erreur de l'API ({reponse.status_code})")
    except Exception as e:
        print(f"⚠️ {lieu} : Impossible de se connecter")
        
    # On fait une pause de 1,5 seconde entre chaque ville pour ne pas bloquer le GPS mondial !
    time.sleep(1.5)

print("\n🎉 Test des 20 villes terminé avec succès !")