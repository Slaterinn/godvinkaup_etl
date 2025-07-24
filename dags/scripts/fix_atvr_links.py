from airflow.hooks.postgres_hook import PostgresHook
import psycopg2.extras
import requests
from time import sleep
from random import uniform

def generate_link_variants(wine_id: str):
    """Generate potential padded versions of the wine_id (e.g., 2057 -> 02057, 002057)."""
    wine_id_int = int(wine_id)
    variants = [
        str(wine_id_int),             # original, unpadded
        str(wine_id_int).zfill(5),    # e.g. 02057
        str(wine_id_int).zfill(4),    # e.g. 2057
    ]
    return list(dict.fromkeys(variants))  # remove duplicates while preserving order

def check_link(session, link):
    """Return True if the link returns HTTP 200 status, else False."""
    try:
        resp = session.head(link, allow_redirects=True, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False

def fix_missing_links(pg_conn):
    with pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        # 1. Get wine IDs from all landing tables with short IDs (<5 chars)
        cursor.execute('''
            SELECT DISTINCT id FROM (
                SELECT id FROM landing.red_wines WHERE LENGTH(id) < 5
                UNION
                SELECT id FROM landing.white_wines WHERE LENGTH(id) < 5
                UNION
                SELECT id FROM landing.rose_wines WHERE LENGTH(id) < 5
                UNION
                SELECT id FROM landing.sparkling_wines WHERE LENGTH(id) < 5
            ) t;
        ''')
        all_wines = {row['id'] for row in cursor.fetchall()}

        # 2. Get existing wine_id in landing.atvr_wine_links
        cursor.execute("SELECT wine_id FROM landing.atvr_wine_links;")
        existing_links = {row['wine_id'] for row in cursor.fetchall()}

        # 3. Identify which wines need links
        missing_wines = all_wines - existing_links
        print(f"🔍 Found {len(missing_wines)} wines missing links.")

        session = requests.Session()
        base_url_template = "https://www.vinbudin.is/heim/vorur/stoek-vara.aspx/?productid={}"

        links_to_insert = []

        for wine_id in missing_wines:
            found_link = None
            variants = generate_link_variants(wine_id)

            for variant in variants:
                test_link = base_url_template.format(variant)
                if check_link(session, test_link):
                    found_link = test_link
                    print(f"✔ Found valid link for wine_id {wine_id}: {found_link}")
                    break
                sleep(uniform(0.1, 0.3))  # polite delay

            if not found_link:
                print(f"❌ No valid link found for wine_id {wine_id}, storing as 'N/F'")
                found_link = 'N/F'

            links_to_insert.append((wine_id, found_link))

        # 4. Insert discovered links into the target table
        insert_query = """
            INSERT INTO landing.atvr_wine_links (wine_id, link)
            VALUES (%s, %s)
            ON CONFLICT (wine_id) DO NOTHING;
        """
        psycopg2.extras.execute_batch(cursor, insert_query, links_to_insert)
        print(f"✅ Inserted {len(links_to_insert)} new links.")

def run():
    # Use Airflow's PostgresHook to get a DB-API connection
    hook = PostgresHook(postgres_conn_id='postgres_godvinkaup')
    pg_conn = hook.get_conn()
    pg_conn.autocommit = True

    try:
        fix_missing_links(pg_conn)
    finally:
        pg_conn.close()

if __name__ == "__main__":
    run()
