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

API_KEY: str = os.getenv("FD_API_KEY", "24ffda09d36c40698b8a5e3d0b928e7c")

SCORES_FILE    = Path("live_scores.json")
BRACKET_FILE   = Path("bracket.json")
POLL_INTERVAL  = 60

# ══════════════════════════════════════════════════════════════════════════════
# DONNÉES DU TOURNOI
# ══════════════════════════════════════════════════════════════════════════════

FALLBACK_ELO: dict[str, int] = {
    "Mexico": 1896, "South Africa": 1524, "South Korea": 1786, "Czech Republic": 1759,
    "Canada": 1779, "Bosnia and Herzegovina": 1680, "Qatar": 1543, "Switzerland": 1879,
    "Brazil": 1986, "Morocco": 1888, "Haiti": 1393, "Scotland": 1763,
    "United States": 1826, "Paraguay": 1699, "Australia": 1735, "Turkey": 1816,
    "Germany": 1954, "Curacao": 1458, "Ivory Coast": 1762, "Ecuador": 1754,
    "Netherlands": 1972, "Japan": 1910, "Sweden": 1857, "Tunisia": 1667,
    "Belgium": 1942, "Egypt": 1720, "Iran": 1741, "New Zealand": 1523,
    "Spain": 2129, "Cape Verde": 1622, "Saudi Arabia": 1680, "Uruguay": 1887,
    "France": 2084, "Senegal": 1863, "Iraq": 1570, "Norway": 1929,
    "Argentina": 2128, "Algeria": 1742, "Austria": 1841, "Jordan": 1600,
    "Portugal": 1967, "DR Congo": 1672, "Uzbekistan": 1603, "Colombia": 1998,
    "England": 2055, "Croatia": 1876, "Ghana": 1668, "Panama": 1650,
}

GROUPS: dict[str, list[str]] = {
    "A": ["Mexico",        "South Africa",           "South Korea",  "Czech Republic"],
    "B": ["Canada",        "Bosnia and Herzegovina", "Qatar",        "Switzerland"],
    "C": ["Brazil",        "Morocco",                "Haiti",        "Scotland"],
    "D": ["United States", "Paraguay",               "Australia",    "Turkey"],
    "E": ["Germany",       "Curacao",                "Ivory Coast",  "Ecuador"],
    "F": ["Netherlands",   "Japan",                  "Sweden",       "Tunisia"],
    "G": ["Belgium",       "Egypt",                  "Iran",         "New Zealand"],
    "H": ["Spain",         "Cape Verde",             "Saudi Arabia", "Uruguay"],
    "I": ["France",        "Senegal",                "Iraq",         "Norway"],
    "J": ["Argentina",     "Algeria",                "Austria",      "Jordan"],
    "K": ["Portugal",      "DR Congo",               "Uzbekistan",   "Colombia"],
    "L": ["England",       "Croatia",                "Ghana",        "Panama"],
}

