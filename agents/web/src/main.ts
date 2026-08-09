const API = "/api";

interface WeatherSection {
  status: string;
  city?: string;
  temp_c?: string;
  temp_f?: string;
  description?: string;
  feels_like_c?: string;
  humidity?: string;
  error?: string;
}

interface NewsArticle {
  title: string;
  source?: string;
  published?: string;
  url?: string;
}

interface NewsSection {
  status: string;
  topic?: string;
  provider?: string;
  articles: NewsArticle[];
  error?: string;
}

interface VocabularySection {
  status: string;
  word?: string;
  part_of_speech?: string;
  pronunciation?: string;
  definition?: string;
  example?: string;
  etymology?: string;
  source?: string;
  date?: string;
  error?: string;
}

interface GithubRepo {
  name: string;
  url: string;
  language?: string;
  stars?: number;
  forks?: number;
  change?: string;
  description?: string;
}

interface GithubSection {
  status: string;
  provider?: string;
  repos: GithubRepo[];
  error?: string;
}

interface DashboardResponse {
  date: string;
  greeting: string;
  weather: WeatherSection;
  news: NewsSection;
  vocabulary: VocabularySection;
  github: GithubSection;
}

type ServerEvent =
  | { type: "connected"; thread_id: string }
  | { type: "start"; thread_id: string; graph: string }
  | { type: "token"; content: string }
  | { type: "tool_start"; name: string }
  | { type: "tool_end"; name: string; content: string }
  | { type: "done"; thread_id: string; graph: string; response: string }
  | { type: "error"; message: string }
  | { type: "pong" };

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

const ICONS = {
  sparkles: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.107 5.568a2 2 0 0 0 1.535 1.535l5.568 1.107a1 1 0 0 1 0 1.966l-5.568 1.107a2 2 0 0 0-1.535 1.535l-1.107 5.568a1 1 0 0 1-1.966 0l-1.107-5.568a2 2 0 0 0-1.535-1.535l-5.568-1.107a1 1 0 0 1 0-1.966l5.568-1.107a2 2 0 0 0 1.535-1.535z"/><path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/></svg>`,
  book: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg>`,
  cloud: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="M20 12h2"/><path d="m19.07 4.93-1.41 1.41"/><path d="M15.947 12.65a4 4 0 0 0-5.925-4.128"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6z"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/></svg>`,
  wand: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9h2"/><path d="M20 9h2"/><path d="M17.8 11.8 19 13"/><path d="M15 9h.01"/><path d="M17.8 6.2 19 5"/><path d="m3 21 9-9"/><path d="M12.2 6.2 11 5"/></svg>`,
  fork: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/></svg>`,
  arrow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 7h10v10"/><path d="M7 17 17 7"/></svg>`,
  sun: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
  moon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`,
};

const SUGGESTIONS = [
  "What's the weather today?",
  "Summarize the top tech news",
  "What's trending on GitHub?",
];

const threadId = `web-${crypto.randomUUID()}`;
const city = localStorage.getItem("dashboard_city") ?? "London";
const newsTopic = localStorage.getItem("dashboard_news_topic") ?? "technology";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Missing #app");

app.className = "shell";
app.innerHTML = `
  <header class="header animate-fade-up">
    <div class="topbar">
      <div class="brand">
        <span class="brand-mark">${ICONS.sparkles}</span>
        <span class="brand-name">Marti</span>
        <span class="brand-tag">Daily Agent Hub</span>
      </div>
      <div class="topbar-actions">
        <span id="status" class="status-pill">
          <span class="status-dot" aria-hidden="true"></span>
          <span class="label">Connecting…</span>
        </span>
        <button id="theme-toggle" class="icon-btn" type="button" aria-label="Toggle theme">
          ${ICONS.moon}
        </button>
      </div>
    </div>

    <div class="greeting-block">
      <h1 id="greeting">Good day</h1>
      <p id="date"></p>
    </div>

    <div class="utility-grid">
      <div id="word-widget" class="word-widget loading">Loading word of the day…</div>
      <div id="weather-widget" class="weather-widget loading">Loading weather…</div>
    </div>
  </header>

  <section class="section animate-fade-up delay-1" aria-labelledby="dashboard-heading">
    <div class="section-head">
      <div>
        <h2 id="dashboard-heading">Today</h2>
        <p class="section-sub">A quick scan of what’s worth knowing this morning.</p>
      </div>
      <button id="refresh-dashboard" class="ghost-btn" type="button">
        ${ICONS.refresh}
        <span>Refresh</span>
      </button>
    </div>
    <div id="dashboard">
      <div class="dashboard-loading">Loading your daily briefing…</div>
    </div>
  </section>

  <section class="chat-github-row animate-fade-up delay-2" aria-label="Agent chat and GitHub trending">
    <div class="chat-panel">
      <div class="panel-head">
        <span class="accent-icon">${ICONS.wand}</span>
        <h2>Ask Marti</h2>
        <span class="side">Streaming</span>
      </div>
      <div id="chat-log" class="chat-log" role="log" aria-live="polite"></div>
      <div id="chat-status" class="chat-status"></div>
      <div class="composer">
        <div id="suggestions" class="suggestions"></div>
        <div class="chat-input-row">
          <label class="sr-only" for="message">Message Marti</label>
          <textarea
            id="message"
            rows="2"
            placeholder="Ask about today’s briefing, or anything else…"
          ></textarea>
          <button id="send" class="send-btn" type="button" aria-label="Send message" disabled>
            ${ICONS.send}
          </button>
        </div>
      </div>
    </div>
    <aside id="github-panel" class="github-panel">
      <div class="dashboard-loading">Loading trending repos…</div>
    </aside>
  </section>
`;

const greetingEl = document.querySelector<HTMLHeadingElement>("#greeting")!;
const dateEl = document.querySelector<HTMLParagraphElement>("#date")!;
const statusEl = document.querySelector<HTMLSpanElement>("#status")!;
const themeToggleBtn = document.querySelector<HTMLButtonElement>("#theme-toggle")!;
const weatherWidgetEl = document.querySelector<HTMLDivElement>("#weather-widget")!;
const wordWidgetEl = document.querySelector<HTMLDivElement>("#word-widget")!;
const dashboardEl = document.querySelector<HTMLDivElement>("#dashboard")!;
const githubPanelEl = document.querySelector<HTMLElement>("#github-panel")!;
const refreshBtn = document.querySelector<HTMLButtonElement>("#refresh-dashboard")!;
const chatLogEl = document.querySelector<HTMLDivElement>("#chat-log")!;
const chatStatusEl = document.querySelector<HTMLDivElement>("#chat-status")!;
const messageEl = document.querySelector<HTMLTextAreaElement>("#message")!;
const sendBtn = document.querySelector<HTMLButtonElement>("#send")!;
const suggestionsEl = document.querySelector<HTMLDivElement>("#suggestions")!;

let ws: WebSocket | null = null;
let streaming = false;
let replyBuffer = "";
const messages: ChatMessage[] = [
  {
    role: "system",
    content: "Connected to your daily agents. Ask about weather, news, repos, or anything else.",
  },
];

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({ thread_id: threadId });
  return `${proto}//${location.host}${API}/chat/ws?${params}`;
}

