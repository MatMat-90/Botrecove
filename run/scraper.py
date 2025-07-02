

import asyncio
import json
import random
import os
from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth.stealth import Stealth

import database

# --- Constantes ---
FAILED_PAGES_FILE = "failed_pages.log"

# --- Fonctions de chargement ---

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, "r") as f:
        return json.load(f)

def load_user_agents():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_agents_path = os.path.join(script_dir, "user_agents.json")
    with open(user_agents_path, "r") as f:
        return json.load(f)

# --- Fonctions de scraping autonomes ---

async def get_autonomous_cookie(browser: BrowserContext):
    """Génère le cookie de manière autonome en simulant une interaction humaine."""
    print("[Auth] Tentative de génération autonome du cookie...")
    page = await browser.new_page()
    stealth = Stealth()
    await stealth.apply_stealth_async(page)
    try:
        await page.goto("https://www.vinted.fr/", timeout=90000)
        await page.wait_for_load_state('networkidle', timeout=30000)

        try:
            accept_button = page.locator('#onetrust-accept-btn-handler')
            await accept_button.wait_for(state="visible", timeout=15000)
            await accept_button.click()
            print("[Auth] Bannière de cookies acceptée.")
            await page.wait_for_timeout(random.randint(1000, 2000))
        except Exception:
            print("[Auth] Pas de bannière de cookies détectée ou erreur, continuation.")

        # Étape 1 de l'interaction : Cliquer sur une catégorie de manière robuste
        print("[Auth] Clic sur une catégorie aléatoire pour simuler la navigation...")
        
        # Listes de catégories et de termes de recherche pour la randomisation
        categories = ["Femmes", "Hommes", "Enfants", "Maison", "Divertissement", "Animaux"]
        search_terms = {
            "Femmes": ["robe été", "sandales cuir", "sac à main", "jean slim", "blouse"],
            "Hommes": ["chemise lin", "bermuda", "baskets blanches", "lunettes de soleil", "montre"],
            "Enfants": ["jouet en bois", "t-shirt fille", "chaussures garçon", "livre enfant"],
            "Maison": ["housse de coussin", "vase céramique", "bougie parfumée", "linge de lit"],
            "Divertissement": ["livre policier", "jeu de société", "vinyle rock", "console de jeux"],
            "Animaux": ["panier pour chien", "arbre à chat", "laisse", "gamelle inox"]
        }
        
        # Sélection aléatoire
        random_category_name = random.choice(categories)
        search_term = random.choice(search_terms[random_category_name])

        print(f"[Auth] Catégorie choisie: '{random_category_name}', Terme de recherche: '{search_term}'")

        # Clic sur la catégorie
        category_link = page.get_by_role('link', name=random_category_name, exact=True)
        await category_link.wait_for(state='visible', timeout=30000)
        await category_link.click()
        
        await page.wait_for_load_state('networkidle', timeout=30000)
        print("[Auth] Page de catégorie chargée.")

        # Étape 2 de l'interaction : Simuler une frappe humaine
        print("[Auth] Simulation d'une recherche avec frappe réaliste...")
        search_bar = page.locator("#search_text").first
        await search_bar.click()
        await page.wait_for_timeout(random.randint(300, 600))
        
        # Taper le terme de recherche lettre par lettre
        for char in search_term:
            await page.keyboard.type(char)
            await page.wait_for_timeout(random.randint(50, 150))
            
        await page.wait_for_timeout(random.randint(500, 1200))
        await search_bar.press("Enter")

        # Attendre que la page de résultats se charge
        print("[Auth] Attente des résultats de la recherche...")
        await page.wait_for_selector("[data-testid*='item-card']", timeout=45000)
        await page.wait_for_load_state('networkidle', timeout=30000)

        # Faire défiler un peu pour plus de réalisme
        print("[Auth] Simulation du défilement de la page...")
        await page.mouse.wheel(0, random.randint(800, 1500))
        await page.wait_for_timeout(random.randint(1000, 2500))

        # Vérifier si le cookie est maintenant présent
        print("[Auth] Vérification de la présence du cookie après interaction...")
        cookies = await page.context.cookies()
        vinted_cookie = next((c for c in cookies if c['name'] == 'v_udt'), None)
        
        if not vinted_cookie:
             # Attente supplémentaire si le cookie n'est pas encore là
            await page.wait_for_function(
                "() => document.cookie.split('; ').some(c => c.startsWith('v_udt='))",
                timeout=30000
            )
            cookies = await page.context.cookies()
            vinted_cookie = next((c for c in cookies if c['name'] == 'v_udt'), None)

        if not vinted_cookie:
            raise Exception("Le cookie 'v_udt' n'a pas pu être extrait même après interaction.")
            
        print("[Auth] Cookie 'v_udt' généré et extrait avec succès !")
        return vinted_cookie['value']
    except Exception as e:
        # Sauvegarde du code HTML pour une analyse approfondie
        html_path = "auth_failure_page.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(await page.content())
        print(f"[Auth] ERREUR CRITIQUE lors de la génération du cookie: {e}")
        print(f"[Auth] Le code HTML de la page a été sauvegardé ici : {os.path.abspath(html_path)}")
        return None
    finally:
        await page.close()



