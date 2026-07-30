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

const threadId = `web-${crypto.randomUUID()}`;
const city = localStorage.getItem("dashboard_city") ?? "London";
const newsTopic = localStorage.getItem("dashboard_news_topic") ?? "technology";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Missing #app");

app.className = "layout";
app.innerHTML = `
  <header class="header">
    <div class="header-main">
      <p class="eyebrow">Daily Agent Hub</p>
      <h1 id="greeting">Good day</h1>
      <p id="date" class="muted"></p>
    </div>
    <div class="header-side">
      <div class="header-widgets">
        <div id="word-widget" class="word-widget loading">Loading word…</div>
        <div id="weather-widget" class="weather-widget loading">Loading weather…</div>
      </div>
      <p id="status" class="status">Connecting…</p>
    </div>
  </header>

  <section class="section">
    <div class="section-head">
      <div>
        <h2>Today</h2>
        <p class="muted section-sub">Latest headlines</p>
      </div>
      <button id="refresh-dashboard" type="button" class="ghost">Refresh</button>
    </div>

    <div id="dashboard" class="dashboard">
      <div class="dashboard-loading">Loading your daily briefing…</div>
    </div>
  </section>

  <section class="section chat-section">
    <div class="section-head">
      <h2>Agent chat</h2>
      <span class="muted">Ask your agents anything</span>
    </div>
    <div class="chat-github-row">
      <div class="chat-panel">
        <div id="chat-log" class="chat-log"></div>
        <div id="chat-status" class="chat-status"></div>
        <div class="chat-input-row">
          <textarea id="message" rows="2" placeholder="What's on your mind? Weather, news, repos, planning…"></textarea>
          <button id="send" type="button">Send</button>
        </div>
      </div>
      <aside id="github-panel" class="github-panel dashboard-block">
        <div class="dashboard-loading">Loading trending repos…</div>
      </aside>
    </div>
  </section>
`;

const greetingEl = document.querySelector<HTMLHeadingElement>("#greeting")!;
const dateEl = document.querySelector<HTMLParagraphElement>("#date")!;
const statusEl = document.querySelector<HTMLParagraphElement>("#status")!;
const weatherWidgetEl = document.querySelector<HTMLDivElement>("#weather-widget")!;
const wordWidgetEl = document.querySelector<HTMLDivElement>("#word-widget")!;
const dashboardEl = document.querySelector<HTMLDivElement>("#dashboard")!;
const githubPanelEl = document.querySelector<HTMLElement>("#github-panel")!;
const refreshBtn = document.querySelector<HTMLButtonElement>("#refresh-dashboard")!;
const chatLogEl = document.querySelector<HTMLDivElement>("#chat-log")!;
const chatStatusEl = document.querySelector<HTMLDivElement>("#chat-status")!;
const messageEl = document.querySelector<HTMLTextAreaElement>("#message")!;
const sendBtn = document.querySelector<HTMLButtonElement>("#send")!;

let ws: WebSocket | null = null;
let streaming = false;
let replyBuffer = "";
const messages: ChatMessage[] = [
  {
    role: "system",
    content: "Connected to your daily agents. Routing happens in the background.",
  },
];

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({ thread_id: threadId });
  return `${proto}//${location.host}${API}/chat/ws?${params}`;
}

function setConnectionStatus(text: string, ok = true): void {
  statusEl.textContent = text;
  statusEl.className = ok ? "status ok" : "status err";
}

function setChatStatus(text: string): void {
  chatStatusEl.textContent = text;
}

