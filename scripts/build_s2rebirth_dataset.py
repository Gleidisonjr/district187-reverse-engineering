import os
import sys
import ssl
import json
import sqlite3
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://s2rebirth.com/veri'
DATA_DIR = os.path.abspath(r'targets/district-187/data')
RAW_DIR = os.path.join(DATA_DIR, 'raw_portal')
DB_PATH = os.path.join(DATA_DIR, 's2rebirth.db')

os.makedirs(RAW_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_json(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    local_path = os.path.join(RAW_DIR, endpoint)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"[*] Downloading {url}...")
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        content = resp.read()
        with open(local_path, 'wb') as f:
            f.write(content)
        return json.loads(content.decode('utf-8'))

def build_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Schema creation
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weapons (
        group_id INTEGER PRIMARY KEY,
        name TEXT,
        dev_name TEXT,
        slot TEXT,
        class TEXT,
        damage INTEGER,
        recoil INTEGER,
        fire_delay INTEGER,
        accuracy INTEGER,
        range INTEGER,
        magazine INTEGER,
        mobility INTEGER,
        gamedb_record TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items_all (
        group_id INTEGER PRIMARY KEY,
        name TEXT,
        dev_name TEXT,
        type TEXT,
        slot TEXT,
        class TEXT,
        icon_path TEXT,
        gamedb_record TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ranks (
        level INTEGER PRIMARY KEY,
        name TEXT,
        text_key TEXT,
        min_xp INTEGER,
        max_xp INTEGER
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS maps (
        id INTEGER PRIMARY KEY,
        name TEXT,
        dev_name TEXT,
        modes TEXT,
        world_file TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS titles (
        index_id INTEGER PRIMARY KEY,
        name TEXT,
        text_key TEXT,
        color TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY,
        group_id INTEGER,
        name TEXT,
        price INTEGER,
        is_cash BOOLEAN,
        is_package BOOLEAN
    )""")

    # 1. Weapons & Items
    esyalar_data = fetch_json('esyalar.json')
    items = esyalar_data.get('esyalar', [])
    weapons_rows = []
    items_rows = []

    for item in items:
        gid = item.get('grup')
        name = item.get('ad')
        dev_name = item.get('gelistiriciAd')
        typ = item.get('tip')
        slot = item.get('slot')
        cls = item.get('sinif')
        gamedb = item.get('gamdbKaydi')
        icon = item.get('ikon', {}).get('yol') if isinstance(item.get('ikon'), dict) else None

        items_rows.append((gid, name, dev_name, typ, slot, cls, icon, gamedb))

        silah = item.get('silah')
        if silah and isinstance(silah, dict):
            weapons_rows.append((
                gid, name, dev_name, slot, cls,
                silah.get('hasar'),
                silah.get('geriTepme'),
                silah.get('atisGecikmesi'),
                silah.get('isabet'),
                silah.get('menzil'),
                silah.get('sarjor'),
                silah.get('tasima'),
                gamedb
            ))

    cur.executemany("INSERT OR REPLACE INTO items_all VALUES (?,?,?,?,?,?,?,?)", items_rows)
    cur.executemany("INSERT OR REPLACE INTO weapons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", weapons_rows)
    print(f"[+] Loaded {len(items_rows)} items ({len(weapons_rows)} weapons with full combat stats).")

    # 2. Ranks
    rutbeler_data = fetch_json('rutbeler.json')
    ranks_rows = [
        (r.get('seviye'), r.get('ad'), r.get('metinAnahtari'), r.get('altSinir'), r.get('ustSinir'))
        for r in rutbeler_data.get('rutbeler', [])
    ]
    cur.executemany("INSERT OR REPLACE INTO ranks VALUES (?,?,?,?,?)", ranks_rows)
    print(f"[+] Loaded {len(ranks_rows)} military ranks/progression tiers.")

    # 3. Maps
    haritalar_data = fetch_json('haritalar.json')
    maps_rows = [
        (m.get('id'), m.get('ad'), m.get('gelistiriciAd'), ", ".join(m.get('modlar', [])), m.get('dunyaDosyasi'))
        for m in haritalar_data.get('haritalar', [])
    ]
    cur.executemany("INSERT OR REPLACE INTO maps VALUES (?,?,?,?,?)", maps_rows)
    print(f"[+] Loaded {len(maps_rows)} maps and game worlds.")

    # 4. Titles
    unvanlar_data = fetch_json('unvanlar.json')
    titles_rows = [
        (t.get('indeks'), t.get('ad'), t.get('metinAnahtari'), t.get('renk'))
        for t in unvanlar_data.get('unvanlar', [])
    ]
    cur.executemany("INSERT OR REPLACE INTO titles VALUES (?,?,?,?)", titles_rows)
    print(f"[+] Loaded {len(titles_rows)} player titles.")

    # 5. Shop
    magaza_data = fetch_json('magaza.json')
    shop_rows = [
        (u.get('id'), u.get('grup'), u.get('ad'), u.get('fiyat'), bool(u.get('nakit')), bool(u.get('paket')))
        for u in magaza_data.get('urunler', [])
    ]
    cur.executemany("INSERT OR REPLACE INTO shop_items VALUES (?,?,?,?,?,?)", shop_rows)
    print(f"[+] Loaded {len(shop_rows)} store catalog items.")

    conn.commit()

    # Analytical Queries
    print("\n" + "="*50)
    print("=== SUMMARY ANALYTICS (SQLite) ===")
    print("="*50)

    cur.execute("SELECT class, COUNT(*), ROUND(AVG(damage),1), ROUND(AVG(fire_delay),1), ROUND(AVG(recoil),1) FROM weapons WHERE damage IS NOT NULL GROUP BY class ORDER BY COUNT(*) DESC")
    print(f"\n{'Class':<10} | {'Count':<6} | {'Avg Dmg':<8} | {'Avg Delay':<10} | {'Avg Recoil':<10}")
    print("-" * 52)
    for row in cur.fetchall():
        cls = row[0] or 'Other'
        print(f"{cls:<10} | {row[1]:<6} | {row[2]:<8} | {row[3]:<10} | {row[4]:<10}")

    cur.execute("SELECT name, class, damage, range, accuracy, recoil FROM weapons ORDER BY damage DESC LIMIT 5")
    print("\nTop 5 Highest Damage Weapons:")
    for row in cur.fetchall():
        print(f"  - {row[0]} ({row[1]}): Dmg {row[2]}, Range {row[3]}, Acc {row[4]}, Recoil {row[5]}")

    conn.close()
    print(f"\n[+] Database created successfully at: {DB_PATH}")

if __name__ == '__main__':
    build_database()
