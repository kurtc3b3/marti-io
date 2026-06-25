const API = "/api";

interface DashboardCard {
  id: string;
  title: string;
  content: string;
  status: string;
}

interface DashboardResponse {
  date: string;
  greeting: string;
  cards: DashboardCard[];
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

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Missing #app");

app.className = "layout";
app.innerHTML = `
  <header class="header">
    <div>
      <p class="eyebrow">Daily Agent Hub</p>
      <h1 id="greeting">Good day</h1>
      <p id="date" class="muted"></p>
    </div>
    <p id="status" class="status">Connecting…</p>
  </header>

  <section class="section">
    <div class="section-head">
      <h2>Today</h2>
      <button id="refresh-dashboard" type="button" class="ghost">Refresh</button>
    </div>
    <div id="dashboard" class="dashboard">Loading daily cards…</div>
  </section>

  <section class="section chat-section">
    <div class="section-head">
      <h2>Agent chat</h2>
      <span class="muted">Ask your agents anything</span>
    </div>
    <div class="chat-panel">
      <div id="chat-log" class="chat-log"></div>
      <div id="chat-status" class="chat-status"></div>
      <div class="chat-input-row">
        <textarea id="message" rows="2" placeholder="What's on your mind? Weather, news, repos, planning…"></textarea>
        <button id="send" type="button">Send</button>
      </div>
    </div>
  </section>
`;

const greetingEl = document.querySelector<HTMLHeadingElement>("#greeting")!;
const dateEl = document.querySelector<HTMLParagraphElement>("#date")!;
const statusEl = document.querySelector<HTMLParagraphElement>("#status")!;
const dashboardEl = document.querySelector<HTMLDivElement>("#dashboard")!;
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
    .replaceAll(">", "&gt;");
}

function renderDashboard(data: DashboardResponse): void {
  greetingEl.textContent = data.greeting;
  dateEl.textContent = data.date;
  dashboardEl.innerHTML = data.cards
    .map(
      (card) => `
        <article class="dash-card ${card.status === "error" ? "dash-card-error" : ""}">
          <h3>${escapeHtml(card.title)}</h3>
          <p>${escapeHtml(card.content)}</p>
        </article>
      `
    )
    .join("");
}

async function loadDashboard(): Promise<void> {
  dashboardEl.textContent = "Loading daily cards…";
  try {
    const params = new URLSearchParams({ city });
    const res = await fetch(`${API}/dashboard?${params}`);
    if (!res.ok) throw new Error(await res.text());
    renderDashboard((await res.json()) as DashboardResponse);
  } catch (error) {
    dashboardEl.innerHTML = `<p class="error">${escapeHtml(error instanceof Error ? error.message : "Failed to load dashboard")}</p>`;
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
