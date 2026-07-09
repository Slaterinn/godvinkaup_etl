import re
from datetime import datetime

import requests
from airflow.providers.postgres.hooks.postgres import PostgresHook

# Get current date for batch_id
insert_date = datetime.now()

# WooCommerce API endpoint
API_URL = "https://uvavino.is/wp-json/wc/store/products"


def fetch_all_products():
    products = []
    page = 1

    while True:
        response = requests.get(API_URL, params={"page": page, "per_page": 100})
        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        products.extend(data)
        page += 1

    print(f"Fetched {len(products)} products.")
    return products


def extract_attribute(attributes, valid_ids):
    for attr in attributes:
        if attr["id"] in valid_ids and attr["terms"]:
            return attr["terms"][0]["name"]
    return None


def extract_from_tags(tags, valid_ids):
    for tag in tags:
        if tag["id"] in valid_ids:
            return tag["name"]
    return None


def should_skip_product(categories):
    return any(cat["id"] in (572, 598) for cat in categories)


def should_skip_by_name(name, skip_strings):
    return any(skip_str.lower() in name.lower() for skip_str in skip_strings)


def extract_wine_type(attributes, tags, categories):
    wine_type = extract_attribute(attributes, [15])
    if wine_type:
        return wine_type
    wine_type_from_tags = extract_from_tags(tags, [42, 43, 44, 45, 353])
    if wine_type_from_tags:
        return wine_type_from_tags
    for category in categories:
        if category["id"] in [62, 61, 60, 59, 58]:
            return category["name"]
    return None


def concatenate_terms(attribute_list, target_ids):
    for attribute in attribute_list:
        if attribute["id"] in target_ids:
            terms = [term["name"] for term in attribute["terms"]]
            return ", ".join(terms)
    return None


def extract_size(name):
    ml_match = re.search(r"(\d+)\s*ml", name, re.IGNORECASE)
    if ml_match:
        return int(ml_match.group(1))
    cl_match = re.search(r"(\d+)\s*cl", name, re.IGNORECASE)
    if cl_match:
        return int(cl_match.group(1)) * 10
    return 750


def extract_year(name):
    year_match = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", name)
    return int(year_match.group(1)) if year_match else None


def run():
    skip_strings = ["kassa", "kassi"]
    products = fetch_all_products()

    pg_hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        DROP TABLE IF EXISTS landing.uva_wines;
        CREATE TABLE IF NOT EXISTS landing.uva_wines (
            id SERIAL PRIMARY KEY,
            wine_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price NUMERIC,
            producer TEXT,
            area TEXT,
            origin_district TEXT,
            origin_place TEXT,
            country TEXT,
            wine_type TEXT,
            food_pairings TEXT,
            grapes TEXT,
            size INTEGER,
            year INTEGER,
            link TEXT,
            batch_id TIMESTAMP
        );
    """)
    conn.commit()

    for product in products:
        if should_skip_product(product.get("categories", [])) or should_skip_by_name(
            product["name"], skip_strings
        ):
            continue

        wine_id = "UVA" + str(product["id"])
        name = product["name"]
        price = product["prices"]["price"]
        attributes = product.get("attributes", [])
        categories = product.get("categories", [])
        link = product.get("permalink", "")
        tags = product.get("tags", [])
        size = extract_size(name)
        year = extract_year(name)

        producer = extract_attribute(attributes, [13, 116]) or extract_from_tags(tags, [721])
        area = extract_attribute(attributes, [14]) or extract_from_tags(tags, [188])
        country = extract_attribute(attributes, [12]) or extract_from_tags(tags, [111])
        wine_type = extract_wine_type(attributes, tags, categories)
        food_pairings = concatenate_terms(attributes, [9])
        grapes = concatenate_terms(attributes, [7]) or extract_from_tags(tags, [116])

        origin_district = origin_place = None
        if area:
            parts = [part.strip() for part in area.split("/")]
            if len(parts) == 3:
                origin_district, _, origin_place = parts
            elif len(parts) == 2:
                origin_district, origin_place = parts
            elif len(parts) == 1:
                origin_district = origin_place = parts[0]

        if grapes:
            grapes = grapes.strip()

        cursor.execute(
            """
            INSERT INTO landing.uva_wines (
                wine_id, name, price, producer, area, origin_district, origin_place,
                country, wine_type, food_pairings, grapes, size, year, link, batch_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                wine_id,
                name,
                price,
                producer,
                area,
                origin_district,
                origin_place,
                country,
                wine_type,
                food_pairings,
                grapes,
                size,
                year,
                link,
                insert_date,
            ),
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("Data successfully inserted into PostgreSQL.")