async def get_catalog_urls(context: BrowserContext):
    # ... (le reste du code est identique à la v2)
    print("[Discovery] Démarrage de la découverte des catégories...")
    page = await context.new_page()
    catalog_urls = set()
    try:
        await page.goto("https://www.vinted.fr/", wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_selector('a[data-testid^="header-category-link"]', timeout=30000)
        links = await page.query_selector_all('a[data-testid^="header-category-link"]')
        for link in links:
            href = await link.get_attribute('href')
            if href and "catalog" in href:
                full_url = f"https://www.vinted.fr{href}"
                catalog_urls.add(full_url)
        print(f"[Discovery] {len(catalog_urls)} catégories principales trouvées.")
        return list(catalog_urls)
    except Exception as e:
        print(f"[Discovery] ERREUR lors de la récupération des URLs: {e}")
        return []
    finally:
        await page.close()

async def scraper_worker(queue: asyncio.Queue, context: BrowserContext, worker_id: int, config: dict, user_agents: list):
    # ... (le reste du code est identique à la v2)
    print(f"[Worker {worker_id}] Démarrage...")
    page = await context.new_page()

    while True:
        try:
            task = await asyncio.wait_for(queue.get(), timeout=300)
        except asyncio.TimeoutError:
            print(f"[Worker {worker_id}] Inactivité de la file d'attente. Terminaison.")
            break

        url, page_num, retries = task["url"], task["page"], task["retries"]
        target_url = f"{url}&page={page_num}"
        print(f"[Worker {worker_id}] Tâche: {target_url} (Essai {retries + 1})")

        try:
            # Rotation du User-Agent à chaque requête
            await page.set_extra_http_headers({"User-Agent": random.choice(user_agents)})

            api_data_event = asyncio.Event()
            api_data = None

            async def handle_response(response):
                nonlocal api_data
                if "/api/v2/catalog/items" in response.url:
                    try:
                        data = await response.json()
                        if "items" in data:
                            api_data = data
                    finally:
                        api_data_event.set()

            page.on("response", handle_response)

            # --- Simulation d'interaction humaine ---
            # Mouvement de souris aléatoire pour simuler la présence humaine
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600), steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.5, 1.5))

            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            # Scroll aléatoire pour imiter la navigation
            scroll_amount = random.randint(400, 1200)
            await page.mouse.wheel(0, scroll_amount)
            print(f"[Worker {worker_id}] Simulation de scroll ({scroll_amount}px).")
            await asyncio.sleep(random.uniform(1, 3))
            # --- Fin de la simulation ---

            await asyncio.wait_for(api_data_event.wait(), timeout=30)
            page.remove_listener("response", handle_response)

            if api_data and "items" in api_data:
                items = api_data["items"]
                new, updated, unchanged = database.process_items(items)
                print(f"[Worker {worker_id}] Succès: {new} nouveaux, {updated} MàJ, {unchanged} inchangés.")
                
                if page_num == 1 and new == 0 and updated == 0 and unchanged > 0:
                    print(f"[Delta] Catégorie à jour. Arrêt de l'exploration pour: {url}")
                elif items:
                    await queue.put({"url": url, "page": page_num + 1, "retries": 0})
                else:
                    print(f"[Worker {worker_id}] Catégorie terminée à la page {page_num}.")
            else:
                raise Exception("Aucune donnée d'item trouvée dans la réponse API.")

        except Exception as e:
            print(f"[Worker {worker_id}] ERREUR sur {target_url}: {e}")
            if retries < config["max_retries"]:
                task["retries"] += 1
                # Implémentation du backoff exponentiel
                backoff_time = config.get("base_backoff_time", 5) * (2 ** retries)
                print(f"[Worker {worker_id}] Nouvel essai dans {backoff_time:.2f} secondes...")
                await asyncio.sleep(backoff_time + random.uniform(0, 1))
                await queue.put(task)
            else:
                print(f"[Worker {worker_id}] Échec final pour {target_url} après {config['max_retries']} essais.")
                with open(FAILED_PAGES_FILE, "a") as f: f.write(f"{target_url}\n")
        finally:
            queue.task_done()
            await asyncio.sleep(random.uniform(2, 5))

    await page.close()
    print(f"[Worker {worker_id}] Terminé.")

# --- Orchestrateur Principal ---

async def main():
    config = load_config()
    user_agents = load_user_agents()
    
    database.init_db()
    open(FAILED_PAGES_FILE, "w").close()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Étape 1: Génération autonome du cookie
        vinted_cookie = await get_autonomous_cookie(browser)
        if not vinted_cookie: 
            await browser.close()
            return

        # Étape 2: Découverte des catégories avec un contexte authentifié
        base_context = await browser.new_context(user_agent=random.choice(user_agents))
        await base_context.add_cookies([{'name': 'v_udt', 'value': vinted_cookie, 'domain': '.vinted.fr', 'path': '/'}])
        all_catalog_urls = await get_catalog_urls(base_context)
        await base_context.close()
        if not all_catalog_urls: return

        # Étape 3: Filtrage et mise en file d'attente
        target_keywords = config.get("target_categories", [])
        final_urls = {url for url in all_catalog_urls if any(kw in url for kw in target_keywords)} if target_keywords else all_catalog_urls
        queue = asyncio.Queue()
        for url in final_urls:
            await queue.put({"url": url, "page": 1, "retries": 0})
        
        if queue.empty(): return

        print(f"--- {queue.qsize()} catégories à scraper. Lancement de {config['parallel_workers']} workers ---")

        # Étape 4: Lancement des workers
        worker_tasks = []
        proxies = config.get("proxies", [])
        for i in range(config['parallel_workers']):
            proxy = proxies[i % len(proxies)] if proxies else None
            context = await browser.new_context(
                user_agent=random.choice(user_agents),
                proxy={'server': proxy} if proxy else None
            )
            await context.add_cookies([{'name': 'v_udt', 'value': vinted_cookie, 'domain': '.vinted.fr', 'path': '/'}])
            print(f"[Worker {i+1}] Contexte créé. Proxy: {proxy or 'Aucun'}")
            worker_tasks.append(asyncio.create_task(scraper_worker(queue, context, i + 1, config, user_agents)))

        await queue.join()

        for task in worker_tasks: task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        await browser.close()

    print(f"\n--- Scraping terminé ---")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
