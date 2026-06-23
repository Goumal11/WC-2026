"""
FIFA World Cup 2026 - Simulateur Monte Carlo
=============================================
Usage:
    python simulator.py              # 100 000 simulations, écrit bracket.json
    python simulator.py --n 50000    # nombre de simulations personnalisé
    python simulator.py --help

Sortie : bracket.json  (lu par l'application React)

Dépendances :
    pip install requests numpy pandas
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from itertools import combinations
from typing import Any

import numpy as np
import requests

# ── Constantes ──────────────────────────────────────────────────────────────

# Ratings Elo pré-encodés (source : eloratings.net, snapshot juin 2026)
# Mis à jour manuellement ou via fetch_elo_ratings() ci-dessous.
FALLBACK_ELO: dict[str, int] = {
    # Groupe A
    "Mexico":       1896,
    "South Africa": 1524,
    "South Korea":  1786,
    "Czech Republic": 1759,
    # Groupe B
    "Canada":       1779,
    "Bosnia and Herzegovina": 1680,
    "Qatar":        1543,
    "Switzerland":  1879,
    # Groupe C
    "Brazil":       1986,
    "Morocco":      1888,
    "Haiti":        1393,
    "Scotland":     1763,
    # Groupe D
    "United States": 1826,
    "Paraguay":     1699,
    "Australia":    1735,
    "Turkey":       1816,
    # Groupe E
    "Germany":      1954,
    "Curacao":      1458,
    "Ivory Coast":  1762,
    "Ecuador":      1754,
    # Groupe F
    "Netherlands":  1972,
    "Japan":        1910,
    "Sweden":       1857,
    "Tunisia":      1667,
    # Groupe G
    "Belgium":      1942,
    "Egypt":        1720,
    "Iran":         1741,
    "New Zealand":  1523,
    # Groupe H
    "Spain":        2129,
    "Cape Verde":   1622,
    "Saudi Arabia": 1680,
    "Uruguay":      1887,
    # Groupe I
    "France":       2084,
    "Senegal":      1863,
    "Iraq":         1570,
    "Norway":       1929,
    # Groupe J
    "Argentina":    2128,
    "Algeria":      1742,
    "Austria":      1841,
    "Jordan":       1600,
    # Groupe K
    "Portugal":     1967,
    "DR Congo":     1672,
    "Uzbekistan":   1603,
    "Colombia":     1998,
    # Groupe L
    "England":      2055,
    "Croatia":      1876,
    "Ghana":        1668,
    "Panama":       1650,
}

# Structure des groupes : groupe → liste de 4 équipes
GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Résultats déjà joués (journée 1 et 2, selon résultats réels)
# Format : (équipe1, équipe2, score1, score2)
# Remplis au fur et à mesure du tournoi — laisser vide pour simuler depuis le début.
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
    # Groupe K — non encore disputés au moment des captures
    # Groupe L — non encore disputés au moment des captures
    # Ajoute ici les résultats de journée 3 quand ils seront connus
]

# Bracket Coupe du Monde 2026 — R32
# Définit quels groupes se rencontrent et selon quelle logique.
# Source officielle FIFA : https://www.fifa.com/en/tournaments/mens/worldcup/canada-mexico-usa-2026
#
# Les slots T1-T12 = 1ers, T2a-T2l = 2es, T3 = meilleur 3e de la combinaison
#
# Format R32 selon draw officiel :
R32_BRACKET: list[tuple[str, str]] = [
    # match_id → (slot_A, slot_B)
    ("1A", "2D"),   # R32 Match 1  : 1er A  vs 2e D
    ("1B", "2E"),   # R32 Match 2  : 1er B  vs 2e E
    ("1C", "2F"),   # R32 Match 3  : 1er C  vs 2e F
    ("1D", "2G"),   # R32 Match 4  : 1er D  vs 2e G
    ("1E", "2H"),   # R32 Match 5  : 1er E  vs 2e H
    ("1F", "2I"),   # R32 Match 6  : 1er F  vs 2e I
    ("1G", "2J"),   # R32 Match 7  : 1er G  vs 2e J
    ("1H", "2K"),   # R32 Match 8  : 1er H  vs 2e K
    ("1I", "2L"),   # R32 Match 9  : 1er I  vs 2e L
    ("1J", "2A"),   # R32 Match 10 : 1er J  vs 2e A
    ("1K", "2B"),   # R32 Match 11 : 1er K  vs 2e B
    ("1L", "2C"),   # R32 Match 12 : 1er L  vs 2e C
    # 8 meilleurs 3es répartis selon la combinaison FIFA (simplification)
    ("T3_1", "T3_2"),
    ("T3_3", "T3_4"),
    ("T3_5", "T3_6"),
    ("T3_7", "T3_8"),
]

# Groupes éligibles pour les 8 meilleurs 3es selon la table FIFA 2026
# (dépend des 3es qui se qualifient — appliqué dynamiquement)
BEST_THIRD_GROUPS = list("ABCDEFGHIJKL")


# ── Scraping Elo (optionnel) ──────────────────────────────────────────────────

def fetch_elo_ratings() -> dict[str, int]:
    """
    Tente de récupérer les ratings Elo en temps réel depuis eloratings.net.
    En cas d'échec, retourne les ratings FALLBACK_ELO.
    """
    url = "https://eloratings.net/World.tsv"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        ratings: dict[str, int] = {}
        for line in r.text.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                name = parts[1].strip()
                try:
                    rating = int(parts[2].strip())
                    ratings[name] = rating
                except ValueError:
                    pass
        if ratings:
            print(f"[OK] {len(ratings)} ratings Elo récupérés depuis eloratings.net")
            # Filtrer aux équipes de la Coupe du Monde
            wc_teams = {t for teams in GROUPS.values() for t in teams}
            merged = {**FALLBACK_ELO}  # priorité au fallback pour les noms exacts
            for wc_team in wc_teams:
                for fetched_name, rating in ratings.items():
                    if _name_match(wc_team, fetched_name):
                        merged[wc_team] = rating
                        break
            return merged
    except Exception as e:
        print(f"[WARN] Impossible de récupérer les Elo en ligne ({e}). Utilisation des ratings embarqués.")
    return FALLBACK_ELO.copy()


def _name_match(a: str, b: str) -> bool:
    """Correspondance floue entre noms d'équipes."""
    a, b = a.lower().strip(), b.lower().strip()
    return a == b or a in b or b in a


