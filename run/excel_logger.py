

import sqlite3
import pandas as pd
from datetime import datetime
import os

def export_to_excel(db_path, excel_path):
    """
    Exporte les données de la base de données SQLite vers un fichier Excel.
    Crée une nouvelle feuille pour chaque exécution et met à jour une feuille de résumé.
    """
    if not os.path.exists(db_path):
        print(f"[Excel Logger] Erreur: La base de données '{db_path}' n'a pas été trouvée.")
        return

    try:
        # Connexion à la base de données et lecture des données
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM items", conn)
        
        if df.empty:
            print("[Excel Logger] La base de données est vide. Aucun rapport Excel n'a été généré.")
            return

        # Nom de la feuille basé sur l'horodatage actuel
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        sheet_name = f"Run_{timestamp}"

        # Calcul des statistiques pour le résumé
        summary_data = {
            'Date Heure': [timestamp],
            'Nom de la Feuille': [sheet_name],
            'Nombre total d'articles': [len(df)],
            'Prix moyen': [df['price'].mean()],
            'Prix median': [df['price'].median()],
            'Articles visibles': [len(df[df['status'] == 'visible'])],
            'Articles réservés': [len(df[df['status'] == 'reservé'])],
            'Articles vendus': [len(df[df['status'] == 'vendu'])]
        }
        summary_df = pd.DataFrame(summary_data)

        # Écriture dans le fichier Excel
        # Utilise le mode 'a' (append) pour ajouter des feuilles, ou 'w' (write) pour créer
        mode = 'a' if os.path.exists(excel_path) else 'w'
        engine = 'openpyxl' if mode == 'a' else None # openpyxl est nécessaire pour l'ajout

        with pd.ExcelWriter(excel_path, engine=engine, mode=mode) as writer:
            # Écrire les données du run dans sa propre feuille
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Mettre à jour la feuille de résumé
            try:
                # Tenter de lire la feuille de résumé existante
                old_summary_df = pd.read_excel(excel_path, sheet_name='Performances_Globales')
                # Concaténer avec les nouvelles données
                new_summary_df = pd.concat([old_summary_df, summary_df], ignore_index=True)
            except FileNotFoundError:
                # Le fichier n'existe pas encore
                new_summary_df = summary_df
            except ValueError:
                # La feuille n'existe pas dans le fichier
                new_summary_df = summary_df

            new_summary_df.to_excel(writer, sheet_name='Performances_Globales', index=False)

        print(f"[Excel Logger] Rapport exporté avec succès. Feuille: '{sheet_name}'. Résumé mis à jour.")

    except Exception as e:
        print(f"[Excel Logger] Une erreur est survenue: {e}")


