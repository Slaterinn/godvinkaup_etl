import json
import random
import re
import time
from datetime import datetime
from difflib import SequenceMatcher

import psycopg2
import requests
from bs4 import BeautifulSoup


def run():
    conn = psycopg2.connect(
        host="192.168.86.226",
        port=5433,
        database="godvinkaup",
        user="postgres",
        password="Slater168",
    )
    conn.autocommit = True

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
        "https://www.vivino.com/",
    ]

    def get_random_headers_and_cookies():
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "authority": "www.vivino.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9,is;q=0.8,it;q=0.7,af;q=0.6,la;q=0.5",
            "referer": referer,
            "sec-ch-ua": '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": user_agent,
        }
        cookies = {}
        return headers, cookies

    def insert_bridge_wine(connection, wines):
        with connection.cursor() as cursor:
            insert_query = """
                INSERT INTO marts.wine_ratings_vivino (
                    pk_wine, vivino_id, wine_name, producer, wine_url, rating,
                    rating_count, insert_date, modified_date, image_url,
                    name_score, producer_score, verified
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pk_wine) DO UPDATE SET
                    vivino_id = excluded.vivino_id,
                    wine_name = excluded.wine_name,
                    producer = excluded.producer,
                    wine_url = excluded.wine_url,
                    image_url = excluded.image_url,
                    rating = excluded.rating,
                    rating_count = excluded.rating_count,
                    modified_date = excluded.modified_date;
            """
            cursor.execute(insert_query, wines)

    def clean_wine_name(name, replace_strings):
        for s in replace_strings:
            name = name.replace(s, "")
        return name.strip()

    def fetch_vivino_results(query_name):
        base_url = "https://www.vivino.com/search/wines"
        params = {"q": query_name}

        for attempt in range(3):
            headers, cookies = get_random_headers_and_cookies()
            try:
                response = requests.get(
                    base_url, params=params, headers=headers, cookies=cookies, timeout=10
                )
                time.sleep(random.uniform(1, 3))
                soup = BeautifulSoup(response.content.decode("utf-8"), features="lxml")

                json_block = soup.find("script", type="application/ld+json")
                if not json_block:
                    print(f"Attempt {attempt + 1}: JSON block not found")
                    continue

                json_data = json.loads(json_block.text)
                return json_data

            except Exception as e:
                print(f"Attempt {attempt + 1} failed to fetch/parse JSON: {e}")

        print("❌ All attempts to fetch Vivino data failed.")
        return None

    def score_match(name_lookup, found_name, producer_query, producer_result):
        found_name = re.sub(r"[\(\[].*?[\)\]]", "", found_name)

        match_score_name_1 = SequenceMatcher(None, name_lookup, found_name).ratio()
        match_score_name_2 = SequenceMatcher(
            None, name_lookup, f"{producer_result} {found_name}"
        ).ratio()
        name_score = max(match_score_name_1, match_score_name_2)

        match_score_prod_1 = SequenceMatcher(None, producer_query, producer_result).ratio()
        match_score_prod_2 = SequenceMatcher(None, name_lookup, producer_result).ratio()
        producer_score = max(match_score_prod_1, match_score_prod_2)

        return round(name_score, 3), round(producer_score, 3)

    def select_best_match(json_data, query_name, query_prod):
        best_index = 0
        best_score = 0.0

        for i, result in enumerate(json_data[:6]):
            name = result.get("name", "")
            producer = result.get("manufacturer", {}).get("name", "N/F") or "N/F"

            name_score, prod_score = score_match(query_name, name, query_prod, producer)
            total_score = name_score + prod_score

            print(
                f" Score: {name_score} | Producer Score: {prod_score} | Found: {name} | Producer: {producer}"
            )

            if total_score - best_score > i * 0.05 and total_score > 0.5:
                best_score = total_score
                best_index = i

        if json_data:
            best_result = json_data[best_index]
            name = best_result.get("name", "")
            producer = best_result.get("manufacturer", {}).get("name", "N/F") or "N/F"
            name_score, prod_score = score_match(query_name, name, query_prod, producer)
            return best_result, name_score, prod_score
        return None, None, None

    def process_wine_item(conn, item, replace_strings):
        producer, wine_name, wine_id = item[:3]
        query_name = clean_wine_name(wine_name, replace_strings)

        print(f"🔍 Querying wine: {query_name} | Producer: {producer}")
        json_data = fetch_vivino_results(query_name)
        if not json_data:
            print("No data received from Vivino.")
            return

        best_match, name_score, prod_score = select_best_match(json_data, query_name, producer)
        if not best_match:
            print("❌ No good match found.")
            return

        try:
            result_id = best_match["@id"].split("/")[-1]
            result_name = best_match["name"]
            result_producer = best_match["manufacturer"]["name"]
            result_rating = best_match["aggregateRating"]["ratingValue"]
            result_count = best_match["aggregateRating"]["reviewCount"]
            result_url = best_match["@id"]
            result_image = best_match["image"]
            now = datetime.now()

            result_tuple = (
                wine_id,
                result_id,
                result_name,
                result_producer,
                result_url,
                result_rating,
                result_count,
                now,
                now,
                result_image,
                name_score,
                prod_score,
                None,
            )

            insert_bridge_wine(conn, result_tuple)
            print(f"✅ Inserted: {result_name} (wine_id={wine_id})")

        except Exception as e:
            print("❌ Failed to insert result into database:")
            print(e)

        time.sleep(random.randint(10, 20))  # Be kind to Vivino
        print("----\n")

    # Step 1: Fetch wines that need info
    need_info_sql = """
        SELECT wines.producer, wines.name, wines.id, wines.origin_place
        FROM marts.dim_wines wines
        LEFT JOIN marts.wine_ratings_vivino vivino ON (wines.id = vivino.pk_wine)
        WHERE vivino.pk_wine IS NULL
        LIMIT 15
    """

    need_info_list = []
    with conn.cursor() as cursor:
        cursor.execute(need_info_sql)
        for row in cursor:
            need_info_list.append(row)

    # Step 2: Replacement strings for cleaning
    replace_string_name = ("rautt", "Rautt", "Organic Wine", "Douro", "duoro")

    # Step 3: Process each wine
    for wine in need_info_list:
        process_wine_item(conn, wine, replace_string_name)

    conn.close()
