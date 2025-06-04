def run():
    from datetime import datetime
    import requests
    import json
    import psycopg2.extras
    from typing import Iterator, Dict, Any
    from airflow.hooks.postgres_hook import PostgresHook

    default_args = {
        'owner': 'airflow',
        'depends_on_past': False,
        'retries': 0,
    }

    def parse_date_on_market(text: str) -> datetime.date:
        datetime_obj = datetime.strptime(text, '%Y-%m-%dT%H:%M:%S')
        return datetime_obj.date()

    def create_product_link(id: int):
        return f'https://www.vinbudin.is/heim/vorur/stoek-vara.aspx/?productid={id}'

    def str_to_int(num: str):
        return int(num) if num else 0

    def recreate_staging_table(cursor) -> None:
        cursor.execute("""
            DROP TABLE IF EXISTS landing.sparkling_wines CASCADE; 
            CREATE UNLOGGED TABLE landing.sparkling_wines (
                id                  TEXT,
                name                TEXT,
                volume              DECIMAL,
                abv                 DECIMAL,
                price               DECIMAL,
                country             TEXT,
                origin_place        TEXT,
                origin_district     TEXT,
                grapes              TEXT,
                produced_year       INTEGER,
                container_type      TEXT,
                first_on_market     DATE,
                taste_group         TEXT,
                category            TEXT,
                food_pairing        TEXT,
                producer            TEXT,
                carbon_footprint    DECIMAL,
                closing             TEXT,
                is_organic          TEXT,
                special_order       TEXT,
                link                TEXT,
                batch_id            DATE,
                seller              TEXT
            );
        """)

    def fetch_and_insert_sparkling_wines():
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'Mozilla/5.0',
            'X-Requested-With': 'XMLHttpRequest',
        }

        params = {
            'category': 'bubbly',
            'skip': '0',
            'count': '2000',
            'orderBy': 'random',
        }

        url = 'https://www.vinbudin.is/addons/origo/module/ajaxwebservices/search.asmx/DoSearch'
        response = requests.get(url, params=params, headers=headers)
        data = response.content.decode('utf-8')

        for line in data.splitlines():
            try:
                payload = json.loads(line)
                wine_data = json.loads(payload['d'])
                wines = wine_data['data']
            except Exception as e:
                raise Exception(f"Failed to parse wine data: {e}")

        insert_date = datetime.now().date()

        pg_hook = PostgresHook(postgres_conn_id='postgres_godvinkaup')
        conn = pg_hook.get_conn()
        conn.autocommit = True
        with conn.cursor() as cursor:
            recreate_staging_table(cursor)

            iter_wines = (dict(
                id=wine['ProductID'],
                name=wine['ProductName'],
                volume=wine['ProductBottledVolume'],
                abv=wine['ProductAlchoholVolume'],
                price=wine['ProductPrice'],
                country=wine['ProductCountryOfOrigin'],
                origin_place=wine['ProductPlaceOfOrigin'],
                origin_district=wine['ProductDistrictOfOrigin'],
                grapes=wine['ProductWine'],
                produced_year=str_to_int(wine['ProductYear']),
                container_type=wine['ProductContainerType'],
                first_on_market=parse_date_on_market(wine['ProductDateOnMarket']),
                taste_group=wine['ProductTasteGroup'],
                category='Sparkling Wine',
                food_pairing=wine['ProductFoodCategories'],
                producer=wine['ProductProducer'],
                carbon_footprint=wine['ProductCarbonFootprint'],
                closing=wine['ProductPackagingClosing'],
                is_organic=wine['ProductOrganic'],
                special_order=wine['ProductIsSpecialOrder'],
                link=create_product_link(wine['ProductID']),
                batch_id=insert_date,
                seller='ÁTVR'
            ) for wine in wines)

            psycopg2.extras.execute_batch(cursor, """
                INSERT INTO landing.sparkling_wines VALUES (
                    %(id)s, %(name)s, %(volume)s, %(abv)s, %(price)s, %(country)s, %(origin_place)s,
                    %(origin_district)s, %(grapes)s, %(produced_year)s, %(container_type)s,
                    %(first_on_market)s, %(taste_group)s, %(category)s, %(food_pairing)s,
                    %(producer)s, %(carbon_footprint)s, %(closing)s, %(is_organic)s,
                    %(special_order)s, %(link)s, %(batch_id)s, %(seller)s
                );
            """, iter_wines)


    fetch_and_insert_sparkling_wines()
    print("Scraping done.")
    return True  # <- add this
