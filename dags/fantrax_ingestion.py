from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from scripts.fantrax.fantrax_league_table import load_fantrax_league_table
from scripts.fantrax.fantrax_players import load_fantrax_players
from scripts.fantrax.fantrax_player_scores import load_fantrax_player_scores
from scripts.fantrax.fantrax_player_minutes import load_fantrax_player_minutes
from scripts.fantrax.fantrax_player_service import load_fantrax_player_service

# -------------------------------------------------------------------
# Fantrax session auth (TEMPORARY)
# Later: move to Airflow Variables or a secrets backend
# -------------------------------------------------------------------

FANTRAX_HEADERS = {
    'accept': 'application/json',
    'accept-language': 'is,en-US;q=0.9,en;q=0.8,it;q=0.7,af;q=0.6,la;q=0.5,no;q=0.4',
    'content-type': 'text/plain',
    'origin': 'https://www.fantrax.com',
    'priority': 'u=1, i',
    'referer': 'https://www.fantrax.com/fantasy/league/41hpiiy9mbujpnmu/players;positionOrGroup=ALL;miscDisplayType=1;pageNumber=1',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

FANTRAX_COOKIES = {
    '_ga': 'GA1.2.993606395.1745399994',
    'uig': '5r8lv2tlm9tq3ayw',
    'ui': '5r8lv2tlm9tq3ayw',
    'FX_RM': '_qpxzAl4RUFJUEBIPGRVfAFYBDgUVUQ8WDloaBxYTGQsFCkA=',
    'consentUUID': '682fb5e7-1d8f-4c69-b44a-1d0ff4347388_44',
    'consentDate': '2025-05-19T21:02:38.924Z',
    'usnatUUID': '7f1be112-903a-4213-a1e8-6ff6647e8b71',
    '_cc_id': '92dde877ec053700543a1f95af0d00fa',
    '_sharedid': '0c38ae48-6323-4d40-8a65-d1762907bc9f',
    'usprivacy': '1---',
    '_sharedid_cst': 'kyw7LIcsqA%3D%3D',
    'cto_bundle': 'TD8wDl9oJTJCempjOXVSTU1NOVIzQkZBRzdKb1RqS0glMkZwa2lsb2ZEd1B5UlRTVUVGcnhpWDlWZnpDdU96SjR6ckRtWmh4eFpPaVI2V1kzTFZ3S3klMkJyM050U0xxZEpOZ3BQdVJVaWwzZU5aa1JTSTlnVnRhTzhyRDhBMVF5RWVYRDl2UE1UemJWWU1TUXBBJTJCTlE4N3QwTHh4N29DUSUzRCUzRA',
    'cto_bidid': '87D4N19jJTJGN1RWNVRqWDNQTyUyQkR5ZUFvRTFrcyUyQjhiRzkySHpqUVphSEFMNUdKR1E2QXFqZXpqRHpaUnNNJTJCQlQzTDAxaTZLMjI2Z2d0aU5tUUtzejclMkJFSHJ3c0ZJSUtkdll3JTJGYVVQYk5uYVNOUSUyQkN3JTNE',
    '__gads': 'ID=71597e4a92b80193:T=1747688560:RT=1758463909:S=ALNI_MYcX5_GFLz1cYI4Id1tDquCGdQroQ',
    '__gpi': 'UID=000010bc336f3d1f:T=1747688560:RT=1758463909:S=ALNI_MYQ-6WvlxKoHYp32PGosK7TBXR1VQ',
    'FCCDCF': '%5Bnull%2Cnull%2Cnull%2C%5B%22CQWI4YAQWI4YAEsACBENB3FoAP_gAEPgACiQK1sB_C5OTWFh8L53QfskeYQH97BgbkAwAgRJg0IBSDoStJwQw2A4AAjSIqAIGRIAqnSBIAEACACERFCAIIAFogBMIECQoDNCIIBECAIBACBQCARoE4NhEQAAgnoEJkQRgBANQVIMWEyASohDknARbCAwAACQAIcICEF0QAISkMAAZGxcpIrICBCBEUgIAlmPBCIpqBBMIhgERAkhwBBAUdgIhEICAIWhAKIAgAEgloK1sB_C5MTXFh8LhXwfskOYQX97AAbkAwAARJg0IBSDoStIwQ02AwAAiSIKQIGRAAonQBIAEACAgERFCBAIAFIgBMAEAQoDNAIMBEACIBACBQAABIA4NhEQABgGoEJEQRgAAMQFIEWEyASIgjknABaKAQAACQCIMAGEFkSAAQgMAA5GRKxIpICICBEQAAAhmPBCIlqFAMohiERIohQBBgUMAIBEACAIWhAKAAgQEgkoAAA.cAAAD_gAAAA%22%2C%222~55.89.108.117.143.149.184.192.211.228.259.272.310.311.313.314.320.358.415.424.442.445.469.486.491.494.495.540.559.584.621.737.803.899.904.979.981.1029.1031.1033.1040.1047.1092.1097.1107.1126.1143.1152.1186.1205.1215.1227.1268.1270.1284.1301.1307.1342.1415.1419.1440.1525.1558.1579.1584.1598.1638.1697.1712.1716.1720.1735.1745.1753.1765.1782.1786.1808.1810.1827.1832.1842.1866.1911.1944.1958.1964.1969.1985.2008.2010.2044.2052.2056.2074.2088.2133.2137.2177.2220.2223.2227.2271.2295.2309.2312.2316.2322.2328.2331.2343.2358.2373.2400.2406.2411.2415.2416.2418.2425.2427.2440.2461.2465.2481.2486.2501.2510.2517.2527.2532.2535.2542.2559.2564.2569.2571.2572.2575.2577.2595.2604.2624.2628.2642.2645.2646.2650.2651.2652.2656.2669.2677.2684.2687.2690.2695.2698.2729.2767.2768.2770.2778.2784.2787.2798.2805.2814.2816.2822.2839.2844.2854.2863.2867.2872.2874.2878.2887.2891.2894.2895.2898.2919.2920.2922.2930.2949.2950.2964.2970.2974.2999.3000.3001.3002.3005.3010.3012.3017.3043.3055.3068.3070.3089.3094.3100.3109.3126.3128.3130.3155.3163.3172.3177.3185.3186.3188.3189.3190.3194.3201.3213.3215.3218.3222.3230.3233.3234.3244.3250.3251.3253.3254.3272.3290.3292.3299.3330.3331.4131.4531.7235.9731.13731.14332.26031.26831.28031.28731.30732.39531.41531~dv.%22%2C%228B6313C1-8BED-4B02-9347-5F894E83AD2D%22%5D%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%229a3c08b5-ebf7-41fc-85ff-32e6bd4cd5be%5C%22%2C%5B1762714196%2C751000000%5D%5D%22%5D%5D%5D',
    '_gid': 'GA1.2.1365061149.1765837850',
    '__cf_bm': 't8gKEIbHXRCqmE5mByI5bpALSL33w4AFlzUjRMXzKYE-1765889767-1.0.1.1-WYgxhVP7mmcTn3pnhkCpG.XMPJ.1vbTDokY8zA77fnbKdAZbthLGiUAhb._7nr.N0OiC3E6LXTw5zhAlEfljad3W7BMWDTGoKyQBQ.o_zus',
    'cf_clearance': 'm51N.gLXimxf_dTjvx0J7b2aWFNCGCPdHZe3SwUUvfA-1765889767-1.2.1.1-GUTy2HovYAZCAcktsw6QTFX6TCdPJlvNOS1funkumZwuV.eSKWq6nx9LRBXm64bpuQMf_iUqkq23z78jMIRQJDuSbx.Gck_cLSrfLpP8U.OVdU3CYiIOZcVZA8MqoZQszDjLS7JGnWUg8P.ySyGJ8jchFG8pIvpO6Ho0YMk26LkaqA6M4x1XhBBlHinX5eztBZ01puWNoe3rfvzPGSVzvgNnQnVdey6GkijUR93NCSA',
    'FCNEC': '%5B%5B%22AKsRol9tXl_c0mMDX1S_dUVE27k5V_h8NqY74G2Nit-5IUeVZPFMeBwvk85eqTblZmpMzQOifR5cbK-00eWDAYkxW-SXJWR8pp5WvLC2TxP-WhcFeQPiUIVx6mQuKPKR7BEwCNUPGbZDDwZI1MxsoydnWTDPzaLHEQ%3D%3D%22%5D%5D',
    '_gat': '1',
    '_ga_DM2Q31JXYV': 'GS2.2.s1765889768$o24$g1$t1765890300$j60$l0$h0',
}




# -------------------------------------------------------------------
# DAG definition
# -------------------------------------------------------------------

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fantrax_ingestion",
    default_args=default_args,
    description="Fantrax data ingestion to Postgres landing schema",
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * 1,4",  # Monday & Thursday at 06:00
    catchup=False,
    tags=["fantrax", "sports"],
) as dag:

    league_table = PythonOperator(
        task_id="load_league_table",
        python_callable=load_fantrax_league_table,
    )

    player_list = PythonOperator(
        task_id="load_player_list",
        python_callable=load_fantrax_players,
        op_kwargs={
            "cookies": FANTRAX_COOKIES,
            "headers": FANTRAX_HEADERS,
        },
    )

    load_scores = PythonOperator(
        task_id="load_player_scores",
        python_callable=load_fantrax_player_scores,
        op_kwargs={
            "cookies": FANTRAX_COOKIES,           # imported or defined in DAG
            "headers": FANTRAX_HEADERS            # imported or defined in DAG
        }
    )

    load_minutes = PythonOperator(
        task_id="load_player_minutes",
        python_callable=load_fantrax_player_minutes,
        op_kwargs={
            "cookies": FANTRAX_COOKIES,           # imported or defined in DAG
            "headers": FANTRAX_HEADERS            # imported or defined in DAG
        }
    )

    load_service = PythonOperator(
        task_id="load_player_service",
        python_callable=load_fantrax_player_service,
        op_kwargs={
            "cookies": FANTRAX_COOKIES,           # imported or defined in DAG
            "headers": FANTRAX_HEADERS            # imported or defined in DAG
        }
    )
# ----------------------------------------------------------------
    # Task dependencies
    # ----------------------------------------------------------------

    league_table >> player_list >> load_scores >> load_minutes >> load_service
