"""
FIFA World Cup 2026 — Simulateur Monte Carlo + Watcher intégré
==============================================================
Un seul fichier. Deux modes :

  python simulator.py                  → simule une fois avec les matchs encodés
  python simulator.py --watch          → mode live : poll football-data.org toutes
                                         les 60s, relance dès qu'un score change
  python simulator.py --watch --once   → une seule passe (mode GitHub Actions)
  python simulator.py --n 50000        → nombre de simulations personnalisé
  python simulator.py --no-fetch       → Elo embarqués (pas d'appel réseau)

Sortie : bracket.json  (lu par l'application React)

Configuration API (mode --watch) :
  Inscription gratuite : https://www.football-data.org/client/register
  → Colle ta clé dans API_KEY ci-dessous, OU
  → Exporte la variable d'environnement : FD_API_KEY=ta_clé

Dépendances :
    pip install requests numpy
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import requests

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# ── Clé API football-data.org ─────────────────────────────────────────────────
# Inscription gratuite sur https://www.football-data.org/client/register
# Pour GitHub Actions : ajoute un secret FD_API_KEY dans Settings > Secrets
API_KEY: str = os.getenv("FD_API_KEY", "24ffda09d36c40698b8a5e3d0b928e7c")

SCORES_FILE    = Path("live_scores.json")
BRACKET_FILE   = Path("bracket.json")
POLL_INTERVAL  = 60   # secondes entre deux polls (mode --watch continu)

# ══════════════════════════════════════════════════════════════════════════════
# DONNÉES DU TOURNOI
# ══════════════════════════════════════════════════════════════════════════════

# ── Ratings Elo pré-encodés (source : eloratings.net, snapshot juin 2026) ─────
FALLBACK_ELO: dict[str, int] = {
    # Groupe A
    "Mexico":                    1896,
    "South Africa":              1524,
    "South Korea":               1786,
    "Czech Republic":            1759,
    # Groupe B
    "Canada":                    1779,
    "Bosnia and Herzegovina":    1680,
    "Qatar":                     1543,
    "Switzerland":               1879,
    # Groupe C
    "Brazil":                    1986,
    "Morocco":                   1888,
    "Haiti":                     1393,
    "Scotland":                  1763,
    # Groupe D
    "United States":             1826,
    "Paraguay":                  1699,
    "Australia":                 1735,
    "Turkey":                    1816,
    # Groupe E
    "Germany":                   1954,
    "Curacao":                   1458,
    "Ivory Coast":               1762,
    "Ecuador":                   1754,
    # Groupe F
    "Netherlands":               1972,
    "Japan":                     1910,
    "Sweden":                    1857,
    "Tunisia":                   1667,
    # Groupe G
    "Belgium":                   1942,
    "Egypt":                     1720,
    "Iran":                      1741,
    "New Zealand":               1523,
    # Groupe H
    "Spain":                     2129,
    "Cape Verde":                1622,
    "Saudi Arabia":              1680,
    "Uruguay":                   1887,
    # Groupe I
    "France":                    2084,
    "Senegal":                   1863,
    "Iraq":                      1570,
    "Norway":                    1929,
    # Groupe J
    "Argentina":                 2128,
    "Algeria":                   1742,
    "Austria":                   1841,
    "Jordan":                    1600,
    # Groupe K
    "Portugal":                  1967,
    "DR Congo":                  1672,
    "Uzbekistan":                1603,
    "Colombia":                  1998,
    # Groupe L
    "England":                   2055,
    "Croatia":                   1876,
    "Ghana":                     1668,
    "Panama":                    1650,
}

# ── Structure des 12 groupes ──────────────────────────────────────────────────
GROUPS: dict[str, list[str]] = {
    "A": ["Mexico",       "South Africa",            "South Korea",   "Czech Republic"],
    "B": ["Canada",       "Bosnia and Herzegovina",  "Qatar",         "Switzerland"],
    "C": ["Brazil",       "Morocco",                 "Haiti",         "Scotland"],
    "D": ["United States","Paraguay",                "Australia",     "Turkey"],
    "E": ["Germany",      "Curacao",                 "Ivory Coast",   "Ecuador"],
    "F": ["Netherlands",  "Japan",                   "Sweden",        "Tunisia"],
    "G": ["Belgium",      "Egypt",                   "Iran",          "New Zealand"],
    "H": ["Spain",        "Cape Verde",              "Saudi Arabia",  "Uruguay"],
    "I": ["France",       "Senegal",                 "Iraq",          "Norway"],
    "J": ["Argentina",    "Algeria",                 "Austria",       "Jordan"],
    "K": ["Portugal",     "DR Congo",                "Uzbekistan",    "Colombia"],
    "L": ["England",      "Croatia",                 "Ghana",         "Panama"],
}

# ── Résultats joués ───────────────────────────────────────────────────────────
# Ce bloc est réécrit automatiquement par le watcher en mode --watch.
# En mode statique, complète-le manuellement.
# Format : (équipe1, équipe2, score1, score2)
PLAYED_MATCHES: list[tuple[str, str, int, int]] = [
    # ── Journée 1 ────────────────────────────────────────────────────────────
    # Groupe A
    ("Mexico",                   "South Africa",           2, 0),
    ("South Korea",              "Czech Republic",         2, 1),
    # Groupe B
    ("Canada",                   "Bosnia and Herzegovina", 1, 1),
    ("Qatar",                    "Switzerland",            1, 1),
    # Groupe C
    ("Brazil",                   "Morocco",                1, 1),
    ("Haiti",                    "Scotland",               0, 1),
    # Groupe D
    ("United States",            "Paraguay",               4, 1),
    ("Australia",                "Turkey",                 2, 0),
    # Groupe E
    ("Germany",                  "Curacao",                7, 1),
    ("Ivory Coast",              "Ecuador",                1, 0),
    # Groupe F
    ("Netherlands",              "Japan",                  2, 2),
    ("Sweden",                   "Tunisia",                5, 1),
    # Groupe G
    ("Belgium",                  "Egypt",                  1, 1),
    ("Iran",                     "New Zealand",            2, 2),
    # Groupe H
    ("Spain",                    "Cape Verde",             0, 0),
    ("Saudi Arabia",             "Uruguay",                1, 1),
    # Groupe I
    ("Iraq",                     "Norway",                 1, 4),
    ("France",                   "Senegal",                3, 1),
    # Groupe J
    ("Argentina",                "Algeria",                3, 0),
    ("Austria",                  "Jordan",                 3, 1),
    # Groupe K
    ("Portugal",                 "DR Congo",               1, 1),
    ("Uzbekistan",               "Colombia",               1, 3),
    # Groupe L
    ("England",                  "Croatia",                4, 2),
    ("Ghana",                    "Panama",                 1, 0),
    # ── Journée 2 ────────────────────────────────────────────────────────────
    # Groupe A
    ("Czech Republic",           "South Africa",           1, 1),
    ("Mexico",                   "South Korea",            1, 0),
    # Groupe B
    ("Switzerland",              "Bosnia and Herzegovina", 4, 1),
    ("Canada",                   "Qatar",                  6, 0),
    # Groupe C
    ("Morocco",                  "Scotland",               1, 0),
    ("Brazil",                   "Haiti",                  3, 0),
    # Groupe D
    ("Turkey",                   "Paraguay",               0, 1),
    ("United States",            "Australia",              2, 0),
    # Groupe E
    ("Germany",                  "Ivory Coast",            2, 1),
    ("Ecuador",                  "Curacao",                0, 0),
    # Groupe F
    ("Netherlands",              "Sweden",                 5, 1),
    ("Tunisia",                  "Japan",                  0, 4),
    # Groupe G
    ("Belgium",                  "Iran",                   0, 0),
    ("New Zealand",              "Egypt",                  1, 3),
    # Groupe H
    ("Spain",                    "Saudi Arabia",           4, 0),
    ("Uruguay",                  "Cape Verde",             2, 2),
    # Groupe I
    ("Norway",                   "Senegal",                3, 2),
    ("France",                   "Iraq",                   3, 0),
    # Groupe J
    ("Argentina",                "Austria",                2, 0),
    ("Jordan",                   "Algeria",                1, 2),
    # Groupe K
    ("DR Congo",                 "Uzbekistan",             2, 0),
    # ── Journée 3 — à compléter ───────────────────────────────────────────────
    # Ajoute les résultats ici, ou utilise --watch pour la mise à jour auto
]

# ── Bracket R32 (structure officielle FIFA 2026) ──────────────────────────────
R32_BRACKET: list[tuple[str, str]] = [
    ("1A", "2D"),  ("1B", "2E"),  ("1C", "2F"),  ("1D", "2G"),
    ("1E", "2H"),  ("1F", "2I"),  ("1G", "2J"),  ("1H", "2K"),
    ("1I", "2L"),  ("1J", "2A"),  ("1K", "2B"),  ("1L", "2C"),
    ("T3_1", "T3_2"), ("T3_3", "T3_4"), ("T3_5", "T3_6"), ("T3_7", "T3_8"),
]

# ── Mapping noms API → noms internes ─────────────────────────────────────────
NAME_MAP: dict[str, str] = {
    "USA":                          "United States",
    "United States of America":     "United States",
    "Côte d'Ivoire":                "Ivory Coast",
    "Cote d'Ivoire":                "Ivory Coast",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    "Bosnia Herzegovina":           "Bosnia and Herzegovina",
    "Democratic Republic of Congo": "DR Congo",
    "Congo DR":                     "DR Congo",
    "Czechia":                      "Czech Republic",
    "Cape Verde Islands":           "Cape Verde",
    "Republic of Korea":            "South Korea",
    "Korea Republic":               "South Korea",
    "Türkiye":                      "Turkey",
    "Curaçao":                      "Curacao",
}


def normalize(name: str) -> str:
    return NAME_MAP.get(name.strip(), name.strip())


# ══════════════════════════════════════════════════════════════════════════════
# FETCH ELO (optionnel)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_elo_ratings() -> dict[str, int]:
    """
    Tente de récupérer les Elo depuis eloratings.net.
    Retourne FALLBACK_ELO en cas d'échec.
    """
    url = "https://eloratings.net/World.tsv"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        ratings: dict[str, int] = {}
        for line in r.text.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    ratings[parts[1].strip()] = int(parts[2].strip())
                except ValueError:
                    pass
        if ratings:
            print(f"[ELO] {len(ratings)} ratings récupérés depuis eloratings.net")
            merged = FALLBACK_ELO.copy()
            wc_teams = {t for teams in GROUPS.values() for t in teams}
            for wc_team in wc_teams:
                for fetched, rating in ratings.items():
                    a, b = wc_team.lower(), fetched.lower()
                    if a == b or a in b or b in a:
                        merged[wc_team] = rating
                        break
            return merged
    except Exception as e:
        print(f"[WARN] Elo en ligne indisponible ({e}). Ratings embarqués utilisés.")
    return FALLBACK_ELO.copy()


# ══════════════════════════════════════════════════════════════════════════════
# MOTEUR DE SIMULATION
# ══════════════════════════════════════════════════════════════════════════════

def win_probability(elo_a: float, elo_b: float) -> tuple[float, float, float]:
    """Retourne (p_win_A, p_draw, p_win_B) selon la formule Elo standard."""
    p_a   = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    spread   = abs(p_a - 0.5)
    p_draw   = max(0.05, 0.28 * (1 - spread * 1.5))
    p_win_a  = p_a * (1 - p_draw)
    p_win_b  = (1 - p_a) * (1 - p_draw)
    total    = p_win_a + p_draw + p_win_b
    return p_win_a / total, p_draw / total, p_win_b / total


def simulate_match(elo_a: float, elo_b: float) -> tuple[int, int]:
    """Simule un match de groupe. Retourne (pts_A, pts_B)."""
    p_win, p_draw, _ = win_probability(elo_a, elo_b)
    r = random.random()
    if r < p_win:
        return (3, 0)
    elif r < p_win + p_draw:
        return (1, 1)
    else:
        return (0, 3)


def simulate_knockout_match(elo_a: float, elo_b: float) -> int:
    """Simule un match KO (pas de nul). Retourne 0 si A gagne, 1 si B gagne."""
    p_a, _, p_b = win_probability(elo_a, elo_b)
    return 0 if random.random() < p_a / (p_a + p_b) else 1


def _sample_goals(elo_att: float, elo_def: float, won: bool) -> int:
    base = max(0.5, 1.0 + (elo_att - elo_def) / 800)
    raw  = int(np.random.poisson(base))
    return max(raw, 1) if won and raw == 0 else raw


def _find_group(team: str) -> str | None:
    for grp, teams in GROUPS.items():
        if team in teams:
            return grp
    return None


def simulate_group_stage(
    elo: dict[str, float],
    played: list[tuple[str, str, int, int]],
) -> dict[str, list[tuple[str, int, int, int]]]:
    """
    Simule la phase de groupes en tenant compte des matchs déjà joués.
    Retourne : groupe → [(équipe, pts, diff_buts, buts_marqués), ...] trié.
    """
    points: dict[str, dict[str, int]] = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}
    gd:     dict[str, dict[str, int]] = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}
    gf:     dict[str, dict[str, int]] = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}

    played_set: set[frozenset[str]] = set()
    for t1, t2, s1, s2 in played:
        key = frozenset([t1, t2])
        if key in played_set:          # dédoublonnage
            continue
        played_set.add(key)
        grp = _find_group(t1)
        if grp is None:
            continue
        if s1 > s2:
            points[grp][t1] += 3
        elif s1 == s2:
            points[grp][t1] += 1
            points[grp][t2] += 1
        else:
            points[grp][t2] += 3
        gd[grp][t1] += s1 - s2;  gd[grp][t2] += s2 - s1
        gf[grp][t1] += s1;       gf[grp][t2] += s2

    # Matchs restants à simuler
    for grp, teams in GROUPS.items():
        for t1, t2 in combinations(teams, 2):
            if frozenset([t1, t2]) in played_set:
                continue
            pts1, pts2 = simulate_match(elo[t1], elo[t2])
            points[grp][t1] += pts1;  points[grp][t2] += pts2
            g1 = _sample_goals(elo[t1], elo[t2], pts1 == 3)
            g2 = _sample_goals(elo[t2], elo[t1], pts2 == 3)
            gd[grp][t1] += g1 - g2;  gd[grp][t2] += g2 - g1
            gf[grp][t1] += g1;       gf[grp][t2] += g2

    return {
        grp: sorted(
            [(t, points[grp][t], gd[grp][t], gf[grp][t]) for t in teams],
            key=lambda x: (x[1], x[2], x[3], elo[x[0]]),
            reverse=True,
        )
        for grp, teams in GROUPS.items()
    }


def select_best_thirds(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> list[str]:
    """Sélectionne les 8 meilleures équipes classées 3es (critères FIFA)."""
    thirds = [
        (ranking[2][0], ranking[2][1], ranking[2][2], ranking[2][3])
        for ranking in group_results.values()
    ]
    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


def get_qualified_teams(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> dict[str, str]:
    qualified: dict[str, str] = {}
    for grp, ranking in group_results.items():
        qualified[f"1{grp}"] = ranking[0][0]
        qualified[f"2{grp}"] = ranking[1][0]
    for i, team in enumerate(select_best_thirds(group_results), 1):
        qualified[f"T3_{i}"] = team
    return qualified


def simulate_knockout_stage(
    qualified: dict[str, str],
    elo: dict[str, float],
) -> dict[str, str]:
    survivors: list[str] = []
    for slot_a, slot_b in R32_BRACKET:
        ta = qualified.get(slot_a, "TBD")
        tb = qualified.get(slot_b, "TBD")
        if ta == "TBD" or tb == "TBD":
            survivors.append(ta if tb == "TBD" else tb)
            continue
        survivors.append(ta if simulate_knockout_match(elo[ta], elo[tb]) == 0 else tb)

    results: dict[str, str] = {}
    current = survivors
    for rnd in ["R16", "QF", "SF", "Final"]:
        nxt: list[str] = []
        for i in range(0, len(current), 2):
            if i + 1 >= len(current):
                nxt.append(current[i])
                break
            w = current[i] if simulate_knockout_match(elo[current[i]], elo[current[i+1]]) == 0 else current[i+1]
            results[f"{rnd}_{i//2}"] = w
            nxt.append(w)
        current = nxt
        if len(current) == 1:
            results["Champion"] = current[0]
            break
    return results


# ── Moteur Monte Carlo ────────────────────────────────────────────────────────

def run_simulation(
    n: int,
    elo: dict[str, float],
    played: list[tuple[str, str, int, int]] | None = None,
) -> dict[str, Any]:
    """
    Lance n simulations Monte Carlo.
    Si `played` est fourni, il remplace PLAYED_MATCHES (utile en mode watch).
    """
    if played is None:
        played = PLAYED_MATCHES

    finish_pos: dict[str, dict[str, dict[str, int]]] = {
        grp: {"1st": defaultdict(int), "2nd": defaultdict(int), "3rd": defaultdict(int)}
        for grp in GROUPS
    }
    best_third_count: dict[str, int] = defaultdict(int)
    ko_counts = {s: defaultdict(int) for s in ["R32", "R16", "QF", "SF", "Final", "Champion"]}
    r32_pairs: dict[int, dict[tuple[str, str], int]] = {i: defaultdict(int) for i in range(len(R32_BRACKET))}

    for _ in range(n):
        gr = simulate_group_stage(elo, played)
        for grp, ranking in gr.items():
            for idx, pos in enumerate(["1st", "2nd", "3rd"]):
                if idx < len(ranking):
                    finish_pos[grp][pos][ranking[idx][0]] += 1
        for t in select_best_thirds(gr):
            best_third_count[t] += 1
        qualified = get_qualified_teams(gr)
        for team in qualified.values():
            ko_counts["R32"][team] += 1
        for i, (sa, sb) in enumerate(R32_BRACKET):
            ta, tb = qualified.get(sa), qualified.get(sb)
            if ta and tb:
                r32_pairs[i][tuple(sorted([ta, tb]))] += 1
        for key, winner in simulate_knockout_stage(qualified, elo).items():
            for stage in ["R16", "QF", "SF", "Final", "Champion"]:
                if key.startswith(stage) or key == stage:
                    ko_counts[stage][winner] += 1

    def probs(c: dict, total: int) -> dict[str, float]:
        return {k: round(v / total, 4) for k, v in sorted(c.items(), key=lambda x: -x[1])}

    output: dict[str, Any] = {
        "n_simulations": n,
        "generated_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elo_ratings":   {k: int(v) for k, v in elo.items()},
        "live_matches":  [
            {"home": t1, "away": t2, "score_home": s1, "score_away": s2}
            for t1, t2, s1, s2 in played
        ],
        "groups": {
            grp: {
                "teams":    GROUPS[grp],
                "prob_1st": probs(finish_pos[grp]["1st"], n),
                "prob_2nd": probs(finish_pos[grp]["2nd"], n),
                "prob_3rd": probs(finish_pos[grp]["3rd"], n),
            }
            for grp in GROUPS
        },
        "knockout": {
            "prob_R32":        probs(ko_counts["R32"], n),
            "prob_R16":        probs(ko_counts["R16"], n),
            "prob_QF":         probs(ko_counts["QF"],  n),
            "prob_SF":         probs(ko_counts["SF"],  n),
            "prob_Final":      probs(ko_counts["Final"], n),
            "prob_Champion":   probs(ko_counts["Champion"], n),
            "prob_best_third": probs(best_third_count, n),
        },
        "bracket": {
            "r32_most_likely_matchups": [
                {
                    "match": i + 1,
                    "slot_a": sa, "slot_b": sb,
                    "most_likely_team_a": max(r32_pairs[i], key=r32_pairs[i].get)[0] if r32_pairs[i] else "?",
                    "most_likely_team_b": max(r32_pairs[i], key=r32_pairs[i].get)[1] if r32_pairs[i] else "?",
                    "probability": round(max(r32_pairs[i].values()) / n, 4) if r32_pairs[i] else 0,
                }
                for i, (sa, sb) in enumerate(R32_BRACKET)
            ]
        },
    }
    return output


# ══════════════════════════════════════════════════════════════════════════════
# WATCHER INTÉGRÉ — récupération des scores live
# ══════════════════════════════════════════════════════════════════════════════

def fetch_live_matches() -> list[tuple[str, str, int, int]] | None:
    """
    Interroge football-data.org et retourne les matchs terminés + en cours.
    Retourne None en cas d'erreur réseau ou clé invalide.
    """
    if API_KEY == "METS_TA_CLE_ICI":
        print("[WARN] Clé API non configurée. Mode statique uniquement.")
        return None

    url     = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    params  = {"season": "2026"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 401:
            print("[ERROR] Clé API invalide (401). Vérifie API_KEY ou FD_API_KEY.")
            return None
        if r.status_code == 429:
            print("[WARN] Quota API atteint (100 req/jour). Réessai demain.")
            return None
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Erreur réseau : {e}")
        return None

    matches = r.json().get("matches", [])
    result: list[tuple[str, str, int, int]] = []

    for m in matches:
        status = m.get("status", "").upper()
        if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue

        home = normalize(m.get("homeTeam", {}).get("name", ""))
        away = normalize(m.get("awayTeam", {}).get("name", ""))
        sc   = m.get("score", {})
        try:
            sh = int(sc.get("fullTime", {}).get("home") or sc.get("regularTime", {}).get("home") or 0)
            sa = int(sc.get("fullTime", {}).get("away") or sc.get("regularTime", {}).get("away") or 0)
        except (TypeError, ValueError):
            sh, sa = 0, 0

        if home and away:
            result.append((home, away, sh, sa))

    return result


def load_score_cache() -> dict[str, tuple[int, int]]:
    if not SCORES_FILE.exists():
        return {}
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            return {k: tuple(v) for k, v in json.load(f).items()}
    except Exception:
        return {}


def save_score_cache(matches: list[tuple[str, str, int, int]]) -> None:
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump({f"{t1} vs {t2}": [s1, s2] for t1, t2, s1, s2 in matches}, f, indent=2)


def scores_changed(
    new: list[tuple[str, str, int, int]],
    cache: dict[str, tuple[int, int]],
) -> bool:
    changed = False
    for t1, t2, s1, s2 in new:
        key = f"{t1} vs {t2}"
        if key not in cache:
            print(f"  [NOUVEAU]   {t1} {s1}–{s2} {t2}")
            changed = True
        elif (s1, s2) != cache[key]:
            ps1, ps2 = cache[key]
            print(f"  [BUT ⚽]    {t1} {ps1}–{ps2} → {s1}–{s2} {t2}")
            changed = True
    return changed


# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_once(n: int, elo: dict[str, float]) -> None:
    """Une passe complète fetch → compare → simulate si changement."""
    print(f"[{time.strftime('%H:%M:%S')}] Vérification des scores...")

    live = fetch_live_matches()

    if live is None:
        # Pas d'API → on simule avec les matchs statiques du script
        print("[INFO] Simulation avec les matchs encodés dans le script.")
        played = PLAYED_MATCHES
        changed = True
    else:
        cache   = load_score_cache()
        changed = scores_changed(live, cache)
        played  = live

        live_count = sum(1 for t1, t2, s1, s2 in live
                         if f"{t1} vs {t2}" not in cache or (s1, s2) != cache[f"{t1} vs {t2}"])
        print(f"  {len(live)} match(s) détectés. Changements : {'oui' if changed else 'non'}.")

        if not changed:
            print("  Aucun nouveau score — simulation non relancée.")
            return

        save_score_cache(live)

    print(f"[SIM] Lancement de {n:,} simulations Monte Carlo...")
    results = run_simulation(n, elo, played)

    with open(BRACKET_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[OK] bracket.json mis à jour — {results['generated_at']}")
    print("\n── Top 5 favoris pour le titre ──")
    for team, prob in list(results["knockout"]["prob_Champion"].items())[:5]:
        print(f"  {team:25s}  {prob * 100:5.1f}%")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulateur Monte Carlo WC 2026 + watcher de scores"
    )
    parser.add_argument("--watch",    action="store_true",
                        help="Mode live : poll toutes les 60s, relance si score change")
    parser.add_argument("--once",     action="store_true",
                        help="Avec --watch : une seule passe puis quitter (GitHub Actions)")
    parser.add_argument("--n",        type=int, default=100_000,
                        help="Nombre de simulations (défaut : 100 000)")
    parser.add_argument("--output",   type=str, default="bracket.json",
                        help="Fichier JSON de sortie")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Ne pas tenter de récupérer les Elo en ligne")
    args = parser.parse_args()

    global BRACKET_FILE
    BRACKET_FILE = Path(args.output)

    # Charger les Elo
    elo = FALLBACK_ELO.copy() if args.no_fetch else fetch_elo_ratings()
    for t in {t for ts in GROUPS.values() for t in ts} - set(elo):
        print(f"[WARN] Elo manquant pour {t} → 1500")
        elo[t] = 1500

    if not args.watch:
        # ── Mode simple : simule une fois avec PLAYED_MATCHES ─────────────────
        print(f"[SIM] Lancement de {args.n:,} simulations...")
        results = run_simulation(args.n, elo)
        with open(BRACKET_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] {BRACKET_FILE} généré — {results['generated_at']}")
        print("\n── Top 5 favoris pour le titre ──")
        for team, prob in list(results["knockout"]["prob_Champion"].items())[:5]:
            print(f"  {team:25s}  {prob * 100:5.1f}%")

    elif args.once:
        # ── Mode GitHub Actions : une passe ───────────────────────────────────
        run_once(args.n, elo)

    else:
        # ── Mode live continu ─────────────────────────────────────────────────
        print(f"[WATCH] Démarrage — poll toutes les {POLL_INTERVAL}s. Ctrl+C pour arrêter.\n")
        while True:
            try:
                run_once(args.n, elo)
            except KeyboardInterrupt:
                print("\n[WATCH] Arrêt.")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
            print(f"  Prochain poll dans {POLL_INTERVAL}s...\n")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()