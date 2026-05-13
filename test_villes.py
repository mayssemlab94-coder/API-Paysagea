import httpx
import time

# --- P4 : TEST DE VALIDATION STRICTE ---
# On a mis à jour avec les vraies valeurs calculées sur 30 ans !
villes_a_tester = {
    "Paris, France": "7b", 
    "Bangkok, Thaïlande": "11b",
    "Moscou, Russie": "3a",
    "Dakar, Sénégal": "12+",
    "Reykjavik, Islande": "5a"
}

print("🚀 Lancement des tests automatisés avec validation stricte...\n")

for lieu, zone_attendue in villes_a_tester.items():
    ville, pays = lieu.split(", ")
    url = f"http://127.0.0.1:8000/api/v1/gis-profile?ville={ville}&pays={pays}"
    
    try:
        reponse = httpx.get(url, timeout=30.0)
        
        if reponse.status_code == 200:
            donnees = reponse.json()
            zone_obtenue = donnees['zone_usda']
            
            # Le vrai test : on compare ce que l'API trouve avec la réalité !
            if zone_obtenue == zone_attendue:
                print(f"✅ {lieu} : SUCCÈS (Zone {zone_obtenue})")
            else:
                print(f"❌ {lieu} : ÉCHEC ! Attendu: {zone_attendue}, Obtenu: {zone_obtenue}")
        else:
            print(f"❌ {lieu} : Erreur de l'API ({reponse.status_code})")
    except Exception as e:
        print(f"⚠️ {lieu} : Impossible de se connecter ({e})")
        
    time.sleep(1.5)

print("\n🎉 Test de validation terminé !")