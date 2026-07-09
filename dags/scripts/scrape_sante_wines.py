import datetime
import re
import unicodedata

import psycopg2
import requests

# Database connection
connection = psycopg2.connect(
    host="192.168.86.226",
    port="5433",
    database="godvinkaup",
    user="postgres",
    password="postgres",
)
connection.autocommit = True

insert_date = datetime.date.today()
currentYear = insert_date.year

# Map of known regions to countries
wine_country_map = {
    # Argentína
    "Mendoza": "Argentína",
    # Ástralía
    "Barossa": "Ástralía",
    "Tasmania": "Ástralía",
    # Frakkland
    "Bordeaux": "Frakkland",
    "Bourgogne": "Frakkland",
    "Castillon": "Frakkland",
    "Chateau": "Frakkland",
    "Champagne": "Frakkland",
    "Drappier": "Frakkland",
    "Provence": "Frakkland",
    "Saint-Emilion": "Frakkland",
    # Ítalía
    "Barbera": "Ítalía",
    "Barolo": "Ítalía",
    "Chianti": "Ítalía",
    "Nebbiolo": "Ítalía",
    "Piedmont": "Ítalía",
    "Sicily": "Ítalía",
    "Tuscany": "Ítalía",
    # Nýja-Sjáland
    "Marlborough": "Nýja-Sjáland",
    # Spánn
    "Alejairen": "Spánn",
    "Cava": "Spánn",
    "Izadi": "Spánn",
    "Rioja": "Spánn",
    # USA
    "Napa": "USA",
    "Sonoma": "USA",
}


def normalize_str(s):
    """Return lowercase ASCII representation of the string"""
    return (
        unicodedata.normalize("NFKD", s.strip()).encode("ASCII", "ignore").decode("ASCII").lower()
    )


def strip_html_tags(text):
    # remove all HTML tags
    return re.sub(r"<[^>]+>", "", text).strip()


def recreate_staging_table(cursor) -> None:
    cursor.execute("""
        DROP TABLE IF EXISTS landing.sante_wines CASCADE; 
        CREATE UNLOGGED TABLE landing.sante_wines (
            id                      TEXT,
            name                    TEXT,
            produced_year           INTEGER,
            producer                TEXT,
            type                    TEXT,
            price                   DECIMAL,
            size                    INT,
            available               TEXT,
            product_url             TEXT,
            image_url               TEXT,
            first_sale_date         DATE,
            country                 TEXT,
            area                    TEXT,
            grapes                  TEXT,
            description		    TEXT,
            district                TEXT,
            batch_date              DATE
        );
    """)


def insert_wines(connection, wines) -> None:
    insert_query = """INSERT INTO landing.sante_wines 
    (id, name, produced_year, producer, type, price, size, available, product_url, image_url, first_sale_date, country, area, grapes, description, district, batch_date)
    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

    with connection.cursor() as cursor:
        cursor.executemany(insert_query, wines)


def get_filter_values(connection, filter_name) -> list:
    op = "LIKE" if "%" in filter_name else "="
    query = f"SELECT filter_value FROM landing.sante_wine_filters WHERE filter_key {op} %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (filter_name,))
        result = cursor.fetchall()
        return [item[0] for item in result]


def run():
    with connection.cursor() as cursor:
        recreate_staging_table(cursor)

    country_list = get_filter_values(connection, "upprunaland")
    area_list = get_filter_values(connection, "herad")
    grapes_list = get_filter_values(connection, "thrug%")
    district_list = get_filter_values(connection, "thorp")

    link = "https://sante.is/collections/lettvin/products.json?limit=1000"
    raw_data = requests.get(link)
    data = raw_data.json()["products"]
    link_prefix = "https://sante.is/products/"

    wines_to_insert = []

    for product in data:
        pid = product["id"]
        title_raw = product["title"]
        cl_pos = title_raw.find("cl.")
        if cl_pos != -1:
            find_rspace = title_raw[: cl_pos - 1].rfind(" ")
            title = title_raw[:find_rspace]
        else:
            title = title_raw

        producer = product["vendor"]
        wine_type = product["product_type"]
        images = product.get("images")
        if images and len(images) > 0 and "src" in images[0]:
            image_url = images[0]["src"]
        else:
            image_url = ""
        created_at = product["created_at"]

        product_price = product["variants"][0]["price"]
        product_available = product["variants"][0]["available"]

        product_handle = product["handle"]
        product_url = link_prefix + product_handle

        if product["body_html"]:
            description = product["body_html"]
            description_clean = strip_html_tags(description)

        tags = product["tags"]

        # Produced year
        produced_year = 0
        year_match = re.match(r"^(\d{4})", title_raw)
        if year_match:
            produced_year = int(year_match.group(1))
        else:
            for tag in tags:
                try:
                    possible_year = int(tag)
                    if currentYear - possible_year < 30:
                        produced_year = possible_year
                except ValueError:
                    continue

        # Size in ml — check title first
        product_size = 0

        # Try to extract ml from title (e.g. "375ml")
        ml_match = re.search(r"(\d{2,4})\s?ml", title_raw.lower())
        if ml_match:
            product_size = int(ml_match.group(1))
        else:
            # Try to extract cl from tags (e.g. "75 cl" → 750ml)
            for tag in tags:
                tag_lower = tag.lower()
                if "cl" in tag_lower:
                    cl_match = re.search(r"([\d.]+)\s*cl", tag_lower)
                    if cl_match:
                        product_size = int(float(cl_match.group(1)) * 10)
                        break

        # Country
        country = next((tag for tag in tags if tag in country_list), "N/F")
        if country == "N/F":
            title_lower = title_raw.lower()
            for region, inferred_country in wine_country_map.items():
                if region.lower() in title_lower:
                    country = inferred_country
                    break

        area = next((tag for tag in tags if tag in area_list), "N/F")

        # Normalized grape matching
        normalized_tags = [normalize_str(tag) for tag in tags]
        normalized_grapes = {normalize_str(grape): grape for grape in grapes_list}
        grapes_l = [
            normalized_grapes[n_tag] for n_tag in normalized_tags if n_tag in normalized_grapes
        ]
        grapes = ",".join(grapes_l)

        district = next((tag for tag in tags if tag in district_list), "N/F")

        result = (
            pid,
            title,
            produced_year,
            producer,
            wine_type,
            product_price,
            product_size,
            product_available,
            product_url,
            image_url,
            created_at,
            country,
            area,
            grapes,
            description_clean,
            district,
            insert_date,
        )
        wines_to_insert.append(result)

    try:
        insert_wines(connection, wines_to_insert)
        print(f"{len(wines_to_insert)} wines added to landing.sante_wines")
    except Exception as e:
        print("Error inserting into landing table:", e)


if __name__ == "__main__":
    run()