# ── Logique de simulation ──────────────────────────────────────────────────

def win_probability(elo_a: float, elo_b: float) -> float:
    """
    Probabilité de victoire de A contre B selon la formule Elo standard.
    P(A gagne) = 1 / (1 + 10^((elo_B - elo_A) / 400))
    Retourne (p_win_A, p_draw, p_win_B)
    """
    p_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    # En football, on modélise les nuls en "réduisant" la victoire nette
    # Modèle simplifié : 30% de la probabilité centrale → nul
    draw_base = 0.28
    spread = abs(p_a - 0.5)
    p_draw = max(0.05, draw_base * (1 - spread * 1.5))
    remaining = 1 - p_draw
    p_win_a = p_a * remaining / (p_a + (1 - p_a))  # renormalise
    # recalcule proprement
    p_win_a = p_a * (1 - p_draw)
    p_win_b = (1 - p_a) * (1 - p_draw)
    # normalise pour sommer à 1
    total = p_win_a + p_draw + p_win_b
    return p_win_a / total, p_draw / total, p_win_b / total


def simulate_match(elo_a: float, elo_b: float) -> tuple[int, int]:
    """
    Simule un match de phase de groupes.
    Retourne (pts_A, pts_B) : victoire=3/0, nul=1/1, défaite=0/3
    """
    p_win, p_draw, p_loss = win_probability(elo_a, elo_b)
    r = random.random()
    if r < p_win:
        return (3, 0)
    elif r < p_win + p_draw:
        return (1, 1)
    else:
        return (0, 3)


def simulate_knockout_match(elo_a: float, elo_b: float) -> int:
    """
    Simule un match à élimination directe (pas de nul possible).
    Retourne 0 si A gagne, 1 si B gagne.
    """
    p_a, _, p_b = win_probability(elo_a, elo_b)
    # En KO, on redistribue les nuls proportionnellement
    total = p_a + p_b
    return 0 if random.random() < p_a / total else 1