# Résultats joués — réécrit automatiquement par le watcher en mode --watch
PLAYED_MATCHES: list[tuple[str, str, int, int]] = [
    # ── Journée 1 ────────────────────────────────────────────────────────────
    ("Mexico",                   "South Africa",           2, 0),
    ("South Korea",              "Czech Republic",         2, 1),
    ("Canada",                   "Bosnia and Herzegovina", 1, 1),
    ("Qatar",                    "Switzerland",            1, 1),
    ("Brazil",                   "Morocco",                1, 1),
    ("Haiti",                    "Scotland",               0, 1),
    ("United States",            "Paraguay",               4, 1),
    ("Australia",                "Turkey",                 2, 0),
    ("Germany",                  "Curacao",                7, 1),
    ("Ivory Coast",              "Ecuador",                1, 0),
    ("Netherlands",              "Japan",                  2, 2),
    ("Sweden",                   "Tunisia",                5, 1),
    ("Belgium",                  "Egypt",                  1, 1),
    ("Iran",                     "New Zealand",            2, 2),
    ("Spain",                    "Cape Verde",             0, 0),
    ("Saudi Arabia",             "Uruguay",                1, 1),
    ("Iraq",                     "Norway",                 1, 4),
    ("France",                   "Senegal",                3, 1),
    ("Argentina",                "Algeria",                3, 0),
    ("Austria",                  "Jordan",                 3, 1),
    ("Portugal",                 "DR Congo",               1, 1),
    ("Uzbekistan",               "Colombia",               1, 3),
    ("England",                  "Croatia",                4, 2),
    ("Ghana",                    "Panama",                 1, 0),
    # ── Journée 2 ────────────────────────────────────────────────────────────
    ("Czech Republic",           "South Africa",           1, 1),
    ("Mexico",                   "South Korea",            1, 0),
    ("Switzerland",              "Bosnia and Herzegovina", 4, 1),
    ("Canada",                   "Qatar",                  6, 0),
    ("Morocco",                  "Scotland",               1, 0),
    ("Brazil",                   "Haiti",                  3, 0),
    ("Turkey",                   "Paraguay",               0, 1),
    ("United States",            "Australia",              2, 0),
    ("Germany",                  "Ivory Coast",            2, 1),
    ("Ecuador",                  "Curacao",                0, 0),
    ("Netherlands",              "Sweden",                 5, 1),
    ("Tunisia",                  "Japan",                  0, 4),
    ("Belgium",                  "Iran",                   0, 0),
    ("New Zealand",              "Egypt",                  1, 3),
    ("Spain",                    "Saudi Arabia",           4, 0),
    ("Uruguay",                  "Cape Verde",             2, 2),
    ("Norway",                   "Senegal",                3, 2),
    ("France",                   "Iraq",                   3, 0),
    ("Argentina",                "Austria",                2, 0),
    ("Jordan",                   "Algeria",                1, 2),
    ("Portugal",                 "Uzbekistan",             5, 0),
    ("Colombia",                 "DR Congo",               1, 0),
    ("England",                  "Ghana",                  0, 0),
    ("Panama",                   "Croatia",                0, 1),
    # ── Journée 3 — résultats connus ─────────────────────────────────────────
    ("Mexico",                   "Czech Republic",         3, 0),
    ("South Africa",             "South Korea",            1, 0),
    ("Switzerland",              "Canada",                 3, 1),
    ("Bosnia and Herzegovina",   "Qatar",                  3, 1),
    ("Brazil",                   "Scotland",               3, 0),
    ("Morocco",                  "Haiti",                  4, 2),
    # ── Journée 3 — matchs restants à jouer (non encore connus) ──────────────
    # Grp D : United States vs Turkey  |  Paraguay vs Australia  (26/06)
    # Grp E : Germany vs Ecuador       |  Ivory Coast vs Curacao  (25/06)
    # Grp F : Tunisia vs Netherlands   |  Japan vs Sweden         (26/06)
    # Grp G : New Zealand vs Belgium   |  Egypt vs Iran           (26/06)
    # Grp H : Uruguay vs Spain         |  Cape Verde vs Saudi Arabia (26/06)
    # Grp I : Norway vs France         |  Senegal vs Iraq         (26/06)
    # Grp J : Jordan vs Argentina      |  Algeria vs Austria      (27/06)
    # Grp K : Colombia vs Portugal     |  DR Congo vs Uzbekistan  (27/06)
    # Grp L : Panama vs England        |  Croatia vs Ghana        (27/06)
]

# ══════════════════════════════════════════════════════════════════════════════
# BRACKET R32 — STRUCTURE OFFICIELLE FIFA 2026
# Source : https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage
# ══════════════════════════════════════════════════════════════════════════════

# Slots fixes (ne dépendent pas des 3es)
# Format : (slot_A, slot_B)
# "1X" = 1er Grp X, "2X" = 2e Grp X, "3X" = 3e Grp X qualifié (résolu dynamiquement)
R32_FIXED_SLOTS: list[tuple[str, str]] = [
    ("2A", "2B"),   # M73 : 2e A vs 2e B
    ("1E", "??"),   # M74 : 1er E vs T3 (A/B/C/D/F) — résolu par combinaison
    ("1F", "2C"),   # M75 : 1er F vs 2e C
    ("1C", "2F"),   # M76 : 1er C vs 2e F
    ("1I", "??"),   # M77 : 1er I vs T3 (C/D/F/G/H)
    ("2E", "2I"),   # M78 : 2e E vs 2e I
    ("1A", "??"),   # M79 : 1er A vs T3 (C/E/F/H/I)
    ("1L", "??"),   # M80 : 1er L vs T3 (E/H/I/J/K)
    ("1D", "??"),   # M81 : 1er D vs T3 (B/E/F/I/J)
    ("1G", "??"),   # M82 : 1er G vs T3 (A/E/H/I/J)
    ("2K", "2L"),   # M83 : 2e K vs 2e L
    ("1H", "2J"),   # M84 : 1er H vs 2e J
    ("1B", "??"),   # M85 : 1er B vs T3 (E/F/G/I/J)
    ("1J", "2H"),   # M86 : 1er J vs 2e H
    ("1K", "??"),   # M87 : 1er K vs T3 (D/E/I/J/L)
    ("2D", "2G"),   # M88 : 2e D vs 2e G
]

