import { useState, useCallback } from "react";

const API_BASE = "https://api.github.com";

function formatDate(d) {
  return d.toISOString().split("T")[0];
}

function getDefaultDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 14);
  return { start: formatDate(start), end: formatDate(end) };
}

function CommitCard({ commit }) {
  const date = new Date(commit.commit.author.date);
  const repo = commit._repo;
  const msg = commit.commit.message;
  const [title, ...bodyLines] = msg.split("\n");
  const body = bodyLines.join("\n").trim();
  const sha = commit.sha.slice(0, 7);

  return (
    <div style={{
      padding: "12px 16px", borderRadius: 8,
      background: "var(--card-bg)", border: "1px solid var(--border)",
      marginBottom: 8
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text)", wordBreak: "break-word" }}>{title}</div>
          {body && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{body}</div>}
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <a href={commit.html_url} target="_blank" rel="noopener noreferrer"
            style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>
            {sha}
          </a>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>
        <span style={{
          background: "var(--tag-bg)", padding: "2px 8px", borderRadius: 12, fontWeight: 500
        }}>{repo}</span>
        <span>{date.toLocaleDateString("fr-FR")} à {date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</span>
      </div>
    </div>
  );
}

export default function App() {
  const defaults = getDefaultDates();
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [dateFrom, setDateFrom] = useState(defaults.start);
  const [dateTo, setDateTo] = useState(defaults.end);
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetched, setFetched] = useState(false);

  const fetchCommits = useCallback(async () => {
    if (!token || !username) { setError("Token et username requis."); return; }
    setLoading(true); setError(""); setCommits([]); setFetched(false);

    const headers = { Authorization: `token ${token}`, Accept: "application/vnd.github.v3+json" };
    const since = new Date(dateFrom + "T00:00:00Z").toISOString();
    const until = new Date(dateTo + "T23:59:59Z").toISOString();

    try {
      // 1. Get all repos user pushed to
      let repos = [], page = 1;
      while (true) {
        const r = await fetch(`${API_BASE}/user/repos?per_page=100&page=${page}&sort=pushed&affiliation=owner,collaborator,organization_member`, { headers });
        if (!r.ok) throw new Error(`Repos: ${r.status} ${r.statusText}`);
        const data = await r.json();
        if (!data.length) break;
        repos = repos.concat(data);
        if (data.length < 100) break;
        page++;
      }

      // Filter repos pushed recently
      const sinceDate = new Date(since);
      repos = repos.filter(r => new Date(r.pushed_at) >= sinceDate);

      // 2. For each repo, get commits by user in range
      let allCommits = [];
      const promises = repos.map(async (repo) => {
        try {
          let pg = 1, repoCommits = [];
          while (true) {
            const url = `${API_BASE}/repos/${repo.full_name}/commits?author=${username}&since=${since}&until=${until}&per_page=100&page=${pg}`;
            const r = await fetch(url, { headers });
            if (!r.ok) return [];
            const data = await r.json();
            if (!data.length) break;
            repoCommits = repoCommits.concat(data.map(c => ({ ...c, _repo: repo.full_name })));
            if (data.length < 100) break;
            pg++;
          }
          return repoCommits;
        } catch { return []; }
      });

      const results = await Promise.all(promises);
      allCommits = results.flat().sort((a, b) =>
        new Date(b.commit.author.date) - new Date(a.commit.author.date)
      );

      setCommits(allCommits);
      setFetched(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token, username, dateFrom, dateTo]);

  // Group by date
  const grouped = {};
  commits.forEach(c => {
    const day = new Date(c.commit.author.date).toLocaleDateString("fr-FR", {
      weekday: "long", year: "numeric", month: "long", day: "numeric"
    });
    if (!grouped[day]) grouped[day] = [];
    grouped[day].push(c);
  });

  // Unique repos
  const repoSet = new Set(commits.map(c => c._repo));

  const css = `
    :root {
      --bg: #0d1117; --card-bg: #161b22; --border: #30363d;
      --text: #e6edf3; --text-muted: #8b949e; --accent: #58a6ff;
      --tag-bg: #1f2937; --input-bg: #0d1117; --btn: #238636; --btn-hover: #2ea043;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg: #ffffff; --card-bg: #f6f8fa; --border: #d1d9e0;
        --text: #1f2328; --text-muted: #656d76; --accent: #0969da;
        --tag-bg: #ddf4ff; --input-bg: #ffffff; --btn: #1f883d; --btn-hover: #1a7f37;
      }
    }
  `;

  const inputStyle = {
    padding: "8px 12px", borderRadius: 6, border: "1px solid var(--border)",
    background: "var(--input-bg)", color: "var(--text)", fontSize: 14, width: "100%",
    boxSizing: "border-box"
  };

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: "var(--text)", maxWidth: 700, margin: "0 auto", padding: 20 }}>
      <style>{css}</style>

      <h2 style={{ margin: "0 0 4px", fontSize: 22 }}>🔍 Mes commits GitHub</h2>
      <p style={{ color: "var(--text-muted)", margin: "0 0 20px", fontSize: 13 }}>
        Retrouve tes commits pushés sur une période donnée — utile pour mettre à jour Jira.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Username GitHub</label>
          <input style={inputStyle} placeholder="ton-username" value={username} onChange={e => setUsername(e.target.value.trim())} />
        </div>
        <div>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
            Personal Access Token <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>(créer)</a>
          </label>
          <input style={inputStyle} type="password" placeholder="ghp_..." value={token} onChange={e => setToken(e.target.value.trim())} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Du</label>
          <input style={inputStyle} type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Au</label>
          <input style={inputStyle} type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </div>
      </div>

      <button onClick={fetchCommits} disabled={loading}
        style={{
          width: "100%", padding: "10px 0", borderRadius: 6, border: "none",
          background: loading ? "var(--border)" : "var(--btn)", color: "#fff",
          fontSize: 14, fontWeight: 600, cursor: loading ? "default" : "pointer",
          transition: "background .2s"
        }}
        onMouseEnter={e => { if (!loading) e.target.style.background = "var(--btn-hover)"; }}
        onMouseLeave={e => { if (!loading) e.target.style.background = "var(--btn)"; }}
      >
        {loading ? "Recherche en cours..." : "Chercher mes commits"}
      </button>

      {error && <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 6, background: "#f8514926", color: "#f85149", fontSize: 13 }}>{error}</div>}

      {fetched && (
        <div style={{ marginTop: 20 }}>
          <div style={{
            display: "flex", gap: 16, marginBottom: 16, padding: "12px 16px",
            background: "var(--card-bg)", borderRadius: 8, border: "1px solid var(--border)",
            fontSize: 13
          }}>
            <div><strong style={{ fontSize: 22, color: "var(--accent)" }}>{commits.length}</strong><br/>commits</div>
            <div><strong style={{ fontSize: 22, color: "var(--accent)" }}>{repoSet.size}</strong><br/>repos</div>
            <div><strong style={{ fontSize: 22, color: "var(--accent)" }}>{Object.keys(grouped).length}</strong><br/>jours actifs</div>
          </div>

          {commits.length === 0 && (
            <p style={{ color: "var(--text-muted)", textAlign: "center", padding: 24 }}>Aucun commit trouvé sur cette période.</p>
          )}

          {Object.entries(grouped).map(([day, dayCommits]) => (
            <div key={day} style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 13, fontWeight: 600, color: "var(--text-muted)",
                textTransform: "capitalize", marginBottom: 8,
                borderBottom: "1px solid var(--border)", paddingBottom: 4
              }}>
                {day} — {dayCommits.length} commit{dayCommits.length > 1 ? "s" : ""}
              </div>
              {dayCommits.map(c => <CommitCard key={c.sha} commit={c} />)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
