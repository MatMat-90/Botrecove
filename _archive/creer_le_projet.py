
   ... first 56 lines hidden ...
    57                     return None
    58     """,
    59
    60     "api_scraper.py": """
    61         import asyncio, httpx, json, random
    62
    63         PROXY_CONFIG = {"http://": None, "https://": None}
    64         SEARCH_TERMS = ["robe", "pantalon", "nike", "adidas", "zara"]
    65         ITEMS_PER_PAGE, MAX_PAGES_PER_TERM, CONCURRENT_REQUESTS, REQUEST_TIMEOUT = 96, 100, 10
       , 30.0
    66         RESULTS_FILE, ERRORS_FILE = "vinted_items.jsonl", "vinted_errors.log"
    67
    68         class VintedAPIClient:
    69             VINTED_API_URL = "https://www.vinted.fr/api/v2/catalog/items"
    70             USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
       (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"]
    71             def __init__(self, c, p):
    72                 self.cookie, self.client = c, httpx.AsyncClient(proxies=p, http2=True,
       timeout=REQUEST_TIMEOUT)
    73             async def fetch_page(self, s, n):
    74                 h = {"User-Agent": random.choice(self.USER_AGENTS), "Accept":
       "application/json", "Cookie": f"v_udt={self.cookie}"}
    75                 p = {"search_text": s, "per_page": str(ITEMS_PER_PAGE), "page": str(n)}
    76                 try:
    77                     r = await self.client.get(self.VINTED_API_URL, headers=h, params=p);
       r.raise_for_status(); return r.json()
    78                 except Exception as e:
    79                     with open(ERRORS_FILE, "a") as f: f.write(f"Erreur: {e} pour {s} page {n}
       \\n")
    80             async def close(self): await self.client.aclose()
    81
    82         class VintedScraper:
    83             def __init__(self, c, p):
    84                 self.api, self.q = VintedAPIClient(c, p), asyncio.Queue()
    85             async def _worker(self):
    86                 while True:
    87                     s, n = await self.q.get()
    88                     d = await self.api.fetch_page(s, n)
    89                     if d and "items" in d:
    90                         i = d["items"]
    91                         with open(RESULTS_FILE, "a", encoding="utf-8") as f:
    92                             for it in i: f.write(json.dumps(it) + "\\n")
    93                         if len(i) == ITEMS_PER_PAGE and n < MAX_PAGES_PER_TERM: await self
       .q.put((s, n + 1))
    94                     self.q.task_done(); await asyncio.sleep(random.uniform(0.5, 1.5))
    95             async def run(self):
    96                 open(RESULTS_FILE, "w").close(); open(ERRORS_FILE, "w").close()
    97                 for t in SEARCH_TERMS: await self.q.put((t, 1))
    98                 tasks = [asyncio.create_task(self._worker()) for _ in range
       (CONCURRENT_REQUESTS)]
    99                 await self.q.join()
   100                 for t in tasks: t.cancel()
   101                 await asyncio.gather(*tasks, return_exceptions=True); await self.api.close()
   102     """,
   103
   104     "run.py": """
   105         import asyncio, sys
   106         from cookie_generator import get_vinted_cookie
   107         from api_scraper import VintedScraper, PROXY_CONFIG
   108
   109         async def main():
   110             print("--- Lancement du scraper V2 ---")
   111             cookie = await get_vinted_cookie()
   112             if not cookie:
   113                 print("\\nERREUR CRITIQUE: Impossible de récupérer le cookie Vinted.")
   114                 return
   115             print("\\n--- Cookie obtenu. Lancement du scraping. ---")
   116             scraper = VintedScraper(cookie=cookie, proxy_config=PROXY_CONFIG)
   117             try:
   118                 await scraper.run()
   119             finally:
   120                 print("\\n--- Processus de scraping terminé ---")
   121
   122         if __name__ == "__main__":
   123             if sys.platform == "win32":
   124                 asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
   125             asyncio.run(main())
   126     """
   127 }
   128
   129 # --- Script Principal ---
   130 def create_project():
   131     """Crée le dossier du projet et tous les fichiers nécessaires."""
   132     print(f"Création du dossier du projet sur votre Bureau : {PROJECT_PATH}")
   133     try:
   134         os.makedirs(PROJECT_PATH, exist_ok=True)
   135     except OSError as e:
   136         print(f"ERREUR: Impossible de créer le dossier. {e}")
   137         return
   138
   139     for filename, content in files_to_create.items():
   140         file_path = os.path.join(PROJECT_PATH, filename)
   141         print(f"  -> Création du fichier : {filename}")
   142         try:
   143             with open(file_path, 'w', encoding='utf-8') as f:
   144                 f.write(textwrap.dedent(content).strip())
   145         except IOError as e:
   146             print(f"ERREUR: Impossible d'écrire dans le fichier {filename}. {e}")
   147             return
   148
   149     print("\\n--- Projet créé avec succès ! ---")
   150     print(f"Le dossier 'Botrecove_V2' est maintenant sur votre Bureau.")
   151     print("\\nProchaines étapes:")
   152     print("1. Ouvrez un terminal (PowerShell).")
   153     print(f"2. Allez dans le dossier avec : cd '{PROJECT_PATH}'")
   154     print("3. Installez les dépendances avec : pip install -r requirements.txt")
   155     print("4. Installez le navigateur avec : playwright install --with-deps chromium")
   156     print("5. Lancez le bot avec : python run.py")
   157
   158 if __name__ == '__main__':
   159     create_project()


  ---