# ── Phase de groupes ──────────────────────────────────────────────────────────

def simulate_group_stage(
    elo: dict[str, float],
    played: list[tuple[str, str, int, int]],
) -> dict[str, dict[str, list[str]]]:
    """
    Simule toute la phase de groupes.
    Retourne un dict : groupe → {"1st": [équipe], "2nd": [équipe], "3rd": [équipe]}
    Plus les classements complets pour choisir les meilleurs 3es.
    """
    # Construire l'état initial depuis les matchs joués
    points: dict[str, dict[str, int]] = {}
    gd: dict[str, dict[str, int]] = {}    # goal difference
    gf: dict[str, dict[str, int]] = {}    # goals for

    for grp, teams in GROUPS.items():
        points[grp] = {t: 0 for t in teams}
        gd[grp] = {t: 0 for t in teams}
        gf[grp] = {t: 0 for t in teams}

    # Matrice des matchs déjà joués
    played_set: set[frozenset[str]] = set()
    for t1, t2, s1, s2 in played:
        key = frozenset([t1, t2])
        played_set.add(key)
        grp = _find_group(t1)
        if grp is None:
            continue
        # Points
        if s1 > s2:
            points[grp][t1] += 3
        elif s1 == s2:
            points[grp][t1] += 1
            points[grp][t2] += 1
        else:
            points[grp][t2] += 3
        # GD / GF
        gd[grp][t1] += s1 - s2
        gd[grp][t2] += s2 - s1
        gf[grp][t1] += s1
        gf[grp][t2] += s2

    # Simuler les matchs restants
    for grp, teams in GROUPS.items():
        for t1, t2 in combinations(teams, 2):
            if frozenset([t1, t2]) in played_set:
                continue
            pts1, pts2 = simulate_match(elo[t1], elo[t2])
            points[grp][t1] += pts1
            points[grp][t2] += pts2
            # Score simulé (approximatif pour GD)
            goals1 = _sample_goals(elo[t1], elo[t2], pts1 == 3)
            goals2 = _sample_goals(elo[t2], elo[t1], pts2 == 3)
            gd[grp][t1] += goals1 - goals2
            gd[grp][t2] += goals2 - goals1
            gf[grp][t1] += goals1
            gf[grp][t2] += goals2

    # Classer chaque groupe
    results: dict[str, list[tuple[str, int, int, int]]] = {}
    for grp, teams in GROUPS.items():
        ranked = sorted(
            teams,
            key=lambda t: (points[grp][t], gd[grp][t], gf[grp][t], elo[t]),
            reverse=True,
        )
        results[grp] = [
            (t, points[grp][t], gd[grp][t], gf[grp][t]) for t in ranked
        ]

    return results


def _find_group(team: str) -> str | None:
    for grp, teams in GROUPS.items():
        if team in teams:
            return grp
    return None


def _sample_goals(elo_attacker: float, elo_defender: float, won: bool) -> int:
    """Génère un score de buts approximatif basé sur le différentiel Elo."""
    base = max(0.5, 1.0 + (elo_attacker - elo_defender) / 800)
    raw = np.random.poisson(base)
    if won and raw == 0:
        raw = 1
    return int(raw)


# ── Sélection des 8 meilleurs 3es ────────────────────────────────────────────

