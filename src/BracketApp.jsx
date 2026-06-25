import { useState, useEffect } from "react";

// ── Données de démo (remplacées par bracket.json en production) ───────────────
const DEMO_DATA = {
  n_simulations: 100000,
  generated_at: "2026-06-25T08:00:00Z",
  groups: {
    A: { teams: ["Mexico","South Africa","South Korea","Czech Republic"], prob_1st: {"Mexico":0.978,"South Korea":0.022}, prob_2nd: {"South Korea":0.803,"South Africa":0.13,"Czech Republic":0.067}, prob_3rd: {"Czech Republic":0.5,"South Africa":0.4,"South Korea":0.1} },
    B: { teams: ["Canada","Bosnia and Herzegovina","Qatar","Switzerland"], prob_1st: {"Switzerland":0.52,"Canada":0.48}, prob_2nd: {"Canada":0.52,"Switzerland":0.48}, prob_3rd: {"Bosnia and Herzegovina":0.8,"Qatar":0.2} },
    C: { teams: ["Brazil","Morocco","Haiti","Scotland"], prob_1st: {"Brazil":0.62,"Morocco":0.36,"Scotland":0.02}, prob_2nd: {"Morocco":0.63,"Brazil":0.21,"Scotland":0.16}, prob_3rd: {"Scotland":0.6,"Haiti":0.4} },
    D: { teams: ["United States","Paraguay","Australia","Turkey"], prob_1st: {"United States":0.85,"Australia":0.15}, prob_2nd: {"Australia":0.6,"Paraguay":0.3,"Turkey":0.1}, prob_3rd: {"Paraguay":0.5,"Turkey":0.5} },
    E: { teams: ["Germany","Curacao","Ivory Coast","Ecuador"], prob_1st: {"Germany":0.92,"Ivory Coast":0.08}, prob_2nd: {"Ivory Coast":0.55,"Ecuador":0.45}, prob_3rd: {"Ecuador":0.6,"Curacao":0.4} },
    F: { teams: ["Netherlands","Japan","Sweden","Tunisia"], prob_1st: {"Netherlands":0.75,"Japan":0.25}, prob_2nd: {"Japan":0.65,"Sweden":0.35}, prob_3rd: {"Sweden":0.7,"Tunisia":0.3} },
    G: { teams: ["Belgium","Egypt","Iran","New Zealand"], prob_1st: {"Belgium":0.88,"Egypt":0.12}, prob_2nd: {"Egypt":0.55,"Iran":0.45}, prob_3rd: {"Iran":0.6,"New Zealand":0.4} },
    H: { teams: ["Spain","Cape Verde","Saudi Arabia","Uruguay"], prob_1st: {"Spain":0.97,"Uruguay":0.03}, prob_2nd: {"Uruguay":0.7,"Cape Verde":0.3}, prob_3rd: {"Saudi Arabia":0.6,"Cape Verde":0.4} },
    I: { teams: ["France","Senegal","Iraq","Norway"], prob_1st: {"France":0.73,"Norway":0.27}, prob_2nd: {"Norway":0.73,"France":0.27}, prob_3rd: {"Senegal":0.8,"Iraq":0.2} },
    J: { teams: ["Argentina","Algeria","Austria","Jordan"], prob_1st: {"Argentina":1.0}, prob_2nd: {"Austria":0.71,"Algeria":0.29}, prob_3rd: {"Algeria":0.55,"Jordan":0.45} },
    K: { teams: ["Portugal","DR Congo","Uzbekistan","Colombia"], prob_1st: {"Colombia":0.62,"Portugal":0.38}, prob_2nd: {"Portugal":0.62,"Colombia":0.38}, prob_3rd: {"DR Congo":0.7,"Uzbekistan":0.3} },
    L: { teams: ["England","Croatia","Ghana","Panama"], prob_1st: {"England":0.91,"Croatia":0.09}, prob_2nd: {"Croatia":0.65,"Ghana":0.35}, prob_3rd: {"Ghana":0.6,"Panama":0.4} },
  },
  knockout: {
    prob_Champion: {"Spain":0.234,"Argentina":0.206,"France":0.118,"England":0.095,"Brazil":0.054,"Colombia":0.05,"Netherlands":0.042,"Germany":0.038,"Norway":0.025,"Portugal":0.02,"Belgium":0.018,"Japan":0.015,"Morocco":0.012,"Uruguay":0.01,"Mexico":0.008,"Australia":0.005},
    prob_Final:    {"Spain":0.42,"Argentina":0.38,"France":0.25,"England":0.21,"Brazil":0.14,"Colombia":0.13,"Netherlands":0.11,"Germany":0.1,"Norway":0.09,"Portugal":0.08},
    prob_SF:       {"Spain":0.62,"Argentina":0.58,"France":0.45,"England":0.39,"Brazil":0.28,"Colombia":0.26,"Netherlands":0.22,"Germany":0.2,"Norway":0.17},
    prob_QF:       {"Spain":0.78,"Argentina":0.74,"France":0.61,"England":0.55,"Brazil":0.42,"Colombia":0.40,"Netherlands":0.35,"Germany":0.32},
    prob_R16:      {"Spain":0.94,"Argentina":0.97,"France":0.85,"England":0.88,"Brazil":0.72,"Colombia":0.68,"Germany":0.75},
    prob_R32:      {"Spain":0.99,"Argentina":1.0,"France":0.97,"England":0.98},
    prob_best_third: {"Senegal":0.55,"Norway":0.45,"Scotland":0.4,"Croatia":0.35},
  },
  bracket: {
    r32_most_likely_matchups: [
      {match:1,slot_a:"1A",slot_b:"2D",most_likely_team_a:"Mexico",most_likely_team_b:"Australia",probability:0.58},
      {match:2,slot_a:"1B",slot_b:"2E",most_likely_team_a:"Switzerland",most_likely_team_b:"Ivory Coast",probability:0.46},
      {match:3,slot_a:"1C",slot_b:"2F",most_likely_team_a:"Brazil",most_likely_team_b:"Japan",probability:0.52},
      {match:4,slot_a:"1D",slot_b:"2G",most_likely_team_a:"United States",most_likely_team_b:"Egypt",probability:0.47},
      {match:5,slot_a:"1E",slot_b:"2H",most_likely_team_a:"Germany",most_likely_team_b:"Uruguay",probability:0.55},
      {match:6,slot_a:"1F",slot_b:"2I",most_likely_team_a:"Netherlands",most_likely_team_b:"Norway",probability:0.43},
      {match:7,slot_a:"1G",slot_b:"2J",most_likely_team_a:"Belgium",most_likely_team_b:"Austria",probability:0.51},
      {match:8,slot_a:"1H",slot_b:"2K",most_likely_team_a:"Spain",most_likely_team_b:"Portugal",probability:0.44},
      {match:9,slot_a:"1I",slot_b:"2L",most_likely_team_a:"France",most_likely_team_b:"Croatia",probability:0.53},
      {match:10,slot_a:"1J",slot_b:"2A",most_likely_team_a:"Argentina",most_likely_team_b:"South Korea",probability:0.62},
      {match:11,slot_a:"1K",slot_b:"2B",most_likely_team_a:"Colombia",most_likely_team_b:"Canada",probability:0.49},
      {match:12,slot_a:"1L",slot_b:"2C",most_likely_team_a:"England",most_likely_team_b:"Morocco",probability:0.56},
      {match:13,slot_a:"T3_1",slot_b:"T3_2",most_likely_team_a:"Senegal",most_likely_team_b:"Norway",probability:0.31},
      {match:14,slot_a:"T3_3",slot_b:"T3_4",most_likely_team_a:"Scotland",most_likely_team_b:"Croatia",probability:0.28},
      {match:15,slot_a:"T3_5",slot_b:"T3_6",most_likely_team_a:"Ecuador",most_likely_team_b:"Iran",probability:0.27},
      {match:16,slot_a:"T3_7",slot_b:"T3_8",most_likely_team_a:"Algeria",most_likely_team_b:"Ghana",probability:0.25},
    ]
  },
  live_matches: [
    {home:"Mexico",away:"South Africa",score_home:2,score_away:0},
    {home:"South Korea",away:"Czech Republic",score_home:2,score_away:1},
  ]
};

