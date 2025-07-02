import sqlite3
import json
from datetime import datetime
from threading import Lock

DB_FILE = "vinted.db"
db_lock = Lock()

def init_db():
    """Initialise la base de données et crée la table des articles avec le nouveau schéma."""
    with db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            # La suppression de l'ancienne table assure une transition propre.
            # À commenter si vous souhaitez conserver d'anciennes données manuellement.
            cursor.execute("DROP TABLE IF EXISTS items")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    price REAL,
                    currency TEXT,
                    status TEXT NOT NULL,
                    url TEXT UNIQUE,
                    last_seen DATETIME NOT NULL,
                    last_updated DATETIME NOT NULL,
                    raw_data TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items (status)")
            conn.commit()
    print("[Database] Base de données initialisée avec le schéma pour le scraping incrémental et le mode WAL activé.")

def get_item_status(item):
    """Détermine le statut de l'article à partir des données brutes."""
    if item.get('is_reserved'):
        return 'reservé'
    if not item.get('is_visible'):
        return 'vendu'
    return 'visible'

def process_items(items_data):
    """
    Traite une liste d'articles en utilisant des opérations de base de données par lots (batch)
    pour une performance accrue.
    """
    if not items_data:
        return 0, 0, 0

    now_str = datetime.utcnow().isoformat()
    items_to_insert = []
    items_to_update = []
    items_to_touch = [] # Pour les articles inchangés

    item_ids = [item['id'] for item in items_data if item.get('id')]
    if not item_ids:
        return 0, 0, 0

    with db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, price, status FROM items WHERE id IN ({','.join('?' for _ in item_ids)})", item_ids)
            existing_items = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    for item in items_data:
        item_id = item.get('id')
        if not item_id:
            continue

        current_price = float(item.get('price', {}).get('amount', 0.0))
        current_status = get_item_status(item)
        existing_item = existing_items.get(item_id)

        if existing_item is None:
            items_to_insert.append((
                item_id, item.get('title'), current_price, item.get('price', {}).get('currency'),
                current_status, item.get('url'), now_str, now_str, json.dumps(item)
            ))
        else:
            old_price, old_status = existing_item
            if not abs(old_price - current_price) < 0.001 or old_status != current_status:
                items_to_update.append((
                    current_price, current_status, now_str, now_str, json.dumps(item), item_id
                ))
            else:
                items_to_touch.append((now_str, item_id))

    if items_to_insert or items_to_update or items_to_touch:
        with db_lock:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                if items_to_insert:
                    cursor.executemany(
                        "INSERT INTO items (id, title, price, currency, status, url, last_seen, last_updated, raw_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        items_to_insert
                    )
                if items_to_update:
                    cursor.executemany(
                        "UPDATE items SET price = ?, status = ?, last_seen = ?, last_updated = ?, raw_data = ? WHERE id = ?",
                        items_to_update
                    )
                if items_to_touch:
                    cursor.executemany(
                        "UPDATE items SET last_seen = ? WHERE id = ?",
                        items_to_touch
                    )
                conn.commit()

    return len(items_to_insert), len(items_to_update), len(items_to_touch)