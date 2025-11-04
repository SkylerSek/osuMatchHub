import requests
import psycopg2
from psycopg2 import sql
from collections import defaultdict
from dotenv import load_dotenv
import json
import os
from time import sleep

# === Load config file ===
def load_config(path="config.json"):
    ## Load configuration from .env first, then fallback to config.json if present.
    load_dotenv()
    config = {}
    CLIENT_ID = os.getenv("OSU_CLIENT_ID")
    CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
    if CLIENT_ID and CLIENT_SECRET:
        config["osu"] = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    elif os.path.exists(path):
        with open(path, "r") as f:
            config = json.load(f)
    else:
        raise FileNotFoundError("⚠️ Missing both .env and config.json — please provide one.")
    return config

load_dotenv()
config = load_config()
CLIENT_ID = os.getenv("OSU_CLIENT_ID")
CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
# Extract values
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "osu_data"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST") or "localhost",
    "port": os.getenv("DB_PORT", "5432")
}
print("DB_CONFIG:", DB_CONFIG)

def test_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print(f"✅ Successfully connected to database '{DB_CONFIG['dbname']}' at host '{DB_CONFIG['host']}'")
    except Exception as e:
        print(f"❌ Failed to connect to database. Check your DB_CONFIG and environment variables.")
        print("Error:", e)

test_db_connection()

def get_osu_token():
    """
    Get OAuth token for osu! API v2
    """
    url = "https://osu.ppy.sh/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "public"
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        return r.json()["access_token"]
    except requests.RequestException as e:
        print("❌ Failed to get osu! token:", e)
        return None

def get_match_data(match_id, token):
    """
    Fetch JSON match data from osu! API v2
    """
    url = f"https://osu.ppy.sh/api/v2/matches/{match_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 404:
            print(f"⚠️ Match {match_id} not found (404). Skipping.")
            return None
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        print(f"⏳ Timeout fetching match {match_id}. Skipping.")
        return None
    except requests.RequestException as e:
        print(f"❌ Error fetching match {match_id}: {e}")
        return None


def parse_match_data(data):
    """
    Convert raw osu! match JSON into a {player: {beatmap_id: score}} structure.
    """
    user_lookup = {str(u["id"]): u["username"] for u in data.get("users", [])}
    player_scores = defaultdict(dict)

    for event in data["events"]:
        game = event.get("game")
        if not game:
            continue

        beatmap = game.get("beatmap")
        beatmap_id = str(beatmap["id"]) if beatmap else None

        for score in game.get("scores", []):
            user_id = str(score["user_id"])
            username = user_lookup.get(user_id, f"User {user_id}")
            player_scores[username][beatmap_id] = score["score"]

    return player_scores

def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                player_name TEXT NOT NULL,
                beatmap_id BIGINT NOT NULL,
                score INT,
                match_id BIGINT,
                UNIQUE(player_name, beatmap_id, match_id)
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database ready")
    except Exception as e:
        print("❌ Failed to prepare database:", e)

def ensure_database_exists():
    """Create the osu_data database if it doesn't exist."""
    try:
        psycopg2.connect(**DB_CONFIG).close()
        print("✅ Database " + os.getenv("DB_NAME") + " already exists.")
    except psycopg2.OperationalError:
        print("⚙️  osu_data database not found — creating it now...")
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_CONFIG["dbname"])))
        cur.close()
        conn.close()
        print("✅ Database osu_data created successfully!")

def insert_scores(match_id, player_scores):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for player, beatmaps in player_scores.items():
        for beatmap_id, score in beatmaps.items():
            cur.execute("""
                INSERT INTO scores (player_name, beatmap_id, score, match_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_name, beatmap_id, match_id)
                DO UPDATE SET score = EXCLUDED.score;
            """, (player, beatmap_id, score, match_id))
    conn.commit()
    cur.close()
    conn.close()

def main():
    """
    Standalone script entry point for fetching and storing osu! match data.
    Users can input a match ID manually, or the script can be imported for use in Flask.
    """
    ensure_database_exists()
    init_db()

    token = get_osu_token()
    if not token:
        print("❌ Cannot continue without a valid osu! token.")
        return

    # Prompt user for a match ID
    match_id = input("Enter the osu! match ID to fetch: ").strip()
    if not match_id.isdigit():
        print("⚠️ Invalid match ID. Must be a number.")
        return

    data = get_match_data(match_id, token)
    if not data:
        print(f"⚠️ Could not fetch match {match_id}.")
        return

    table = parse_match_data(data)

    match_name = data.get("match", {}).get("name", f"Match {match_id}")
    print(f"Inserting data for match: {match_name} ...")
    insert_scores(match_id, table)
    print("✅ Data inserted successfully!")
    print("DB_CONFIG:", DB_CONFIG)


if __name__ == "__main__":
    main()
