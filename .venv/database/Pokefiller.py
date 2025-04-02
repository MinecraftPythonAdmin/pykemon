import sqlite3
import requests


def get_pokemon_data():
    url = "https://pokeapi.co/api/v2/pokemon?limit=151"  # Begrenzung auf 10 für Testzwecke
    response = requests.get(url)
    pokemon_list = response.json()["results"]

    data = []
    for pokemon in pokemon_list:
        details = requests.get(pokemon["url"]).json()
        species = requests.get(details["species"]["url"]).json()

        german_name = next((name["name"] for name in species["names"] if name["language"]["name"] == "de"),
                           details["name"])
        height = details["height"]
        weight = details["weight"]
        types = []
        for t in details["types"]:
            type_details = requests.get(t["type"]["url"]).json()
            type_name = next((name["name"] for name in type_details["names"] if name["language"]["name"] == "de"),
                             t["type"]["name"])
            for s in type_details["damage_relations"]["double_damage_to"]:
                types.append((type_name, s["name"], "strong"))
            for w in type_details["damage_relations"]["double_damage_from"]:
                types.append((type_name, w["name"], "weak"))
            for i in type_details["damage_relations"]["no_damage_from"]:
                types.append((type_name, i["name"], "immune"))

        data.append((details["id"], details["name"], german_name, height, weight, types))

    return data


def create_database():
    conn = sqlite3.connect("pokemon.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            german_name TEXT NOT NULL,
            height INTEGER,
            weight INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS type_relations (
            attacker_type_id INTEGER,
            defender_type_id INTEGER,
            effectiveness TEXT CHECK(effectiveness IN ('strong', 'weak', 'immune')),
            PRIMARY KEY (attacker_type_id, defender_type_id),
            FOREIGN KEY (attacker_type_id) REFERENCES types(id) ON DELETE CASCADE,
            FOREIGN KEY (defender_type_id) REFERENCES types(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_types (
            pokemon_id INTEGER,
            type_id INTEGER,
            PRIMARY KEY (pokemon_id, type_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id) ON DELETE CASCADE,
            FOREIGN KEY (type_id) REFERENCES types(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def insert_pokemon_data():
    data = get_pokemon_data()
    conn = sqlite3.connect("pokemon.db")
    cursor = conn.cursor()

    for poke_id, name, german_name, height, weight, types in data:
        cursor.execute("INSERT OR IGNORE INTO pokemon (id, name, german_name, height, weight) VALUES (?, ?, ?, ?, ?)",
                       (poke_id, name, german_name, height, weight))

        for type_name, related_type, effectiveness in types:
            cursor.execute("INSERT OR IGNORE INTO types (name) VALUES (?)", (type_name,))
            cursor.execute("INSERT OR IGNORE INTO types (name) VALUES (?)", (related_type,))
            cursor.execute(
                "INSERT OR IGNORE INTO pokemon_types (pokemon_id, type_id) VALUES (?, (SELECT id FROM types WHERE name = ?))",
                (poke_id, type_name))

            cursor.execute("""
                INSERT OR IGNORE INTO type_relations (attacker_type_id, defender_type_id, effectiveness)
                VALUES (
                    (SELECT id FROM types WHERE name = ?),
                    (SELECT id FROM types WHERE name = ?),
                    ?
                )
            """, (type_name, related_type, effectiveness))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    insert_pokemon_data()
    print("Datenbank erfolgreich gefüllt!")