// ── Flags emoji par équipe ────────────────────────────────────────────────────
const FLAGS = {
  "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷","Czech Republic":"🇨🇿",
  "Canada":"🇨🇦","Bosnia and Herzegovina":"🇧🇦","Qatar":"🇶🇦","Switzerland":"🇨🇭",
  "Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "United States":"🇺🇸","Paraguay":"🇵🇾","Australia":"🇦🇺","Turkey":"🇹🇷",
  "Germany":"🇩🇪","Curacao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨",
  "Netherlands":"🇳🇱","Japan":"🇯🇵","Sweden":"🇸🇪","Tunisia":"🇹🇳",
  "Belgium":"🇧🇪","Egypt":"🇪🇬","Iran":"🇮🇷","New Zealand":"🇳🇿",
  "Spain":"🇪🇸","Cape Verde":"🇨🇻","Saudi Arabia":"🇸🇦","Uruguay":"🇺🇾",
  "France":"🇫🇷","Senegal":"🇸🇳","Iraq":"🇮🇶","Norway":"🇳🇴",
  "Argentina":"🇦🇷","Algeria":"🇩🇿","Austria":"🇦🇹","Jordan":"🇯🇴",
  "Portugal":"🇵🇹","DR Congo":"🇨🇩","Uzbekistan":"🇺🇿","Colombia":"🇨🇴",
  "England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croatia":"🇭🇷","Ghana":"🇬🇭","Panama":"🇵🇦",
};

