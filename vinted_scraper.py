import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json

# --- Configuration ---
SEARCH_TEXT = "chaussures nike"
MAX_PAGES_TO_SCRAPE = 3 # Nombre de pages à scraper

async def fetch_page_data(page, page_num):
    """
    Navigue vers une page de résultats et intercepte les données de l'API correspondante.
    """
    print(f"\n--- Scraping de la page {page_num} ---")
    target_url = f"https://www.vinted.fr/catalog?search_text={SEARCH_TEXT}&page={page_num}"
    
    api_data_event = asyncio.Event()
    api_data = None

    async def handle_response(response):
        nonlocal api_data
        if f"/api/v2/catalog/items" in response.url and f"page={page_num}" in response.url:
            print(f"Interception de l'API pour la page {page_num} réussie.")
            try:
                api_data = await response.json()
                api_data_event.set()
            except Exception as e:
                print(f"Erreur JSON pour la page {page_num}: {e}")
                api_data_event.set()

    page.on("response", handle_response)

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.wait_for(api_data_event.wait(), timeout=30)
    finally:
        page.remove_listener("response", handle_response)
    
    return api_data.get("items", []) if api_data else []

async def main():
    """
    Fonction principale pour orchestrer le scraping de plusieurs pages.
    """
    print("--- Lancement du scraper multi-pages final ---")
    all_items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigation initiale pour gérer les cookies
            print("Navigation initiale pour gérer les cookies...")
            await page.goto(f"https://www.vinted.fr/catalog?search_text={SEARCH_TEXT}", wait_until="domcontentloaded", timeout=60000)
            try:
                accept_button = page.locator('#onetrust-accept-btn-handler')
                await accept_button.wait_for(state="visible", timeout=10000)
                print("Bannière de cookies trouvée. Clic sur 'Tout accepter'.")
                await accept_button.click()
                await page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                print("Bannière de cookies non trouvée, on continue.")

            # Boucle pour scraper chaque page
            for page_num in range(1, MAX_PAGES_TO_SCRAPE + 1):
                items = await fetch_page_data(page, page_num)
                if items:
                    print(f"Page {page_num}: {len(items)} items trouvés.")
                    all_items.extend(items)
                else:
                    print(f"Aucun item trouvé sur la page {page_num}. Arrêt.")
                    break
                await asyncio.sleep(2) # Pause entre les pages

            # --- AFFICHAGE DES RÉSULTATS ---
            print(f"\n--- TOTAL DE {len(all_items)} ITEMS TROUVÉS SUR {MAX_PAGES_TO_SCRAPE} PAGES ---")
            for item in all_items[:10]: # On affiche les 10 premiers
                print(f"  Titre: {item.get('title')}")
                price_info = item.get('price', {})
                amount = price_info.get('amount')
                currency = price_info.get('currency_code')
                if amount and currency:
                    print(f"  Prix: {amount} {currency}")
                else:
                    print(f"  Prix: N/A")
                print(f"  URL: {item.get('url')}")
                print("-" * 20)

        except Exception as e:
            print(f"\nUne erreur majeure est survenue: {e}")
            await page.screenshot(path="error_screenshot.png")
            print("Capture d'écran sauvegardée dans 'error_screenshot.png'")
        
        finally:
            await browser.close()
            print("\n--- Scraper terminé ---")

if __name__ == "__main__":
    asyncio.run(main())