import httpx
import asyncio
import json

# --- Configuration ---
# URL de l'API et paramètres de recherche
SEARCH_TEXT = "chaussures nike"
ITEMS_PER_PAGE = 96  # On demande plus d'items par page pour être efficace
VINTED_API_URL = "https://www.vinted.fr/api/v2/catalog/items"

# Headers pour simuler un navigateur. Le cookie est essentiel.
# IMPORTANT : Ce cookie a une durée de vie. S'il expire, le script ne marchera plus.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "v_udt=WE40eExkOTRoNXArT1ZaNXlJeVVuWS9LNkVRSC0tMTRWakVpUzFjOHlnQWR5eC0tWjVhZ0lwNVpUellvWlFpdkNXcWYwdz09"
}

# --- Fonctions du Scraper ---

async def fetch_one_page(client: httpx.AsyncClient, page: int):
    """Récupère une seule page de résultats de l'API Vinted."""
    params = {
        "search_text": SEARCH_TEXT,
        "per_page": str(ITEMS_PER_PAGE),
        "page": str(page)
    }
    try:
        # On fait la requête directe à l'API avec un timeout
        response = await client.get(VINTED_API_URL, headers=HEADERS, params=params, timeout=30.0)
        
        # Lève une exception si la requête a échoué (status code 4xx ou 5xx)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        print(f"Succès pour la page {page}. Trouvé {len(items)} items.")
        return items

    except httpx.HTTPStatusError as e:
        print(f"Erreur HTTP en récupérant la page {page}: {e.response.status_code}")
        print(f"Réponse de l'API: {e.response.text[:500]}...") # Affiche le début de l'erreur
        return []
    except Exception as e:
        print(f"Une erreur inattendue est survenue pour la page {page}: {e}")
        return []


async def main():
    """Fonction principale pour lancer le test du scraper."""
    print("--- Lancement du scraper en mode requête directe (httpx) ---")
    
    # httpx.AsyncClient gère les connexions de manière efficace
    async with httpx.AsyncClient() as client:
        # Pour ce test, on ne récupère que la première page.
        # Plus tard, on fera une boucle pour toutes les récupérer.
        items_on_first_page = await fetch_one_page(client, page=1)

        if items_on_first_page:
            print(f"\n--- {len(items_on_first_page)} ITEMS TROUVÉS SUR LA PREMIÈRE PAGE ---")
            # On affiche les 5 premiers pour l'exemple
            for item in items_on_first_page[:5]:
                print(f"  Titre: {item.get('title')}")
                print(f"  Prix: {item.get('price')} {item.get('currency')}")
                print(f"  URL: {item.get('url')}")
                print("-" * 20)
        else:
            print("\nAucun item récupéré. Causes possibles :")
            print("1. Le cookie 'v_udt' est peut-être expiré.")
            print("2. Vinted a bloqué la requête (IP blacklistée, headers suspects).")
            print("3. La recherche n'a donné aucun résultat.")

# --- Point d'entrée du script ---

if __name__ == "__main__":
    asyncio.run(main())