// ── Couleur selon probabilité de titre ────────────────────────────────────────
function champColor(p) {
  if (p >= 0.15) return "#00c853";
  if (p >= 0.07) return "#64dd17";
  if (p >= 0.03) return "#f4b942";
  if (p >= 0.01) return "#ff6d00";
  return "#546e7a";
}

function pct(v) { return v != null ? (v * 100).toFixed(1) + "%" : "—"; }
function flag(team) { return FLAGS[team] || "🏳️"; }

// ── Composant : carte équipe dans le bracket ──────────────────────────────────
function TeamSlot({ team, champProb, isWinner }) {
  const color = team ? champColor(champProb || 0) : "#37474f";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "6px 10px",
      background: isWinner ? "rgba(0,200,83,0.12)" : "transparent",
      borderLeft: isWinner ? `3px solid ${color}` : "3px solid transparent",
      borderRadius: 4,
      minWidth: 0,
    }}>
      <span style={{ fontSize: 18, flexShrink: 0 }}>{team ? flag(team) : "?"}</span>
      <span style={{
        fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1,
      }}>
        {team || "À déterminer"}
      </span>
      {team && champProb > 0 && (
        <span style={{
          fontSize: 11, fontWeight: 500,
          color: color, flexShrink: 0, minWidth: 34, textAlign: "right",
        }}>
          {pct(champProb)}
        </span>
      )}
    </div>
  );
}

// ── Composant : match du bracket ──────────────────────────────────────────────
function BracketMatch({ match, champProbs, title }) {
  const pa = champProbs[match.most_likely_team_a] || 0;
  const pb = champProbs[match.most_likely_team_b] || 0;
  const winnerA = pa >= pb;
  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: "var(--border-radius-lg)",
      overflow: "hidden", minWidth: 210,
    }}>
      {title && (
        <div style={{
          fontSize: 10, fontWeight: 500, letterSpacing: "0.08em",
          color: "var(--color-text-tertiary)", padding: "5px 10px 4px",
          borderBottom: "0.5px solid var(--color-border-tertiary)",
          textTransform: "uppercase",
        }}>
          {title}
        </div>
      )}
      <TeamSlot team={match.most_likely_team_a} champProb={pa} isWinner={winnerA} />
      <div style={{ height: "0.5px", background: "var(--color-border-tertiary)", margin: "0 10px" }} />
      <TeamSlot team={match.most_likely_team_b} champProb={pb} isWinner={!winnerA} />
      <div style={{
        padding: "3px 10px 5px",
        fontSize: 10, color: "var(--color-text-tertiary)",
      }}>
        Probabilité du match : {pct(match.probability)}
      </div>
    </div>
  );
}

