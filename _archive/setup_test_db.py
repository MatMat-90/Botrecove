
import json
import database

ARCHIVED_RESULTS = "_archive/results.jsonl"

def main():
    print("--- Préparation de la base de données de test ---")
    
    # 1. Initialise la BDD avec le schéma v3 (supprime l'ancienne table si elle existe)
    database.init_db()
    
    # 2. Charge les anciennes données
    try:
        with open(ARCHIVED_RESULTS, "r", encoding="utf-8") as f:
            items_data = [json.loads(line) for line in f]
        print(f"{len(items_data)} articles chargés depuis l'archive.")
    except FileNotFoundError:
        print(f"ERREUR: Le fichier d'archive {ARCHIVED_RESULTS} est introuvable.")
        return

    # 3. Insère ces données dans la nouvelle BDD
    new, updated, _ = database.process_items(items_data)
    print(f"Base de données pré-remplie: {new} articles insérés, {updated} mis à jour.")
    print("--- Base de données prête pour le test delta. ---")

if __name__ == "__main__":
    main()
