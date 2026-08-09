(function(){const s=document.createElement("link").relList;if(s&&s.supports&&s.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))w(n);new MutationObserver(n=>{for(const a of n)if(a.type==="childList")for(const b of a.addedNodes)b.tagName==="LINK"&&b.rel==="modulepreload"&&w(b)}).observe(document,{childList:!0,subtree:!0});function u(n){const a={};return n.integrity&&(a.integrity=n.integrity),n.referrerPolicy&&(a.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?a.credentials="include":n.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function w(n){if(n.ep)return;n.ep=!0;const a=u(n);fetch(n.href,a)}})();const C="/api",r={sparkles:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.107 5.568a2 2 0 0 0 1.535 1.535l5.568 1.107a1 1 0 0 1 0 1.966l-5.568 1.107a2 2 0 0 0-1.535 1.535l-1.107 5.568a1 1 0 0 1-1.966 0l-1.107-5.568a2 2 0 0 0-1.535-1.535l-5.568-1.107a1 1 0 0 1 0-1.966l5.568-1.107a2 2 0 0 0 1.535-1.535z"/><path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/></svg>',book:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg>',cloud:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="M20 12h2"/><path d="m19.07 4.93-1.41 1.41"/><path d="M15.947 12.65a4 4 0 0 0-5.925-4.128"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6z"/></svg>',refresh:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>',send:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/></svg>',wand:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9h2"/><path d="M20 9h2"/><path d="M17.8 11.8 19 13"/><path d="M15 9h.01"/><path d="M17.8 6.2 19 5"/><path d="m3 21 9-9"/><path d="M12.2 6.2 11 5"/></svg>',fork:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/></svg>',arrow:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 7h10v10"/><path d="M7 17 17 7"/></svg>',sun:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>',moon:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>'},P=["What's the weather today?","Summarize the top tech news","What's trending on GitHub?"],H=`web-${crypto.randomUUID()}`,T=localStorage.getItem("dashboard_city")??"London",N=localStorage.getItem("dashboard_news_topic")??"technology",S=document.querySelector("#app");if(!S)throw new Error("Missing #app");S.className="shell";S.innerHTML=`
  <header class="header animate-fade-up">
    <div class="topbar">
      <div class="brand">
        <span class="brand-mark">${r.sparkles}</span>
        <span class="brand-name">Marti</span>
        <span class="brand-tag">Daily Agent Hub</span>
      </div>
      <div class="topbar-actions">
        <span id="status" class="status-pill">
          <span class="status-dot" aria-hidden="true"></span>
          <span class="label">Connecting…</span>
        </span>
        <button id="theme-toggle" class="icon-btn" type="button" aria-label="Toggle theme">
          ${r.moon}
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
        ${r.refresh}
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
        <span class="accent-icon">${r.wand}</span>
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
            ${r.send}
          </button>
        </div>
      </div>
    </div>
    <aside id="github-panel" class="github-panel">
      <div class="dashboard-loading">Loading trending repos…</div>
    </aside>
  </section>
`;const G=document.querySelector("#greeting"),I=document.querySelector("#date"),E=document.querySelector("#status"),$=document.querySelector("#theme-toggle"),i=document.querySelector("#weather-widget"),d=document.querySelector("#word-widget"),M=document.querySelector("#dashboard"),L=document.querySelector("#github-panel"),c=document.querySelector("#refresh-dashboard"),k=document.querySelector("#chat-log"),x=document.querySelector("#chat-status"),p=document.querySelector("#message"),q=document.querySelector("#send"),j=document.querySelector("#suggestions");let o=null,g=!1,y="";const m=[{role:"system",content:"Connected to your daily agents. Ask about weather, news, repos, or anything else."}];function t(e){return e.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;")}function D(){const e=location.protocol==="https:"?"wss:":"ws:",s=new URLSearchParams({thread_id:H});return`${e}//${location.host}${C}/chat/ws?${s}`}function B(){return document.documentElement.classList.contains("dark")}function A(){const e=B();$.innerHTML=e?r.sun:r.moon,$.setAttribute("aria-label",e?"Switch to light theme":"Switch to dark theme")}function R(){const e=!B();document.documentElement.classList.toggle("dark",e),localStorage.setItem("marti_theme",e?"dark":"light"),A()}function v(e,s=!0){E.className=s?"status-pill ok":"status-pill err",E.innerHTML=`
    <span class="status-dot" aria-hidden="true"></span>
    <span class="label">${t(e)}</span>
  `}function h(e){if(!e){x.textContent="";return}x.innerHTML=`
    <span class="pulse" aria-hidden="true"></span>
    <span>${t(e)}</span>
  `}function l(){q.disabled=!p.value.trim()||!o||o.readyState!==WebSocket.OPEN||g}function f(){k.innerHTML=m.map(e=>`
        <div class="bubble-row ${e.role}">
          <div class="bubble bubble-${e.role}">${t(e.content)}</div>
        </div>
      `).join(""),k.scrollTop=k.scrollHeight}function U(e){if(e.status==="error"||e.error){d.className="word-widget error",d.textContent=e.error??"Word unavailable";return}d.className="word-widget",d.innerHTML=`
    <p class="widget-label">${r.book}<span>Word of the day</span></p>
    <p class="word-title">${t(e.word??"")}</p>
    <p class="word-meta">${t([e.part_of_speech,e.pronunciation].filter(Boolean).join(" · "))}</p>
    <p class="word-definition">${t(e.definition??"")}</p>
    ${e.etymology?`<p class="word-etymology">${t(e.etymology)}</p>`:""}
    ${e.example?`<p class="word-example">“${t(e.example)}”</p>`:""}
    ${e.source?`<p class="word-source">${t(e.source)}</p>`:""}
  `}function z(e){if(e.status==="error"||e.error){i.className="weather-widget error",i.textContent=e.error??"Weather unavailable";return}i.className="weather-widget",i.innerHTML=`
    <p class="widget-label">${r.cloud}<span>Weather</span></p>
    <div class="weather-row">
      <div>
        <p class="weather-city">${t(e.city??T)}</p>
        <p class="weather-desc">${t(e.description??"")}</p>
      </div>
      <div>
        <p class="weather-temp">${t(e.temp_c??"—")}°<span>C</span></p>
        <p class="weather-temp-f">${t(e.temp_f??"—")}°F</p>
      </div>
    </div>
  `}function V(e){const s=[e.source,e.published].filter(Boolean).join(" · "),u=e.url?t(e.url):"#";return`
    <a class="news-card" ${e.url?`href="${u}" target="_blank" rel="noopener noreferrer"`:'href="#" aria-disabled="true"'}>
      <p class="news-title">${t(e.title)}</p>
      <p class="news-meta">
        <span>${t(s||"Headline")}</span>
        ${r.arrow}
      </p>
    </a>
  `}function F(e){const s=[e.language?`<span class="repo-lang">${t(e.language)}</span>`:"",e.stars!=null?`<span>★ ${t(e.stars.toLocaleString())}</span>`:"",e.forks!=null?`<span>${t(e.forks.toLocaleString())} forks</span>`:"",e.change?`<span class="repo-change">${t(e.change)}</span>`:""].filter(Boolean);return`
    <li class="repo-item">
      <a href="${t(e.url)}" target="_blank" rel="noopener noreferrer" class="repo-name">${t(e.name)}</a>
      ${e.description?`<p class="repo-desc">${t(e.description)}</p>`:""}
      ${s.length?`<div class="repo-stats">${s.join("")}</div>`:""}
    </li>
  `}function J(e){const s=e.status==="error"?`<p class="panel-error">${t(e.error??"GitHub unavailable")}</p>`:e.repos.length?`<ul class="repo-list">${e.repos.map(F).join("")}</ul>`:'<div class="empty-state">No trending repositories found.</div>';L.innerHTML=`
    <div class="panel-head">
      ${r.fork}
      <h3>Trending on GitHub</h3>
      ${e.provider?`<span class="side">${t(e.provider)}</span>`:""}
    </div>
    <div class="github-scroll">${s}</div>
  `}function K(e){G.textContent=e.greeting,I.textContent=e.date,U(e.vocabulary),z(e.weather),J(e.github);const s=e.news.status==="error"?`<p class="panel-error">${t(e.news.error??"News unavailable")}</p>`:e.news.articles.length?`<div class="news-grid">${e.news.articles.map(V).join("")}</div>`:'<div class="empty-state">No headlines found.</div>';M.innerHTML=`
    <div class="chip-row">
      <span class="chip">${t(e.news.topic??N)}</span>
      ${e.news.provider?`<span class="chip muted">${t(e.news.provider)}</span>`:""}
    </div>
    ${s}
  `}async function _(){c.classList.add("spinning"),c.disabled=!0,c.querySelector("span").textContent="Refreshing…",M.innerHTML='<div class="dashboard-loading">Loading your daily briefing…</div>',L.innerHTML='<div class="dashboard-loading">Loading trending repos…</div>',d.className="word-widget loading",d.textContent="Loading word of the day…",i.className="weather-widget loading",i.textContent="Loading weather…";try{const e=new URLSearchParams({city:T,news_topic:N}),s=await fetch(`${C}/dashboard?${e}`);if(!s.ok)throw new Error(await s.text());K(await s.json())}catch(e){const s=e instanceof Error?e.message:"Failed to load dashboard";M.innerHTML=`<p class="error">${t(s)}</p>`,L.innerHTML=`<p class="panel-error">${t(s)}</p>`,d.className="word-widget error",d.textContent="Word unavailable",i.className="weather-widget error",i.textContent="Weather unavailable"}finally{c.classList.remove("spinning"),c.disabled=!1,c.querySelector("span").textContent="Refresh"}}function W(){o=new WebSocket(D()),o.addEventListener("open",()=>{v(`Live · ${H.slice(0,8)}`),l()}),o.addEventListener("close",()=>{v("Reconnecting…",!1),l(),setTimeout(W,2e3)}),o.addEventListener("error",()=>{v("Connection error",!1)}),o.addEventListener("message",e=>{Z(JSON.parse(e.data))})}function Z(e){switch(e.type){case"connected":v(`Live · ${e.thread_id.slice(0,8)}`);break;case"start":g=!0,y="",l(),h("Agent is thinking…");break;case"token":y+=e.content,h("Agent is responding…");break;case"tool_start":h(`Using ${e.name}…`);break;case"tool_end":h(`${e.name} finished`);break;case"done":{g=!1;const s=e.response||y;m.push({role:"assistant",content:s||"Done."}),f(),h(""),l();break}case"error":g=!1,m.push({role:"assistant",content:e.message}),f(),h(""),l();break}}function O(){const e=p.value.trim();!e||!o||o.readyState!==WebSocket.OPEN||g||(m.push({role:"user",content:e}),f(),p.value="",l(),o.send(JSON.stringify({type:"chat",message:e})))}j.innerHTML=P.map(e=>`<button type="button" class="suggestion" data-suggestion="${t(e)}">${t(e)}</button>`).join("");j.addEventListener("click",e=>{const s=e.target,u=s==null?void 0:s.closest("[data-suggestion]");u&&(p.value=u.dataset.suggestion??"",p.focus(),l())});$.addEventListener("click",()=>R());q.addEventListener("click",()=>O());c.addEventListener("click",()=>void _());p.addEventListener("input",()=>l());p.addEventListener("keydown",e=>{e.key==="Enter"&&!e.shiftKey&&(e.preventDefault(),O())});A();f();W();_();