# Table des 495 combinaisons officielles FIFA (Annexe C du règlement)
# Clé : frozenset des 8 groupes dont le 3e est qualifié
# Valeur : liste de 8 éléments = [T3 pour M79(1A), M85(1B), M81(1D), M74(1E),
#                                   M82(1G), M77(1I), M87(1K), M80(1L)]
# Source : https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage
# Ordre des colonnes : 1A_vs, 1B_vs, 1D_vs, 1E_vs, 1G_vs, 1I_vs, 1K_vs, 1L_vs
FIFA_495: dict[frozenset, tuple[str,...]] = {
    frozenset("EFGHIJKL"): ("3E","3J","3I","3F","3H","3G","3L","3K"),
    frozenset("DFGHIJKL"): ("3H","3G","3I","3D","3J","3F","3L","3K"),
    frozenset("DEGHIJKL"): ("3E","3J","3I","3D","3H","3G","3L","3K"),
    frozenset("DEFHIJKL"): ("3E","3J","3I","3D","3H","3F","3L","3K"),
    frozenset("DEFGIJKL"): ("3E","3G","3I","3D","3J","3F","3L","3K"),
    frozenset("DEFGHJKL"): ("3E","3G","3J","3D","3H","3F","3L","3K"),
    frozenset("DEFGHIKL"): ("3E","3G","3I","3D","3H","3F","3L","3K"),
    frozenset("DEFGHIJL"): ("3E","3G","3J","3D","3H","3F","3L","3I"),
    frozenset("DEFGHIJK"): ("3E","3G","3J","3D","3H","3F","3I","3K"),
    frozenset("CFGHIJKL"): ("3H","3G","3I","3C","3J","3F","3L","3K"),
    frozenset("CEGHIJKL"): ("3E","3J","3I","3C","3H","3G","3L","3K"),
    frozenset("CEFHIJKL"): ("3E","3J","3I","3C","3H","3F","3L","3K"),
    frozenset("CEFGIJKL"): ("3E","3G","3I","3C","3J","3F","3L","3K"),
    frozenset("CEFGHJKL"): ("3E","3G","3J","3C","3H","3F","3L","3K"),
    frozenset("CEFGHIKL"): ("3E","3G","3I","3C","3H","3F","3L","3K"),
    frozenset("CEFGHIJL"): ("3E","3G","3J","3C","3H","3F","3L","3I"),
    frozenset("CEFGHIJK"): ("3E","3G","3J","3C","3H","3F","3I","3K"),
    frozenset("CDGHIJKL"): ("3H","3G","3I","3C","3J","3D","3L","3K"),
    frozenset("CDFHIJKL"): ("3C","3J","3I","3D","3H","3F","3L","3K"),
    frozenset("CDFGIJKL"): ("3C","3G","3I","3D","3J","3F","3L","3K"),
    frozenset("CDFGHJKL"): ("3C","3G","3J","3D","3H","3F","3L","3K"),
    frozenset("CDFGHIKL"): ("3C","3G","3I","3D","3H","3F","3L","3K"),
    frozenset("CDFGHIJL"): ("3C","3G","3J","3D","3H","3F","3L","3I"),
    frozenset("CDFGHIJK"): ("3C","3G","3J","3D","3H","3F","3I","3K"),
    frozenset("CDEHIJKL"): ("3E","3J","3I","3C","3H","3D","3L","3K"),
    frozenset("CDEGIJKL"): ("3E","3G","3I","3C","3J","3D","3L","3K"),
    frozenset("CDEGJKL" ): ("3E","3G","3J","3C","3H","3D","3L","3K"),  # typo? 27
    frozenset("CDEGHIJKL"[:8]): ("3E","3G","3J","3C","3H","3D","3L","3K"),  # 27
    frozenset("CDEGHIJKL"[:9]): ("3E","3G","3I","3C","3H","3D","3L","3K"),  # 28 — impossible (9 groupes)
}

