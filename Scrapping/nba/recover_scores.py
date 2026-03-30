"""
Recuperar scores faltantes para juegos ya jugados que tienen score=0.

Consulta espn.games para juegos con home_score=0 y fecha pasada,
luego usa la ESPN Summary API para obtener los scores reales.

Uso:
    cd Scrapping/nba
    python recover_scores.py
    python recover_scores.py --dry-run   # solo muestra, no actualiza
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import date

import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config

ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NBA-thesis-scraper/1.0)",
    "Accept": "application/json",
}
SLEEP_BETWEEN = 0.4


def fetch_score(game_id: str) -> dict | None:
    """Obtiene score de un juego via ESPN Summary API."""
    try:
        resp = requests.get(
            ESPN_SUMMARY_URL,
            params={"event": game_id},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ERROR API {game_id}: {e}")
        return None

    try:
        header = data["header"]
        comp = header["competitions"][0]
        comps = comp["competitors"]

        home = next(c for c in comps if c["homeAway"] == "home")
        away = next(c for c in comps if c["homeAway"] == "away")

        status = comp.get("status", {}).get("type", {})
        completed = status.get("completed", False)

        home_score = int(home.get("score") or 0)
        away_score = int(away.get("score") or 0)

        if not completed or home_score == 0:
            return None

        home_win = 1 if home_score > away_score else 0

        return {
            "game_id": game_id,
            "home_score": home_score,
            "away_score": away_score,
            "home_win": home_win,
        }
    except (KeyError, StopIteration, ValueError, TypeError) as e:
        print(f"  ERROR parse {game_id}: {e}")
        return None


def recover_scores(dry_run: bool = False):
    engine = create_engine(db_config.get_database_url())
    schema = db_config.get_schema("espn")

    # Buscar juegos con score=0 y fecha pasada
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT game_id::text, fecha, home_team, away_team
            FROM {schema}.games
            WHERE home_score = 0
              AND fecha < CURRENT_DATE
            ORDER BY fecha
        """)).fetchall()

    print(f"Juegos con score=0 y fecha pasada: {len(rows)}")
    if not rows:
        print("No hay juegos por recuperar.")
        return

    recovered = 0
    failed = 0
    skipped = 0

    for gid, fecha, home, away in rows:
        print(f"  {fecha} | {gid} | {away} @ {home} ... ", end="")
        result = fetch_score(gid)

        if result is None:
            print("SIN DATOS (no completado o sin score)")
            skipped += 1
            time.sleep(SLEEP_BETWEEN)
            continue

        print(f"{result['away_score']}-{result['home_score']} ", end="")

        if dry_run:
            print("[DRY RUN]")
            recovered += 1
            time.sleep(SLEEP_BETWEEN)
            continue

        try:
            with engine.begin() as conn:
                conn.execute(text(f"""
                    UPDATE {schema}.games
                    SET home_score = :hs,
                        away_score = :as_,
                        home_win = :hw
                    WHERE game_id = :gid
                """), {
                    "hs": result["home_score"],
                    "as_": result["away_score"],
                    "hw": result["home_win"],
                    "gid": gid,
                })
            print("OK")
            recovered += 1
        except Exception as e:
            print(f"ERROR DB: {e}")
            failed += 1

        time.sleep(SLEEP_BETWEEN)

    print(f"\nResumen:")
    print(f"  Recuperados: {recovered}")
    print(f"  Sin datos:   {skipped}")
    print(f"  Fallidos:    {failed}")

    # Verificacion final
    with engine.connect() as conn:
        remaining = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM {schema}.games
            WHERE home_score = 0 AND fecha < CURRENT_DATE
        """)).scalar()
    print(f"\n  Juegos restantes con score=0 y fecha pasada: {remaining}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recuperar scores faltantes de ESPN")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no actualizar")
    args = parser.parse_args()
    recover_scores(dry_run=args.dry_run)