function isDarkTheme(): boolean {
  return document.documentElement.classList.contains("dark");
}

function syncThemeToggle(): void {
  const dark = isDarkTheme();
  themeToggleBtn.innerHTML = dark ? ICONS.sun : ICONS.moon;
  themeToggleBtn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
}

function toggleTheme(): void {
  const nextDark = !isDarkTheme();
  document.documentElement.classList.toggle("dark", nextDark);
  localStorage.setItem("marti_theme", nextDark ? "dark" : "light");
  syncThemeToggle();
}

function setConnectionStatus(text: string, ok = true): void {
  statusEl.className = ok ? "status-pill ok" : "status-pill err";
  statusEl.innerHTML = `
    <span class="status-dot" aria-hidden="true"></span>
    <span class="label">${escapeHtml(text)}</span>
  `;
}

function setChatStatus(text: string): void {
  if (!text) {
    chatStatusEl.textContent = "";
    return;
  }
  chatStatusEl.innerHTML = `
    <span class="pulse" aria-hidden="true"></span>
    <span>${escapeHtml(text)}</span>
  `;
}

function updateSendEnabled(): void {
  sendBtn.disabled = !messageEl.value.trim() || !ws || ws.readyState !== WebSocket.OPEN || streaming;
}

function renderChat(): void {
  chatLogEl.innerHTML = messages
    .map((m) => {
      const roleClass = m.role;
      return `
        <div class="bubble-row ${roleClass}">
          <div class="bubble bubble-${m.role}">${escapeHtml(m.content)}</div>
        </div>
      `;
    })
    .join("");
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

function renderVocabulary(vocabulary: VocabularySection): void {
  if (vocabulary.status === "error" || vocabulary.error) {
    wordWidgetEl.className = "word-widget error";
    wordWidgetEl.textContent = vocabulary.error ?? "Word unavailable";
    return;
  }

  wordWidgetEl.className = "word-widget";
  wordWidgetEl.innerHTML = `
    <p class="widget-label">${ICONS.book}<span>Word of the day</span></p>
    <p class="word-title">${escapeHtml(vocabulary.word ?? "")}</p>
    <p class="word-meta">${escapeHtml(
      [vocabulary.part_of_speech, vocabulary.pronunciation].filter(Boolean).join(" · ")
    )}</p>
    <p class="word-definition">${escapeHtml(vocabulary.definition ?? "")}</p>
    ${
      vocabulary.etymology
        ? `<p class="word-etymology">${escapeHtml(vocabulary.etymology)}</p>`
        : ""
    }
    ${
      vocabulary.example
        ? `<p class="word-example">“${escapeHtml(vocabulary.example)}”</p>`
        : ""
    }
    ${
      vocabulary.source
        ? `<p class="word-source">${escapeHtml(vocabulary.source)}</p>`
        : ""
    }
  `;
}

function renderWeather(weather: WeatherSection): void {
  if (weather.status === "error" || weather.error) {
    weatherWidgetEl.className = "weather-widget error";
    weatherWidgetEl.textContent = weather.error ?? "Weather unavailable";
    return;
  }

  weatherWidgetEl.className = "weather-widget";
  weatherWidgetEl.innerHTML = `
    <p class="widget-label">${ICONS.cloud}<span>Weather</span></p>
    <div class="weather-row">
      <div>
        <p class="weather-city">${escapeHtml(weather.city ?? city)}</p>
        <p class="weather-desc">${escapeHtml(weather.description ?? "")}</p>
      </div>
      <div>
        <p class="weather-temp">${escapeHtml(weather.temp_c ?? "—")}°<span>C</span></p>
        <p class="weather-temp-f">${escapeHtml(weather.temp_f ?? "—")}°F</p>
      </div>
    </div>
  `;
}

function renderNewsCard(article: NewsArticle): string {
  const meta = [article.source, article.published].filter(Boolean).join(" · ");
  const href = article.url ? escapeHtml(article.url) : "#";
  const attrs = article.url
    ? `href="${href}" target="_blank" rel="noopener noreferrer"`
    : `href="#" aria-disabled="true"`;

  return `
    <a class="news-card" ${attrs}>
      <p class="news-title">${escapeHtml(article.title)}</p>
      <p class="news-meta">
        <span>${escapeHtml(meta || "Headline")}</span>
        ${ICONS.arrow}
      </p>
    </a>
  `;
}

function renderGithubRepo(repo: GithubRepo): string {
  const stats = [
    repo.language ? `<span class="repo-lang">${escapeHtml(repo.language)}</span>` : "",
    repo.stars != null ? `<span>★ ${escapeHtml(repo.stars.toLocaleString())}</span>` : "",
    repo.forks != null ? `<span>${escapeHtml(repo.forks.toLocaleString())} forks</span>` : "",
    repo.change ? `<span class="repo-change">${escapeHtml(repo.change)}</span>` : "",
  ].filter(Boolean);

  return `
    <li class="repo-item">
      <a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer" class="repo-name">${escapeHtml(repo.name)}</a>
      ${repo.description ? `<p class="repo-desc">${escapeHtml(repo.description)}</p>` : ""}
      ${stats.length ? `<div class="repo-stats">${stats.join("")}</div>` : ""}
    </li>
  `;
}

function renderGithub(github: GithubSection): void {
  const content =
    github.status === "error"
      ? `<p class="panel-error">${escapeHtml(github.error ?? "GitHub unavailable")}</p>`
      : github.repos.length
        ? `<ul class="repo-list">${github.repos.map(renderGithubRepo).join("")}</ul>`
        : `<div class="empty-state">No trending repositories found.</div>`;

  githubPanelEl.innerHTML = `
    <div class="panel-head">
      ${ICONS.fork}
      <h3>Trending on GitHub</h3>
      ${github.provider ? `<span class="side">${escapeHtml(github.provider)}</span>` : ""}
    </div>
    <div class="github-scroll">${content}</div>
  `;
}

function renderDashboard(data: DashboardResponse): void {
  greetingEl.textContent = data.greeting;
  dateEl.textContent = data.date;
  renderVocabulary(data.vocabulary);
  renderWeather(data.weather);
  renderGithub(data.github);

  const newsArticles =
    data.news.status === "error"
      ? `<p class="panel-error">${escapeHtml(data.news.error ?? "News unavailable")}</p>`
      : data.news.articles.length
        ? `<div class="news-grid">${data.news.articles.map(renderNewsCard).join("")}</div>`
        : `<div class="empty-state">No headlines found.</div>`;

  dashboardEl.innerHTML = `
    <div class="chip-row">
      <span class="chip">${escapeHtml(data.news.topic ?? newsTopic)}</span>
      ${
        data.news.provider
          ? `<span class="chip muted">${escapeHtml(data.news.provider)}</span>`
          : ""
      }
    </div>
    ${newsArticles}
  `;
}

async function loadDashboard(): Promise<void> {
  refreshBtn.classList.add("spinning");
  refreshBtn.disabled = true;
  refreshBtn.querySelector("span")!.textContent = "Refreshing…";

  dashboardEl.innerHTML = `<div class="dashboard-loading">Loading your daily briefing…</div>`;
  githubPanelEl.innerHTML = `<div class="dashboard-loading">Loading trending repos…</div>`;
  wordWidgetEl.className = "word-widget loading";
  wordWidgetEl.textContent = "Loading word of the day…";
  weatherWidgetEl.className = "weather-widget loading";
  weatherWidgetEl.textContent = "Loading weather…";

  try {
    const params = new URLSearchParams({ city, news_topic: newsTopic });
    const res = await fetch(`${API}/dashboard?${params}`);
    if (!res.ok) throw new Error(await res.text());
    renderDashboard((await res.json()) as DashboardResponse);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load dashboard";
    dashboardEl.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    githubPanelEl.innerHTML = `<p class="panel-error">${escapeHtml(message)}</p>`;
    wordWidgetEl.className = "word-widget error";
    wordWidgetEl.textContent = "Word unavailable";
    weatherWidgetEl.className = "weather-widget error";
    weatherWidgetEl.textContent = "Weather unavailable";
  } finally {
    refreshBtn.classList.remove("spinning");
    refreshBtn.disabled = false;
    refreshBtn.querySelector("span")!.textContent = "Refresh";
  }
}

function connect(): void {
  ws = new WebSocket(wsUrl());

  ws.addEventListener("open", () => {
    setConnectionStatus(`Live · ${threadId.slice(0, 8)}`);
    updateSendEnabled();
  });

  ws.addEventListener("close", () => {
    setConnectionStatus("Reconnecting…", false);
    updateSendEnabled();
    setTimeout(connect, 2000);
  });

  ws.addEventListener("error", () => {
    setConnectionStatus("Connection error", false);
  });

  ws.addEventListener("message", (event) => {
    handleServerEvent(JSON.parse(event.data as string) as ServerEvent);
  });
}

function handleServerEvent(data: ServerEvent): void {
  switch (data.type) {
    case "connected":
      setConnectionStatus(`Live · ${data.thread_id.slice(0, 8)}`);
      break;
    case "start":
      streaming = true;
      replyBuffer = "";
      updateSendEnabled();
      setChatStatus("Agent is thinking…");
      break;
    case "token":
      replyBuffer += data.content;
      setChatStatus("Agent is responding…");
      break;
    case "tool_start":
      setChatStatus(`Using ${data.name}…`);
      break;
    case "tool_end":
      setChatStatus(`${data.name} finished`);
      break;
    case "done": {
      streaming = false;
      const text = data.response || replyBuffer;
      messages.push({ role: "assistant", content: text || "Done." });
      renderChat();
      setChatStatus("");
      updateSendEnabled();
      break;
    }
    case "error":
      streaming = false;
      messages.push({ role: "assistant", content: data.message });
      renderChat();
      setChatStatus("");
      updateSendEnabled();
      break;
    case "pong":
      break;
  }
}

function sendMessage(): void {
  const message = messageEl.value.trim();
  if (!message || !ws || ws.readyState !== WebSocket.OPEN || streaming) return;

  messages.push({ role: "user", content: message });
  renderChat();
  messageEl.value = "";
  updateSendEnabled();

  ws.send(JSON.stringify({ type: "chat", message }));
}

suggestionsEl.innerHTML = SUGGESTIONS.map(
  (text) => `<button type="button" class="suggestion" data-suggestion="${escapeHtml(text)}">${escapeHtml(text)}</button>`
).join("");

suggestionsEl.addEventListener("click", (event) => {
  const target = event.target as HTMLElement | null;
  const button = target?.closest<HTMLButtonElement>("[data-suggestion]");
  if (!button) return;
  messageEl.value = button.dataset.suggestion ?? "";
  messageEl.focus();
  updateSendEnabled();
});

themeToggleBtn.addEventListener("click", () => toggleTheme());
sendBtn.addEventListener("click", () => sendMessage());
refreshBtn.addEventListener("click", () => void loadDashboard());
messageEl.addEventListener("input", () => updateSendEnabled());
messageEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

syncThemeToggle();
renderChat();
connect();
void loadDashboard();