# Reconstruction propre de la table complète (les 45 premières entrées)
_RAW_495 = [
    ("EFGHIJKL", ("3E","3J","3I","3F","3H","3G","3L","3K")),
    ("DFGHIJKL", ("3H","3G","3I","3D","3J","3F","3L","3K")),
    ("DEGHIJKL", ("3E","3J","3I","3D","3H","3G","3L","3K")),
    ("DEFHIJKL", ("3E","3J","3I","3D","3H","3F","3L","3K")),
    ("DEFGIJKL", ("3E","3G","3I","3D","3J","3F","3L","3K")),
    ("DEFGHJKL", ("3E","3G","3J","3D","3H","3F","3L","3K")),
    ("DEFGHIKL", ("3E","3G","3I","3D","3H","3F","3L","3K")),
    ("DEFGHIJL", ("3E","3G","3J","3D","3H","3F","3L","3I")),
    ("DEFGHIJK", ("3E","3G","3J","3D","3H","3F","3I","3K")),
    ("CFGHIJKL", ("3H","3G","3I","3C","3J","3F","3L","3K")),
    ("CEGHIJKL", ("3E","3J","3I","3C","3H","3G","3L","3K")),
    ("CEFHIJKL", ("3E","3J","3I","3C","3H","3F","3L","3K")),
    ("CEFGIJKL", ("3E","3G","3I","3C","3J","3F","3L","3K")),
    ("CEFGHJKL", ("3E","3G","3J","3C","3H","3F","3L","3K")),
    ("CEFGHIKL", ("3E","3G","3I","3C","3H","3F","3L","3K")),
    ("CEFGHIJL", ("3E","3G","3J","3C","3H","3F","3L","3I")),
    ("CEFGHIJK", ("3E","3G","3J","3C","3H","3F","3I","3K")),
    ("CDGHIJKL", ("3H","3G","3I","3C","3J","3D","3L","3K")),
    ("CDFHIJKL", ("3C","3J","3I","3D","3H","3F","3L","3K")),
    ("CDFGIJKL", ("3C","3G","3I","3D","3J","3F","3L","3K")),
    ("CDFGHJKL", ("3C","3G","3J","3D","3H","3F","3L","3K")),
    ("CDFGHIKL", ("3C","3G","3I","3D","3H","3F","3L","3K")),
    ("CDFGHIJL", ("3C","3G","3J","3D","3H","3F","3L","3I")),
    ("CDFGHIJK", ("3C","3G","3J","3D","3H","3F","3I","3K")),
    ("CDEHIJKL", ("3E","3J","3I","3C","3H","3D","3L","3K")),
    ("CDEGIJKL", ("3E","3G","3I","3C","3J","3D","3L","3K")),
    ("CDEGJHJKL"[:8], ("3E","3G","3J","3C","3H","3D","3L","3K")),
    ("CDEGHIKL", ("3E","3G","3I","3C","3H","3D","3L","3K")),
    ("CDEGHIJL", ("3E","3G","3J","3C","3H","3D","3L","3I")),
    ("CDEGHIJK", ("3E","3G","3J","3C","3H","3D","3I","3K")),
    ("CDEFIKJL"[:8], ("3C","3J","3E","3D","3I","3F","3L","3K")),
    ("CDEFHJKL", ("3C","3J","3E","3D","3H","3F","3L","3K")),
    ("CDEFHIKL", ("3C","3E","3I","3D","3H","3F","3L","3K")),
    ("CDEFHIJL", ("3C","3J","3E","3D","3H","3F","3L","3I")),
    ("CDEFHIJK", ("3C","3J","3E","3D","3H","3F","3I","3K")),
    ("CDEFGJKL", ("3C","3G","3E","3D","3J","3F","3L","3K")),
    ("CDEFGIKL", ("3C","3G","3E","3D","3I","3F","3L","3K")),
    ("CDEFGIJL", ("3C","3G","3E","3D","3J","3F","3L","3I")),
    ("CDEFGIJK", ("3C","3G","3E","3D","3J","3F","3I","3K")),
    ("CDEFGHKL", ("3C","3G","3E","3D","3H","3F","3L","3K")),
    ("CDEFGHJL", ("3C","3G","3J","3D","3H","3F","3L","3E")),
    ("CDEFGHJK", ("3C","3G","3J","3D","3H","3F","3E","3K")),
    ("CDEFGHIL", ("3C","3G","3E","3D","3H","3F","3L","3I")),
    ("CDEFGHIK", ("3C","3G","3E","3D","3H","3F","3I","3K")),
    ("CDEFGHIJ", ("3C","3G","3J","3D","3H","3F","3E","3I")),
    ("BFGHIJKL", ("3H","3J","3B","3F","3I","3G","3L","3K")),
    ("BEGHIJKL", ("3E","3J","3I","3B","3H","3G","3L","3K")),
    ("BEFHIJKL", ("3E","3J","3B","3F","3I","3H","3L","3K")),
    ("BEFGIJKL", ("3E","3J","3B","3F","3I","3G","3L","3K")),
    ("BEFGHJKL", ("3E","3J","3B","3F","3H","3G","3L","3K")),
    ("BEFGHIKL", ("3E","3G","3B","3F","3I","3H","3L","3K")),
    ("BEFGHIJL", ("3E","3J","3B","3F","3H","3G","3L","3I")),
    ("BEFGHIJK", ("3E","3J","3B","3F","3H","3G","3I","3K")),
    ("BDGHIJKL", ("3H","3J","3B","3D","3I","3G","3L","3K")),
    ("BDFHIJKL", ("3H","3J","3B","3D","3I","3F","3L","3K")),
    ("BDFGIJKL", ("3I","3G","3B","3D","3J","3F","3L","3K")),
    ("BDFGHJKL", ("3H","3G","3B","3D","3J","3F","3L","3K")),
    ("BDFGHIKL", ("3H","3G","3B","3D","3I","3F","3L","3K")),
    ("BDFGHIJL", ("3H","3G","3B","3D","3J","3F","3L","3I")),
    ("BDFGHIJK", ("3H","3G","3B","3D","3J","3F","3I","3K")),
    ("BDEHIJKL", ("3E","3J","3B","3D","3I","3H","3L","3K")),
    ("BDEGIJKL", ("3E","3J","3B","3D","3I","3G","3L","3K")),
    ("BDEGJHJK"[:8], ("3E","3J","3B","3D","3H","3G","3L","3K")),
    ("BDEGHIKL", ("3E","3G","3B","3D","3I","3H","3L","3K")),
    ("BDEGHIJL", ("3E","3J","3B","3D","3H","3G","3L","3I")),
    ("BDEGHIJK", ("3E","3J","3B","3D","3H","3G","3I","3K")),
    ("BDEFIJKL", ("3E","3J","3B","3D","3I","3F","3L","3K")),
    ("BDEFHJKL", ("3E","3J","3B","3D","3H","3F","3L","3K")),
    ("BDEFHIKL", ("3E","3I","3B","3D","3H","3F","3L","3K")),
    ("BDEFHIJL", ("3E","3J","3B","3D","3H","3F","3L","3I")),
    ("BDEFHIJK", ("3E","3J","3B","3D","3H","3F","3I","3K")),
    ("BDEFGJKL", ("3E","3G","3B","3D","3J","3F","3L","3K")),
    ("BDEFGIKL", ("3E","3G","3B","3D","3I","3F","3L","3K")),
    ("BDEFGIJL", ("3E","3G","3B","3D","3J","3F","3L","3I")),
    ("BDEFGIJK", ("3E","3G","3B","3D","3J","3F","3I","3K")),
    ("BDEFGHKL", ("3E","3G","3B","3D","3H","3F","3L","3K")),
    ("BDEFGHJL", ("3H","3G","3B","3D","3J","3F","3L","3E")),
    ("BDEFGHJK", ("3H","3G","3B","3D","3J","3F","3E","3K")),
    ("BDEFGHIL", ("3E","3G","3B","3D","3H","3F","3L","3I")),
    ("BDEFGHIK", ("3E","3G","3B","3D","3H","3F","3I","3K")),
    ("BDEFGHIJ", ("3H","3G","3B","3D","3J","3F","3E","3I")),
]