def select_best_thirds(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> list[str]:
    """
    Sélectionne les 8 meilleures équipes classées 3es (critères FIFA 2026) :
    Points → Différence de buts → Buts marqués → Tirage aléatoire.
    Retourne la liste des 8 équipes qualifiées comme meilleurs 3es.
    """
    thirds = []
    for grp, ranking in group_results.items():
        team, pts, gd, gf = ranking[2]  # 3e de chaque groupe
        thirds.append((team, pts, gd, gf))

    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


# ── Phase à élimination directe ──────────────────────────────────────────────

def get_qualified_teams(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> dict[str, str]:
    """
    Construit le dict des équipes qualifiées.
    Clés : "1A", "2A", ..., "1L", "2L", "T3_1" ... "T3_8"
    """
    qualified: dict[str, str] = {}
    for grp, ranking in group_results.items():
        qualified[f"1{grp}"] = ranking[0][0]  # 1er
        qualified[f"2{grp}"] = ranking[1][0]  # 2e

    best_thirds = select_best_thirds(group_results)
    for i, team in enumerate(best_thirds, 1):
        qualified[f"T3_{i}"] = team

    return qualified


def simulate_knockout_stage(
    qualified: dict[str, str],
    elo: dict[str, float],
) -> dict[str, str]:
    """
    Simule les phases éliminatoires (R32 → R16 → QF → SF → Finale).
    Retourne un dict : round+match_id → équipe gagnante.
    """
    rounds = {
        "R32": R32_BRACKET,
    }

    survivors: list[str] = []
    for slot_a, slot_b in R32_BRACKET:
        team_a = qualified.get(slot_a, "TBD")
        team_b = qualified.get(slot_b, "TBD")
        if team_a == "TBD" or team_b == "TBD":
            survivors.append(team_a if team_b == "TBD" else team_b)
            continue
        winner_idx = simulate_knockout_match(elo[team_a], elo[team_b])
        survivors.append(team_a if winner_idx == 0 else team_b)

    # R16, QF, SF, Finale
    results: dict[str, str] = {}
    current_round = survivors
    round_names = ["R16", "QF", "SF", "Final"]

    for rnd_name in round_names:
        next_round: list[str] = []
        for i in range(0, len(current_round), 2):
            if i + 1 >= len(current_round):
                next_round.append(current_round[i])
                break
            t1 = current_round[i]
            t2 = current_round[i + 1]
            winner_idx = simulate_knockout_match(elo[t1], elo[t2])
            winner = t1 if winner_idx == 0 else t2
            results[f"{rnd_name}_{i//2}"] = winner
            next_round.append(winner)
        current_round = next_round
        if len(current_round) == 1:
            results["Champion"] = current_round[0]
            break

    return results


# ── Moteur Monte Carlo ──────────────────────────────────────────────────────

def run_simulation(n: int, elo: dict[str, float]) -> dict[str, Any]:
    """
    Lance n simulations Monte Carlo et agrège les probabilités.

    Retourne un dict prêt pour export JSON :
    {
      "n_simulations": int,
      "groups": {
        "A": {
          "teams": [...],
          "prob_1st": {"Mexico": 0.72, ...},
          "prob_2nd": {...},
          "prob_3rd_qualify": {...},
        },
        ...
      },
      "knockout": {
        "prob_R32": {"Argentina": 0.98, ...},
        "prob_R16": {...},
        "prob_QF": {...},
        "prob_SF": {...},
        "prob_Final": {...},
        "prob_Champion": {...},
      },
      "bracket": {
        "most_likely": {
          "R32": [["ArgentinaXX%", "BrazilXX%"], ...],
          ...
        }
      }
    }
    """
    # Compteurs
    finish_pos: dict[str, dict[str, dict[str, int]]] = {
        grp: {"1st": defaultdict(int), "2nd": defaultdict(int), "3rd": defaultdict(int)}
        for grp in GROUPS
    }
    best_third_count: dict[str, int] = defaultdict(int)

    ko_counts: dict[str, dict[str, int]] = {
        stage: defaultdict(int)
        for stage in ["R32", "R16", "QF", "SF", "Final", "Champion"]
    }

    # Suivi des adversaires les plus probables par slot R32
    r32_opponents: dict[int, dict[tuple[str, str], int]] = {
        i: defaultdict(int) for i in range(len(R32_BRACKET))
    }

    print(f"Lancement de {n:,} simulations...")

    for _ in range(n):
        # 1. Phase de groupes
        group_results = simulate_group_stage(elo, PLAYED_MATCHES)

        # 2. Comptage des positions en groupes
        for grp, ranking in group_results.items():
            for pos_idx, pos_key in enumerate(["1st", "2nd", "3rd"]):
                if pos_idx < len(ranking):
                    finish_pos[grp][pos_key][ranking[pos_idx][0]] += 1

        # 3. Meilleurs 3es qualifiés
        best_thirds = select_best_thirds(group_results)
        for t in best_thirds:
            best_third_count[t] += 1

        # 4. Qualification R32
        qualified = get_qualified_teams(group_results)

        # Compter les équipes en R32
        for team in qualified.values():
            ko_counts["R32"][team] += 1

        # Tracker les paires R32
        for i, (slot_a, slot_b) in enumerate(R32_BRACKET):
            ta = qualified.get(slot_a)
            tb = qualified.get(slot_b)
            if ta and tb:
                pair = tuple(sorted([ta, tb]))
                r32_opponents[i][pair] += 1

        # 5. Phase éliminatoire
        ko_results = simulate_knockout_stage(qualified, elo)
        for key, winner in ko_results.items():
            for stage in ["R16", "QF", "SF", "Final", "Champion"]:
                if key.startswith(stage):
                    ko_counts[stage][winner] += 1
                elif key == "Champion" and stage == "Champion":
                    ko_counts["Champion"][winner] += 1

    # ── Normalisation ──
    def to_probs(counter: dict[str, int], total: int) -> dict[str, float]:
        return {k: round(v / total, 4) for k, v in sorted(
            counter.items(), key=lambda x: -x[1]
        )}

    output: dict[str, Any] = {
        "n_simulations": n,
        "elo_ratings": {k: int(v) for k, v in elo.items()},
        "groups": {},
        "knockout": {
            "prob_R32": to_probs(ko_counts["R32"], n),
            "prob_R16": to_probs(ko_counts["R16"], n),
            "prob_QF": to_probs(ko_counts["QF"], n),
            "prob_SF": to_probs(ko_counts["SF"], n),
            "prob_Final": to_probs(ko_counts["Final"], n),
            "prob_Champion": to_probs(ko_counts["Champion"], n),
            "prob_best_third": to_probs(best_third_count, n),
        },
        "bracket": {
            "r32_most_likely_matchups": []
        }
    }

    for grp in GROUPS:
        total_teams = len(GROUPS[grp])
        output["groups"][grp] = {
            "teams": GROUPS[grp],
            "prob_1st":  to_probs(finish_pos[grp]["1st"], n),
            "prob_2nd":  to_probs(finish_pos[grp]["2nd"], n),
            "prob_3rd":  to_probs(finish_pos[grp]["3rd"], n),
        }

    # Matchup R32 le plus probable par slot
    for i, (slot_a, slot_b) in enumerate(R32_BRACKET):
        counter = r32_opponents[i]
        if counter:
            best_pair = max(counter, key=counter.get)
            prob = counter[best_pair] / n
            output["bracket"]["r32_most_likely_matchups"].append({
                "match": i + 1,
                "slot_a": slot_a,
                "slot_b": slot_b,
                "most_likely_team_a": best_pair[0],
                "most_likely_team_b": best_pair[1],
                "probability": round(prob, 4),
            })

    return output


# ── Entrée principale ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulateur Monte Carlo Coupe du Monde 2026")
    parser.add_argument("--n", type=int, default=100_000, help="Nombre de simulations (défaut : 100000)")
    parser.add_argument("--output", type=str, default="bracket.json", help="Fichier JSON de sortie")
    parser.add_argument("--no-fetch", action="store_true", help="Ne pas tenter de récupérer les Elo en ligne")
    args = parser.parse_args()

    # Charger les Elo
    if args.no_fetch:
        elo = FALLBACK_ELO.copy()
        print("[INFO] Utilisation des ratings Elo embarqués.")
    else:
        elo = fetch_elo_ratings()

    # Vérifier que toutes les équipes ont un rating
    all_teams = {t for teams in GROUPS.values() for t in teams}
    missing = all_teams - set(elo.keys())
    if missing:
        print(f"[WARN] équipes sans rating Elo : {missing}")
        for t in missing:
            elo[t] = 1500  # Valeur par défaut

    # Fixer la graine pour la reproductibilité (commenter pour aléatoire)
    # random.seed(42); np.random.seed(42)

    # Lancer les simulations
    results = run_simulation(args.n, elo)

    # Exporter
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Résultats exportés dans '{args.output}'")
    print("\n── Top 5 favoris pour le titre ──")
    for team, prob in list(results["knockout"]["prob_Champion"].items())[:5]:
        print(f"  {team:25s}  {prob*100:5.1f}%")


if __name__ == "__main__":
    main()