// ── Composant : groupe ────────────────────────────────────────────────────────
function GroupCard({ letter, group, champProbs }) {
  const teams = group.teams.slice().sort((a, b) =>
    ((group.prob_1st[b] || 0) + (group.prob_2nd[b] || 0)) -
    ((group.prob_1st[a] || 0) + (group.prob_2nd[a] || 0))
  );
  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: "var(--border-radius-lg)",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "8px 12px",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <span style={{
          width: 24, height: 24, borderRadius: 6,
          background: "#00c853", color: "#003c14",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 500, flexShrink: 0,
        }}>{letter}</span>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-secondary)" }}>
          Groupe {letter}
        </span>
      </div>
      <div>
        {teams.map((team, i) => {
          const p1 = group.prob_1st[team] || 0;
          const p2 = group.prob_2nd[team] || 0;
          const pQ = p1 + p2;
          const cProb = champProbs[team] || 0;
          const barColor = i === 0 ? "#00c853" : i === 1 ? "#64dd17" : "#37474f";
          return (
            <div key={team} style={{
              padding: "7px 12px",
              borderBottom: i < teams.length - 1 ? "0.5px solid var(--color-border-tertiary)" : "none",
              opacity: pQ < 0.05 ? 0.5 : 1,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 16 }}>{flag(team)}</span>
                <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-primary)", flex: 1 }}>
                  {team}
                </span>
                <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>
                  Q: {pct(pQ)}
                </span>
              </div>
              <div style={{ height: 3, background: "var(--color-background-tertiary)", borderRadius: 2 }}>
                <div style={{
                  height: "100%", borderRadius: 2,
                  width: pct(pQ), background: barColor,
                  transition: "width 0.6s ease",
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Composant : top favoris ───────────────────────────────────────────────────
function TopFavorites({ champProbs }) {
  const top = Object.entries(champProbs)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const max = top[0]?.[1] || 1;
  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: "var(--border-radius-lg)",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "10px 14px",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)",
        textTransform: "uppercase", letterSpacing: "0.08em",
      }}>
        Favoris pour le titre
      </div>
      {top.map(([team, prob], i) => (
        <div key={team} style={{
          padding: "8px 14px",
          borderBottom: i < top.length - 1 ? "0.5px solid var(--color-border-tertiary)" : "none",
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <span style={{
            fontSize: 11, fontWeight: 500, color: "var(--color-text-tertiary)",
            width: 16, textAlign: "right", flexShrink: 0,
          }}>
            {i + 1}
          </span>
          <span style={{ fontSize: 20, flexShrink: 0 }}>{flag(team)}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)" }}>
                {team}
              </span>
              <span style={{
                fontSize: 13, fontWeight: 500, color: champColor(prob), flexShrink: 0,
              }}>
                {pct(prob)}
              </span>
            </div>
            <div style={{ height: 4, background: "var(--color-background-tertiary)", borderRadius: 2 }}>
              <div style={{
                height: "100%", borderRadius: 2,
                width: pct(prob / max),
                background: champColor(prob),
                transition: "width 0.8s ease",
              }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Composant : scores live ───────────────────────────────────────────────────
function LiveScores({ matches }) {
  if (!matches || matches.length === 0) return null;
  return (
    <div style={{
      display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16,
    }}>
      {matches.map((m, i) => (
        <div key={i} style={{
          background: "var(--color-background-primary)",
          border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-md)",
          padding: "5px 10px",
          fontSize: 12, display: "flex", alignItems: "center", gap: 6,
        }}>
          <span>{flag(m.home)}</span>
          <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>
            {m.score_home} – {m.score_away}
          </span>
          <span>{flag(m.away)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Composant : section bracket ───────────────────────────────────────────────
function BracketSection({ title, matchups, champProbs }) {
  return (
    <div>
      <h3 style={{
        fontSize: 11, fontWeight: 500, letterSpacing: "0.1em",
        color: "var(--color-text-tertiary)", textTransform: "uppercase",
        margin: "0 0 10px",
      }}>
        {title}
      </h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {matchups.map((m) => (
          <BracketMatch
            key={m.match}
            match={m}
            champProbs={champProbs}
            title={`Match ${m.match}`}
          />
        ))}
      </div>
    </div>
  );
}

// ── App principale ────────────────────────────────────────────────────────────
export default function App() {
  const [data, setData] = useState(DEMO_DATA);
  const [tab, setTab] = useState("bracket");
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Charge bracket.json depuis la racine du site (GitHub Pages)
  useEffect(() => {
    setLoading(true);
    fetch("./bracket.json")
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLastUpdate(d.generated_at);
      })
      .catch(() => {
        // Pas de bracket.json → on reste sur les données de démo
        setLastUpdate(DEMO_DATA.generated_at);
      })
      .finally(() => setLoading(false));
  }, []);

  // Rafraîchissement automatique toutes les 5 minutes
  useEffect(() => {
    const id = setInterval(() => {
      fetch(`./bracket.json?t=${Date.now()}`)
        .then((r) => r.json())
        .then((d) => {
          if (d.generated_at !== data.generated_at) {
            setData(d);
            setLastUpdate(d.generated_at);
          }
        })
        .catch(() => {});
    }, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [data.generated_at]);

  const champProbs = data.knockout?.prob_Champion || {};
  const matchups   = data.bracket?.r32_most_likely_matchups || [];
  const liveMatches = data.live_matches || [];

  const r32  = matchups.filter((m) => m.match <= 16);
  const tabs = [
    { id: "bracket", label: "Bracket R32" },
    { id: "groups",  label: "Groupes" },
    { id: "odds",    label: "Probabilités" },
  ];

  return (
    <div style={{ padding: "16px 0", fontFamily: "var(--font-sans)" }}>
      <h2 className="sr-only">Simulateur Monte Carlo — Coupe du Monde 2026</h2>

      {/* En-tête */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <div>
            <h2 style={{
              margin: 0, fontSize: 18, fontWeight: 500,
              color: "var(--color-text-primary)",
            }}>
              ⚽ Coupe du Monde 2026
            </h2>
            <p style={{
              margin: "2px 0 0", fontSize: 12,
              color: "var(--color-text-tertiary)",
            }}>
              {(data.n_simulations || 0).toLocaleString()} simulations Monte Carlo
              {lastUpdate && ` · mis à jour le ${new Date(lastUpdate).toLocaleString("fr-FR")}`}
            </p>
          </div>
          {loading && (
            <span style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
              Chargement…
            </span>
          )}
        </div>
      </div>

      {/* Scores récents */}
      <LiveScores matches={liveMatches.slice(0, 8)} />

      {/* Onglets */}
      <div style={{
        display: "flex", gap: 4, marginBottom: 16,
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        paddingBottom: 0,
      }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px",
              fontSize: 13, fontWeight: tab === t.id ? 500 : 400,
              background: "transparent", border: "none", cursor: "pointer",
              borderBottom: tab === t.id ? "2px solid #00c853" : "2px solid transparent",
              color: tab === t.id ? "var(--color-text-primary)" : "var(--color-text-secondary)",
              borderRadius: 0, transition: "all 0.15s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Onglet Bracket ── */}
      {tab === "bracket" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0,1fr) minmax(0,280px)" }}>
            <div>
              <BracketSection
                title="Round of 32 — Matchups les plus probables"
                matchups={r32.slice(0, 12)}
                champProbs={champProbs}
              />
            </div>
            <TopFavorites champProbs={champProbs} />
          </div>
          {r32.length > 12 && (
            <BracketSection
              title="Meilleurs 3es — Matchups les plus probables"
              matchups={r32.slice(12)}
              champProbs={champProbs}
            />
          )}
          <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", margin: 0 }}>
            Les % à droite de chaque équipe représentent la probabilité de remporter le titre.
            Le matchup affiché est le plus fréquent sur {(data.n_simulations || 0).toLocaleString()} simulations.
          </p>
        </div>
      )}

      {/* ── Onglet Groupes ── */}
      {tab === "groups" && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 10,
        }}>
          {Object.entries(data.groups || {}).map(([letter, group]) => (
            <GroupCard
              key={letter}
              letter={letter}
              group={group}
              champProbs={champProbs}
            />
          ))}
        </div>
      )}

      {/* ── Onglet Probabilités ── */}
      {tab === "odds" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { key: "prob_Champion", label: "Champion du monde" },
            { key: "prob_Final",    label: "Atteindre la finale" },
            { key: "prob_SF",       label: "Atteindre les demi-finales" },
            { key: "prob_QF",       label: "Atteindre les quarts" },
            { key: "prob_R16",      label: "Atteindre les 1/8" },
          ].map(({ key, label }) => {
            const probs = data.knockout?.[key] || {};
            const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 12);
            const max = sorted[0]?.[1] || 1;
            return (
              <div key={key} style={{
                background: "var(--color-background-primary)",
                border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-lg)",
                overflow: "hidden",
              }}>
                <div style={{
                  padding: "8px 14px",
                  borderBottom: "0.5px solid var(--color-border-tertiary)",
                  fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)",
                  textTransform: "uppercase", letterSpacing: "0.08em",
                }}>
                  {label}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", padding: 10, gap: 6 }}>
                  {sorted.map(([team, prob]) => (
                    <div key={team} style={{
                      display: "flex", alignItems: "center", gap: 6,
                      padding: "4px 10px",
                      background: "var(--color-background-secondary)",
                      borderRadius: "var(--border-radius-md)",
                      minWidth: 130,
                    }}>
                      <span style={{ fontSize: 16 }}>{flag(team)}</span>
                      <span style={{ fontSize: 12, color: "var(--color-text-primary)", flex: 1, fontWeight: 400 }}>
                        {team}
                      </span>
                      <span style={{
                        fontSize: 12, fontWeight: 500,
                        color: champColor(prob / max * (max >= 0.15 ? 1 : 3)),
                      }}>
                        {pct(prob)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}