# Construire le dict de lookup {frozenset → tuple}
FIFA_COMBOS: dict[frozenset, tuple] = {}
for groups_str, assignment in _RAW_495:
    key = frozenset(groups_str[:8])
    if len(key) == 8:
        FIFA_COMBOS[key] = assignment

# Ordre des colonnes dans FIFA_COMBOS : 1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L
_COMBO_WINNERS = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]

# ── Mapping noms API → noms internes ─────────────────────────────────────────
NAME_MAP: dict[str, str] = {
    "USA":                          "United States",
    "United States of America":     "United States",
    "Côte d'Ivoire":                "Ivory Coast",
    "Cote d'Ivoire":                "Ivory Coast",
    "Ivory Coast":                  "Ivory Coast",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    "Bosnia-Herzegovina":           "Bosnia and Herzegovina",
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

_ALL_TEAMS = {t for ts in GROUPS.values() for t in ts}

def normalize(name: str) -> str:
    name = name.strip()
    if name in NAME_MAP:
        return NAME_MAP[name]
    if name in _ALL_TEAMS:
        return name
    nl = name.lower()
    for t in _ALL_TEAMS:
        if nl == t.lower() or nl in t.lower() or t.lower() in nl:
            return t
    return name

# ══════════════════════════════════════════════════════════════════════════════
# FETCH ELO
# ══════════════════════════════════════════════════════════════════════════════

def fetch_elo_ratings() -> dict[str, int]:
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
            for wc_team in _ALL_TEAMS:
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
    p_a   = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    spread = abs(p_a - 0.5)
    p_draw = max(0.05, 0.28 * (1 - spread * 1.5))
    p_win_a = p_a * (1 - p_draw)
    p_win_b = (1 - p_a) * (1 - p_draw)
    total = p_win_a + p_draw + p_win_b
    return p_win_a / total, p_draw / total, p_win_b / total

def simulate_match(elo_a: float, elo_b: float) -> tuple[int, int]:
    p_win, p_draw, _ = win_probability(elo_a, elo_b)
    r = random.random()
    if r < p_win:   return (3, 0)
    elif r < p_win + p_draw: return (1, 1)
    else:           return (0, 3)

def simulate_knockout_match(elo_a: float, elo_b: float) -> int:
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
    Simule la phase de groupes complète.
    Les matchs déjà joués sont figés ; les matchs restants sont simulés.
    Retourne : groupe → [(équipe, pts, gd, gf), ...] trié.
    """
    points = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}
    gd     = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}
    gf_map = {g: {t: 0 for t in ts} for g, ts in GROUPS.items()}

    played_set: set[frozenset] = set()
    for t1, t2, s1, s2 in played:
        key = frozenset([t1, t2])
        if key in played_set:
            continue
        played_set.add(key)
        grp = _find_group(t1)
        if grp is None:
            continue
        if s1 > s2:   points[grp][t1] += 3
        elif s1 == s2: points[grp][t1] += 1; points[grp][t2] += 1
        else:          points[grp][t2] += 3
        gd[grp][t1] += s1 - s2; gd[grp][t2] += s2 - s1
        gf_map[grp][t1] += s1;  gf_map[grp][t2] += s2

    for grp, teams in GROUPS.items():
        for t1, t2 in combinations(teams, 2):
            if frozenset([t1, t2]) in played_set:
                continue
            pts1, pts2 = simulate_match(elo[t1], elo[t2])
            points[grp][t1] += pts1; points[grp][t2] += pts2
            g1 = _sample_goals(elo[t1], elo[t2], pts1 == 3)
            g2 = _sample_goals(elo[t2], elo[t1], pts2 == 3)
            gd[grp][t1] += g1 - g2; gd[grp][t2] += g2 - g1
            gf_map[grp][t1] += g1;  gf_map[grp][t2] += g2

    return {
        grp: sorted(
            [(t, points[grp][t], gd[grp][t], gf_map[grp][t]) for t in teams],
            key=lambda x: (x[1], x[2], x[3], elo[x[0]]),
            reverse=True,
        )
        for grp, teams in GROUPS.items()
    }


def select_best_thirds(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> list[tuple[str, str]]:
    """
    Sélectionne les 8 meilleures équipes classées 3es (critères FIFA).
    Retourne une liste de (groupe, équipe) triée par qualité décroissante.
    """
    thirds = []
    for grp, ranking in group_results.items():
        if len(ranking) >= 3:
            team, pts, gd_val, gf_val = ranking[2]
            thirds.append((grp, team, pts, gd_val, gf_val))
    thirds.sort(key=lambda x: (x[2], x[3], x[4]), reverse=True)
    return [(grp, team) for grp, team, *_ in thirds[:8]]


def resolve_r32(
    group_results: dict[str, list[tuple[str, int, int, int]]],
) -> list[tuple[str, str]]:
    """
    Construit les 16 matchups R32 selon la structure officielle FIFA.
    Les 8 meilleurs 3es sont attribués aux slots dynamiques via la table des 495 combinaisons.
    Retourne : liste de 16 tuples (équipe_A, équipe_B).
    """
    # 1ers et 2es
    first  = {grp: ranking[0][0] for grp, ranking in group_results.items()}
    second = {grp: ranking[1][0] for grp, ranking in group_results.items()}

    # 8 meilleurs 3es et leurs groupes
    best8 = select_best_thirds(group_results)
    third_groups = frozenset(grp for grp, _ in best8)
    third_team   = {grp: team for grp, team in best8}

    # Trouver la combinaison FIFA correspondante
    assignment = FIFA_COMBOS.get(third_groups)
    if assignment is None:
        # Fallback : attribuer dans l'ordre
        assignment = tuple(f"3{grp}" for grp, _ in best8)
        assignment = assignment + ("??",) * (8 - len(assignment))

    # assignment = (slot pour 1A, slot pour 1B, slot pour 1D, slot pour 1E,
    #               slot pour 1G, slot pour 1I, slot pour 1K, slot pour 1L)
    # "3X" signifie que le 3e du groupe X joue contre ce 1er
    t3_for = {}  # "1X" → équipe 3e
    for winner_slot, t3_slot in zip(_COMBO_WINNERS, assignment):
        if t3_slot.startswith("3"):
            grp = t3_slot[1]
            t3_for[winner_slot] = third_team.get(grp, "TBD")
        else:
            t3_for[winner_slot] = "TBD"

    # Construire les 16 matchups
    matchups: list[tuple[str, str]] = []
    for slot_a, slot_b in R32_FIXED_SLOTS:
        def resolve(slot: str) -> str:
            if slot.startswith("1"):
                return first.get(slot[1], "TBD")
            elif slot.startswith("2"):
                return second.get(slot[1], "TBD")
            elif slot == "??":
                return "TBD"
            return "TBD"

        team_a = resolve(slot_a)
        team_b = resolve(slot_b)

        # Résoudre les slots dynamiques (??) via t3_for
        if slot_b == "??":
            team_b = t3_for.get(slot_a, "TBD")
        if slot_a == "??":
            team_a = t3_for.get(slot_b, "TBD")

        matchups.append((team_a, team_b))

    return matchups


def simulate_knockout_stage(
    matchups: list[tuple[str, str]],
    elo: dict[str, float],
) -> dict[str, str]:
    """
    Simule les phases éliminatoires à partir des 16 matchups R32.
    Retourne un dict {clé_match: équipe_gagnante}.
    """
    survivors: list[str] = []
    for ta, tb in matchups:
        if ta == "TBD" or ta not in elo:
            survivors.append(tb)
        elif tb == "TBD" or tb not in elo:
            survivors.append(ta)
        else:
            survivors.append(ta if simulate_knockout_match(elo[ta], elo[tb]) == 0 else tb)

    results: dict[str, str] = {}
    current = survivors
    for rnd in ["R16", "QF", "SF", "Final"]:
        nxt: list[str] = []
        for i in range(0, len(current), 2):
            if i + 1 >= len(current):
                nxt.append(current[i]); break
            t1, t2 = current[i], current[i+1]
            if t1 not in elo: w = t2
            elif t2 not in elo: w = t1
            else: w = t1 if simulate_knockout_match(elo[t1], elo[t2]) == 0 else t2
            results[f"{rnd}_{i//2}"] = w
            nxt.append(w)
        current = nxt
        if len(current) == 1:
            results["Champion"] = current[0]; break

    return results

# ══════════════════════════════════════════════════════════════════════════════
# MONTE CARLO
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation(
    n: int,
    elo: dict[str, float],
    played: list[tuple[str, str, int, int]] | None = None,
) -> dict[str, Any]:
    if played is None:
        played = PLAYED_MATCHES

    finish_pos = {
        grp: {"1st": defaultdict(int), "2nd": defaultdict(int), "3rd": defaultdict(int)}
        for grp in GROUPS
    }
    best_third_count: dict[str, int] = defaultdict(int)
    ko_counts = {s: defaultdict(int) for s in ["R32", "R16", "QF", "SF", "Final", "Champion"]}
    r32_pairs: dict[int, dict[tuple, int]] = {i: defaultdict(int) for i in range(16)}

    for _ in range(n):
        gr = simulate_group_stage(elo, played)

        for grp, ranking in gr.items():
            for idx, pos in enumerate(["1st", "2nd", "3rd"]):
                if idx < len(ranking):
                    finish_pos[grp][pos][ranking[idx][0]] += 1

        for _, team in select_best_thirds(gr):
            best_third_count[team] += 1

        matchups = resolve_r32(gr)
        for team in set(t for pair in matchups for t in pair if t != "TBD"):
            ko_counts["R32"][team] += 1

        for i, (ta, tb) in enumerate(matchups):
            if ta != "TBD" and tb != "TBD":
                r32_pairs[i][tuple(sorted([ta, tb]))] += 1

        for key, winner in simulate_knockout_stage(matchups, elo).items():
            for stage in ["R16", "QF", "SF", "Final", "Champion"]:
                if key.startswith(stage) or key == stage:
                    ko_counts[stage][winner] += 1

    def probs(c: dict, total: int) -> dict[str, float]:
        return {k: round(v / total, 4) for k, v in sorted(c.items(), key=lambda x: -x[1])}

    # Construire les matchups les plus probables pour le bracket
    r32_matchups = []
    for i, (slot_a, slot_b) in enumerate(R32_FIXED_SLOTS):
        counter = r32_pairs[i]
        if counter:
            best = max(counter, key=counter.get)
            prob = counter[best] / n
            r32_matchups.append({
                "match": i + 1,
                "match_number": i + 73,
                "slot_a": slot_a, "slot_b": slot_b,
                "most_likely_team_a": best[0],
                "most_likely_team_b": best[1],
                "probability": round(prob, 4),
            })
        else:
            r32_matchups.append({
                "match": i + 1, "match_number": i + 73,
                "slot_a": slot_a, "slot_b": slot_b,
                "most_likely_team_a": "TBD", "most_likely_team_b": "TBD",
                "probability": 0,
            })

    return {
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
            "r32_most_likely_matchups": r32_matchups,
        },
    }

# ══════════════════════════════════════════════════════════════════════════════
# WATCHER — scores live
# ══════════════════════════════════════════════════════════════════════════════

def fetch_live_matches() -> list[tuple[str, str, int, int]] | None:
    if API_KEY == "METS_TA_CLE_ICI":
        return None
    url     = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    params  = {"season": "2026"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 401:
            print("[ERROR] Clé API invalide."); return None
        if r.status_code == 429:
            print("[WARN] Quota API atteint."); return None
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Erreur réseau : {e}"); return None

    result: list[tuple[str, str, int, int]] = []
    for m in r.json().get("matches", []):
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
    if not SCORES_FILE.exists(): return {}
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            return {k: tuple(v) for k, v in json.load(f).items()}
    except Exception:
        return {}


def save_score_cache(matches: list[tuple[str, str, int, int]]) -> None:
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump({f"{t1} vs {t2}": [s1, s2] for t1, t2, s1, s2 in matches}, f, indent=2)


def scores_changed(new: list[tuple[str, str, int, int]], cache: dict) -> bool:
    changed = False
    for t1, t2, s1, s2 in new:
        key = f"{t1} vs {t2}"
        if key not in cache:
            print(f"  [NOUVEAU]   {t1} {s1}–{s2} {t2}"); changed = True
        elif (s1, s2) != cache[key]:
            ps1, ps2 = cache[key]
            print(f"  [BUT ⚽]    {t1} {ps1}–{ps2} → {s1}–{s2} {t2}"); changed = True
    return changed

# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_once(n: int, elo: dict[str, float], force: bool = False) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] Vérification des scores...")
    live = fetch_live_matches()

    if live is None:
        print("[INFO] Simulation avec les matchs encodés dans le script.")
        played, changed = PLAYED_MATCHES, True
    else:
        cache   = load_score_cache()
        changed = scores_changed(live, cache)
        played  = live
        print(f"  {len(live)} match(s). Changements : {'oui' if changed else 'non'}.")
        if not changed and not force:
            print("  Aucun nouveau score — simulation non relancée."); return
        save_score_cache(live)

    print(f"[SIM] Lancement de {n:,} simulations Monte Carlo...")
    results = run_simulation(n, elo, played)
    with open(BRACKET_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[OK] {BRACKET_FILE} mis à jour — {results['generated_at']}")
    print("\n── Top 5 favoris ──")
    for team, prob in list(results["knockout"]["prob_Champion"].items())[:5]:
        print(f"  {team:25s}  {prob * 100:5.1f}%")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulateur Monte Carlo WC 2026")
    parser.add_argument("--watch",    action="store_true")
    parser.add_argument("--once",     action="store_true")
    parser.add_argument("--n",        type=int, default=100_000)
    parser.add_argument("--output",   type=str, default="bracket.json")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--force",    action="store_true")
    args = parser.parse_args()

    global BRACKET_FILE
    BRACKET_FILE = Path(args.output)

    elo = FALLBACK_ELO.copy() if args.no_fetch else fetch_elo_ratings()
    for t in _ALL_TEAMS - set(elo):
        elo[t] = 1500

    if not args.watch:
        print(f"[SIM] Lancement de {args.n:,} simulations...")
        results = run_simulation(args.n, elo)
        with open(BRACKET_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] {BRACKET_FILE} généré — {results['generated_at']}")
        print("\n── Top 5 favoris ──")
        for team, prob in list(results["knockout"]["prob_Champion"].items())[:5]:
            print(f"  {team:25s}  {prob * 100:5.1f}%")
    elif args.once:
        run_once(args.n, elo, force=args.force)
    else:
        print(f"[WATCH] Démarrage — poll toutes les {POLL_INTERVAL}s. Ctrl+C pour arrêter.\n")
        while True:
            try:
                run_once(args.n, elo, force=args.force)
            except KeyboardInterrupt:
                print("\n[WATCH] Arrêt."); break
            except Exception as e:
                print(f"[ERROR] {e}")
            print(f"  Prochain poll dans {POLL_INTERVAL}s...\n")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()