function renderChat(): void {
  chatLogEl.innerHTML = messages
    .map(
      (m) => `
        <article class="bubble bubble-${m.role}">
          <span class="bubble-label">${m.role === "user" ? "You" : m.role === "assistant" ? "Agent" : "System"}</span>
          <div class="bubble-body">${escapeHtml(m.content)}</div>
        </article>
      `
    )
    .join("");
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function weatherIcon(description: string): string {
  const value = description.toLowerCase();
  if (value.includes("rain") || value.includes("drizzle")) return "🌧️";
  if (value.includes("snow")) return "❄️";
  if (value.includes("cloud") || value.includes("overcast")) return "☁️";
  if (value.includes("clear") || value.includes("sun")) return "☀️";
  if (value.includes("mist") || value.includes("fog")) return "🌫️";
  return "🌤️";
}

function renderVocabulary(vocabulary: VocabularySection): void {
  if (vocabulary.status === "error" || vocabulary.error) {
    wordWidgetEl.className = "word-widget error";
    wordWidgetEl.innerHTML = `
      <p class="word-label">Word of the day</p>
      <p class="word-error">${escapeHtml(vocabulary.error ?? "Word unavailable")}</p>
    `;
    return;
  }

  wordWidgetEl.className = "word-widget";
  wordWidgetEl.innerHTML = `
    <div class="word-header">
      <p class="word-label">Word of the day</p>
      ${vocabulary.source ? `<span class="word-source">${escapeHtml(vocabulary.source)}</span>` : ""}
    </div>
    <div class="word-body">
      <div class="word-primary">
        <p class="word-title">${escapeHtml(vocabulary.word ?? "")}</p>
        <p class="word-meta">${escapeHtml(
          [vocabulary.part_of_speech, vocabulary.pronunciation].filter(Boolean).join(" · ")
        )}</p>
      </div>
      <div class="word-copy">
        <p class="word-definition">${escapeHtml(vocabulary.definition ?? "")}</p>
        ${vocabulary.etymology ? `<p class="word-etymology">${escapeHtml(vocabulary.etymology)}</p>` : ""}
      </div>
      ${vocabulary.example ? `<blockquote class="word-example">${escapeHtml(vocabulary.example)}</blockquote>` : ""}
    </div>
  `;
}

function renderWeather(weather: WeatherSection): void {
  if (weather.status === "error" || weather.error) {
    weatherWidgetEl.className = "weather-widget error";
    weatherWidgetEl.innerHTML = `
      <span class="weather-icon">⚠️</span>
      <div class="weather-copy">
        <p class="weather-city">${escapeHtml(weather.city ?? city)}</p>
        <p class="weather-desc">${escapeHtml(weather.error ?? "Weather unavailable")}</p>
      </div>
    `;
    return;
  }

  weatherWidgetEl.className = "weather-widget";
  weatherWidgetEl.innerHTML = `
    <span class="weather-icon">${weatherIcon(weather.description ?? "")}</span>
    <div class="weather-copy">
      <p class="weather-city">${escapeHtml(weather.city ?? city)}</p>
      <p class="weather-temp">${escapeHtml(weather.temp_c ?? "—")}°C · ${escapeHtml(weather.temp_f ?? "—")}°F</p>
      <p class="weather-desc">${escapeHtml(weather.description ?? "")}</p>
    </div>
  `;
}

function renderNewsCard(article: NewsArticle): string {
  const meta = [article.source, article.published].filter(Boolean).join(" · ");
  const title = article.url
    ? `<a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(article.title)}</a>`
    : escapeHtml(article.title);

  return `
    <article class="news-card">
      ${meta ? `<p class="news-meta">${escapeHtml(meta)}</p>` : ""}
      <h3 class="news-title">${title}</h3>
    </article>
  `;
}

function renderGithubRepo(repo: GithubRepo): string {
  const stats = [
    repo.change,
    repo.stars ? `${repo.stars.toLocaleString()} stars` : "",
    repo.forks ? `${repo.forks.toLocaleString()} forks` : "",
  ].filter(Boolean);

  return `
    <li class="repo-item">
      <a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer" class="repo-name">${escapeHtml(repo.name)}</a>
      ${repo.language ? `<span class="repo-lang">${escapeHtml(repo.language)}</span>` : ""}
      ${stats.length ? `<p class="repo-stats">${escapeHtml(stats.join(" · "))}</p>` : ""}
      ${repo.description ? `<p class="repo-desc">${escapeHtml(repo.description)}</p>` : ""}
    </li>
  `;
}

function renderGithub(github: GithubSection): void {
  const content =
    github.status === "error"
      ? `<p class="panel-error">${escapeHtml(github.error ?? "GitHub unavailable")}</p>`
      : github.repos.length
        ? `<ul class="repo-list">${github.repos.map(renderGithubRepo).join("")}</ul>`
        : `<p class="muted">No trending repositories found.</p>`;

  githubPanelEl.innerHTML = `
    <div class="block-head">
      <h3>GitHub trending</h3>
      ${github.provider ? `<span class="muted tiny">${escapeHtml(github.provider)}</span>` : ""}
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
        : `<p class="muted">No headlines found.</p>`;

  dashboardEl.innerHTML = `
    <section class="dashboard-block">
      <div class="block-head">
        <h3>News</h3>
        <span class="chip">${escapeHtml(data.news.topic ?? newsTopic)}</span>
        ${data.news.provider ? `<span class="muted tiny">${escapeHtml(data.news.provider)}</span>` : ""}
      </div>
      ${newsArticles}
    </section>
  `;
}

async function loadDashboard(): Promise<void> {
  dashboardEl.innerHTML = `<div class="dashboard-loading">Loading your daily briefing…</div>`;
  githubPanelEl.innerHTML = `<div class="dashboard-loading">Loading trending repos…</div>`;
  wordWidgetEl.className = "word-widget loading";
  wordWidgetEl.textContent = "Loading word…";
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
  }
}

function connect(): void {
  ws = new WebSocket(wsUrl());

  ws.addEventListener("open", () => {
    setConnectionStatus(`Live · ${threadId.slice(0, 8)}`);
    sendBtn.disabled = false;
  });

  ws.addEventListener("close", () => {
    setConnectionStatus("Reconnecting…", false);
    sendBtn.disabled = true;
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
      sendBtn.disabled = true;
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
      sendBtn.disabled = false;
      const text = data.response || replyBuffer;
      messages.push({ role: "assistant", content: text || "Done." });
      renderChat();
      setChatStatus("");
      break;
    }
    case "error":
      streaming = false;
      sendBtn.disabled = false;
      messages.push({ role: "assistant", content: data.message });
      renderChat();
      setChatStatus("");
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

  ws.send(JSON.stringify({ type: "chat", message }));
}

sendBtn.addEventListener("click", () => sendMessage());
refreshBtn.addEventListener("click", () => void loadDashboard());
messageEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

renderChat();
connect();
void loadDashboard();
