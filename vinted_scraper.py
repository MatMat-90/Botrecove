

import asyncio
import json
import random
from playwright.async_api import async_playwright, Page, BrowserContext

# --- Constantes ---
RESULTS_FILE = "results.jsonl"
FAILED_PAGES_FILE = "failed_pages.log"

# --- Fonctions de chargement ---

def load_config():
    """Charge la configuration depuis config.json."""
    with open("config.json", "r") as f:
        return json.load(f)

def load_user_agents():
    """Charge la liste des User-Agents depuis user_agents.json."""
    with open("user_agents.json", "r") as f:
        return json.load(f)

# --- Worker de Scraping ---

async def scraper_worker(
    queue: asyncio.Queue,
    context: BrowserContext,
    config: dict,
    worker_id: int
):
    """
    Un worker qui consomme des tâches (pages à scraper) depuis une file d'attente.
    """
    print(f"[Worker {worker_id}] Démarrage...")
    page = await context.new_page()

    while not queue.empty():
        task = await queue.get()
        search_term, page_num, retries = task["term"], task["page"], task["retries"]
        
        print(f"[Worker {worker_id}] Tâche reçue: {search_term} - Page {page_num} (Essai {retries + 1})" )

        try:
            # Simulation de comportement humain
            await page.mouse.move(random.randint(0, 100), random.randint(0, 100))
            await asyncio.sleep(random.uniform(1, 3))

            target_url = f"https://www.vinted.fr/catalog?search_text={search_term}&page={page_num}"
            api_data_event = asyncio.Event()
            api_data = None

            async def handle_response(response):
                nonlocal api_data
                if f"/api/v2/catalog/items" in response.url and f"page={page_num}" in response.url:
                    try:
                        data = await response.json()
                        if "items" in data:
                            api_data = data
                            api_data_event.set()
                    except Exception:
                        api_data_event.set() # Débloquer même en cas d'erreur

            page.on("response", handle_response)
            
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.wait_for(api_data_event.wait(), timeout=30)
            page.remove_listener("response", handle_response)

            if api_data and "items" in api_data:
                items = api_data["items"]
                with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                    for item in items:
                        f.write(json.dumps(item) + "\n")
                print(f"[Worker {worker_id}] Succès: {len(items)} items de la page {page_num} sauvegardés.")
            else:
                raise Exception("Aucune donnée d'item trouvée dans la réponse API.")

        except Exception as e:
            print(f"[Worker {worker_id}] ERREUR sur la page {page_num}: {e}")
            if retries < config["max_retries"]:
                print(f"[Worker {worker_id}] Remise en file d'attente de la page {page_num}.")
                task["retries"] += 1
                await queue.put(task)
            else:
                print(f"[Worker {worker_id}] Échec final pour la page {page_num}. Enregistrement dans {FAILED_PAGES_FILE}.")
                with open(FAILED_PAGES_FILE, "a") as f:
                    f.write(f"{search_term}, page {page_num}\n")
        finally:
            queue.task_done()

    await page.close()
    print(f"[Worker {worker_id}] Terminé.")

# --- Orchestrateur Principal ---

async def main():
    """
    Orchestre le scraping en créant les tâches et en lançant les workers.
    """
    config = load_config()
    user_agents = load_user_agents()
    
    # Vider les fichiers de résultats précédents
    open(RESULTS_FILE, "w").close()
    open(FAILED_PAGES_FILE, "w").close()

    playwright_options = {"headless": True}
    if config.get("proxy_server"):
        playwright_options["proxy"] = {"server": config["proxy_server"]}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**playwright_options)
        
        # Création de la file d'attente des tâches
        queue = asyncio.Queue()
        for search in config["searches"]:
            for page_num in range(1, search["max_pages"] + 1):
                task = {"term": search["term"], "page": page_num, "retries": 0}
                await queue.put(task)
        
        print(f"{queue.qsize()} tâches créées. Lancement de {config['parallel_workers']} workers...")

        # Création et lancement des workers
        worker_tasks = []
        for i in range(config["parallel_workers"]):
            # Chaque worker a son propre contexte de navigateur avec un User-Agent différent
            context = await browser.new_context(user_agent=random.choice(user_agents))
            # Gérer les cookies une seule fois par worker
            page = await context.new_page()
            try:
                await page.goto("https://www.vinted.fr/", wait_until="domcontentloaded", timeout=60000)
                accept_button = page.locator('#onetrust-accept-btn-handler')
                await accept_button.wait_for(state="visible", timeout=10000)
                await accept_button.click()
                await page.close()
                print(f"[Worker {i+1}] Cookies acceptés.")
            except Exception as e:
                print(f"[Worker {i+1}] Pas de bannière de cookies ou erreur: {e}")
                await page.close()

            task = asyncio.create_task(scraper_worker(queue, context, config, i + 1))
            worker_tasks.append(task)

        # Attendre que toutes les tâches de la file soient terminées
        await queue.join()

        # Annuler les workers (qui sont maintenant en attente)
        for task in worker_tasks:
            task.cancel()
        
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        await browser.close()

    print(f"\n--- Scraping terminé. Résultats dans {RESULTS_FILE}, échecs dans {FAILED_PAGES_FILE} ---")

if __name__ == "__main__":
    asyncio.run(main())
