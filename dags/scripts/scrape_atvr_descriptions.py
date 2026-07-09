# scripts/scrape_descriptions.py

import random
import time

import requests
from airflow.hooks.postgres_hook import PostgresHook
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://search.yahoo.com/",
    "https://www.duckduckgo.com/",
    "https://www.vinbudin.is/heim/vorur/vorur.aspx/?category=red",
]


def get_random_headers_and_cookies():
    user_agent = random.choice(USER_AGENTS)
    referer = random.choice(REFERERS)
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "is,en-US;q=0.9,en;q=0.8,it;q=0.7,af;q=0.6,la;q=0.5,no;q=0.4",
        "User-Agent": user_agent,
        "referer": referer,
    }
    cookies = {}
    return headers, cookies


def insert_atvr_description(connection, wine_id, description):
    with connection.cursor() as cursor:
        insert_query = """
            INSERT INTO landing.atvr_wine_descriptions (
                wine_id, description
            )
            VALUES (%s, %s)
            ON CONFLICT (wine_id) DO UPDATE SET
                description = EXCLUDED.description;
        """
        cursor.execute(insert_query, (wine_id, description))


def fetch_atvr_description(link):
    for attempt in range(3):
        try:
            headers, cookies = get_random_headers_and_cookies()
            response = requests.get(link, headers=headers, cookies=cookies, timeout=10)
            time.sleep(random.uniform(1, 3))
            soup = BeautifulSoup(response.content.decode("utf-8"), features="lxml")

            span = soup.find("span", id="ctl00_ctl01_Label_ProductDescription")
            if span:
                paragraphs = span.find_all("p")
                if paragraphs:
                    text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
                else:
                    text = span.get_text(separator=" ", strip=True)
                cleaned = text.replace("Sjá meira.", "").strip()
                cleaned = text.replace("Sjá meira", "").strip()
                if cleaned:
                    return cleaned

            meta_tag = soup.find("meta", property="og:description")
            if meta_tag and meta_tag.get("content"):
                cleaned = meta_tag["content"].replace("Sjá meira.", "").strip()
                if cleaned:
                    return cleaned

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")

    print("❌ All attempts to fetch description failed.")
    return None


def process_wine_item(conn, item):
    wine_id, wine_name, wine_link = item[:3]
    print(f"🔍 Querying wine: {wine_name} | wine_id: {wine_id} | wine_link: {wine_link}")
    description = fetch_atvr_description(wine_link)

    if description:
        insert_atvr_description(conn, wine_id, description)
        print(f"✅ Inserted description for wine_id {wine_id}")
    else:
        insert_atvr_description(conn, wine_id, "N/F")
        print(f"⚠️ No description found for wine_id {wine_id}")


def run():
    pg_hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = pg_hook.get_conn()

    need_info_sql = """
        SELECT wine_id, wine_name, link from
        (
        SELECT wines.id as wine_id, wines.name as wine_name, coalesce(links.link, wines.link) as link
        FROM landing.red_wines wines
        LEFT JOIN landing.atvr_wine_links links ON wines.id = links.wine_id
        LEFT JOIN landing.atvr_wine_descriptions descriptions ON wines.id = descriptions.wine_id
        WHERE descriptions.wine_id IS NULL

        UNION

        SELECT wines.id as wine_id, wines.name as wine_name, coalesce(links.link, wines.link) as link
        FROM landing.white_wines wines
        LEFT JOIN landing.atvr_wine_links links ON wines.id = links.wine_id
        LEFT JOIN landing.atvr_wine_descriptions descriptions ON wines.id = descriptions.wine_id
        WHERE descriptions.wine_id IS NULL

        UNION

        SELECT wines.id as wine_id, wines.name as wine_name, coalesce(links.link, wines.link) as link
        FROM landing.rose_wines wines
        LEFT JOIN landing.atvr_wine_links links ON wines.id = links.wine_id
        LEFT JOIN landing.atvr_wine_descriptions descriptions ON wines.id = descriptions.wine_id
        WHERE descriptions.wine_id IS NULL

        UNION

        SELECT wines.id as wine_id, wines.name as wine_name, coalesce(links.link, wines.link) as link
        FROM landing.sparkling_wines wines
        LEFT JOIN landing.atvr_wine_links links ON wines.id = links.wine_id
        LEFT JOIN landing.atvr_wine_descriptions descriptions ON wines.id = descriptions.wine_id
        WHERE descriptions.wine_id IS NULL
        ) t1
    """

    with conn.cursor() as cursor:
        cursor.execute(need_info_sql)
        need_info_list = cursor.fetchall()

    print(f"🔎 Found {len(need_info_list)} wines missing description.")
    for wine in need_info_list:
        process_wine_item(conn, wine)

    conn.close()
