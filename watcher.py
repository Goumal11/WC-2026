"""
FIFA World Cup 2026 — Watcher de scores en direct
===================================================
Source : football-data.org (tier gratuit, 100 req/jour)
Inscription gratuite : https://www.football-data.org/client/register

Après inscription, copie ta clé dans la variable API_KEY ci-dessous
(ou via la variable d'environnement FD_API_KEY pour GitHub Actions).

Usage local :
    python watcher.py              # poll toutes les 60s en continu
    python watcher.py --once       # une seule vérification (mode GitHub Actions)

Usage GitHub Actions : appelé avec --once à chaque cron.

Dépendances :
    pip install requests
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

# Clé API football-data.org
# → Inscription gratuite sur https://www.football-data.org/client/register
# → Pour GitHub Actions : ajoute FD_API_KEY dans Settings > Secrets > Actions
API_KEY: str = os.getenv("FD_API_KEY", "24ffda09d36c40698b8a5e3d0b928e7c")

API_BASE        = "https://api.football-data.org/v4"
WC_COMPETITION  = "WC"       # code Coupe du Monde
WC_SEASON       = "2026"

SCORES_FILE     = Path("live_scores.json")   # cache local des scores
SIMULATOR       = Path("simulator.py")
POLL_INTERVAL   = 60   # secondes entre deux polls (mode continu local)
REQUEST_TIMEOUT = 15

# ── Mapping noms API → noms simulator.py ──────────────────────────────────────

NAME_MAP: dict[str, str] = {
    "USA":                          "United States",
    "United States of America":     "United States",
    "Côte d'Ivoire":                "Ivory Coast",
    "Cote d'Ivoire":                "Ivory Coast",
    "Bosnia and Herzegovina":       "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    "DR Congo":                     "DR Congo",
    "Congo DR":                     "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Czechia":                      "Czech Republic",
    "Czech Republic":               "Czech Republic",
    "Cape Verde Islands":           "Cape Verde",
    "Republic of Korea":            "South Korea",
    "Korea Republic":               "South Korea",
    "Türkiye":                      "Turkey",
    "Curaçao":                      "Curacao",
}


def normalize(name: str) -> str:
    return NAME_MAP.get(name.strip(), name.strip())


# ── Récupération des scores ────────────────────────────────────────────────────

def fetch_matches() -> list[dict[str, Any]] | None:
    """
    Récupère tous les matchs du tournoi depuis football-data.org.
    Retourne None en cas d'erreur.
    """
    url = f"{API_BASE}/competitions/{WC_COMPETITION}/matches"
    headers = {"X-Auth-Token": API_KEY}
    params  = {"season": WC_SEASON}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)

        if r.status_code == 401:
            print("[ERROR] Clé API invalide. Vérifie API_KEY dans watcher.py ou la variable FD_API_KEY.")
            return None
        if r.status_code == 429:
            print("[WARN] Limite de requêtes atteinte (100/jour). On réessaiera demain.")
            return None
        r.raise_for_status()

        data = r.json()
        return data.get("matches", [])

    except requests.exceptions.RequestException as e:
        print(f"[WARN] Erreur réseau : {e}")
        return None


def extract_finished_matches(
    matches: list[dict[str, Any]],
) -> list[tuple[str, str, int, int]]:
    """
    Extrait les matchs terminés ET en cours depuis la réponse API.
    Retourne une liste de (team1, team2, score1, score2).
    """
    result: list[tuple[str, str, int, int]] = []

    for m in matches:
        status = m.get("status", "").upper()

        # Statuts considérés (terminé ou en cours)
        # FINISHED = match terminé ; IN_PLAY / PAUSED = en cours
        if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue

        home = normalize(m.get("homeTeam", {}).get("name", ""))
        away = normalize(m.get("awayTeam", {}).get("name", ""))

        score = m.get("score", {})
        # Priorité : score en cours (fullTime pendant le match, puis fullTime après)
        s_home = (
            score.get("fullTime", {}).get("home") or
            score.get("regularTime", {}).get("home") or
            0
        )
        s_away = (
            score.get("fullTime", {}).get("away") or
            score.get("regularTime", {}).get("away") or
            0
        )

        try:
            s_home = int(s_home)
            s_away = int(s_away)
        except (TypeError, ValueError):
            s_home, s_away = 0, 0

        if home and away:
            result.append((home, away, s_home, s_away))

    return result


# ── Comparaison des scores ─────────────────────────────────────────────────────

def load_previous_scores() -> dict[str, tuple[int, int]]:
    if not SCORES_FILE.exists():
        return {}
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return {k: tuple(v) for k, v in raw.items()}
    except Exception:
        return {}


def save_scores(matches: list[tuple[str, str, int, int]]) -> None:
    data = {f"{t1} vs {t2}": [s1, s2] for t1, t2, s1, s2 in matches}
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scores_changed(
    new: list[tuple[str, str, int, int]],
    previous: dict[str, tuple[int, int]],
) -> bool:
    changed = False
    for t1, t2, s1, s2 in new:
        key = f"{t1} vs {t2}"
        if key not in previous:
            print(f"  [NOUVEAU]  {t1} {s1}-{s2} {t2}")
            changed = True
        else:
            ps1, ps2 = previous[key]
            if s1 != ps1 or s2 != ps2:
                print(f"  [BUT ⚽]   {t1} {ps1}-{ps2} → {s1}-{s2} {t2}")
                changed = True
    return changed



# ── Lancement du simulateur ────────────────────────────────────────────────────

def run_simulator(n: int = 100_000) -> bool:
    print(f"[SIM] Lancement de {n:,} simulations Monte Carlo...")
    result = subprocess.run(
        [sys.executable, str(SIMULATOR), "--n", str(n), "--no-fetch"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.strip():
                print(" ", line)
        return True
    else:
        print(f"[ERROR] simulator.py a échoué :\n{result.stderr}")
        return False


# ── Logique principale ─────────────────────────────────────────────────────────

def run_once(n_sim: int = 100_000) -> bool:
    """Une passe complète. Retourne True si une simulation a été lancée."""
    print(f"[{time.strftime('%H:%M:%S')}] Vérification des scores...")

    matches_raw = fetch_matches()
    if matches_raw is None:
        return False

    matches = extract_finished_matches(matches_raw)
    live_count = sum(
        1 for m in matches_raw
        if m.get("status", "").upper() in ("IN_PLAY", "PAUSED")
    )
    print(f"  {len(matches)} match(s) terminé(s) ou en cours ({live_count} live).")

    if not matches:
        return False

    previous = load_previous_scores()
    changed  = scores_changed(matches, previous)

    if not changed:
        print("  Aucun changement de score — simulation non relancée.")
        return False

    save_scores(matches)
    update_simulator_matches(matches)
    return run_simulator(n_sim)


def run_loop(n_sim: int = 100_000) -> None:
    print(f"[WATCHER] Démarrage — poll toutes les {POLL_INTERVAL}s. Ctrl+C pour arrêter.\n")
    while True:
        try:
            run_once(n_sim)
        except KeyboardInterrupt:
            print("\n[WATCHER] Arrêt.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
        print(f"  Prochain poll dans {POLL_INTERVAL}s...\n")
        time.sleep(POLL_INTERVAL)


# ── Entrée ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Watcher scores WC 2026")
    parser.add_argument("--once", action="store_true",
                        help="Une seule passe (mode GitHub Actions)")
    parser.add_argument("--n", type=int, default=100_000,
                        help="Nombre de simulations (défaut : 100000)")
    args = parser.parse_args()

    if args.once:
        run_once(args.n)
    else:
        run_loop(args.n)


if __name__ == "__main__":
    main()
