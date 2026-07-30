(function(){const s=document.createElement("link").relList;if(s&&s.supports&&s.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))S(n);new MutationObserver(n=>{for(const r of n)if(r.type==="childList")for(const w of r.addedNodes)w.tagName==="LINK"&&w.rel==="modulepreload"&&S(w)}).observe(document,{childList:!0,subtree:!0});function g(n){const r={};return n.integrity&&(r.integrity=n.integrity),n.referrerPolicy&&(r.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?r.credentials="include":n.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function S(n){if(n.ep)return;n.ep=!0;const r=g(n);fetch(n.href,r)}})();const E="/api",N=`web-${crypto.randomUUID()}`,v=localStorage.getItem("dashboard_city")??"London",q=localStorage.getItem("dashboard_news_topic")??"technology",L=document.querySelector("#app");if(!L)throw new Error("Missing #app");L.className="layout";L.innerHTML=`
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
`;const x=document.querySelector("#greeting"),M=document.querySelector("#date"),k=document.querySelector("#status"),a=document.querySelector("#weather-widget"),i=document.querySelector("#word-widget"),b=document.querySelector("#dashboard"),y=document.querySelector("#github-panel"),_=document.querySelector("#refresh-dashboard"),f=document.querySelector("#chat-log"),A=document.querySelector("#chat-status"),$=document.querySelector("#message"),d=document.querySelector("#send");let o=null,l=!1,m="";const p=[{role:"system",content:"Connected to your daily agents. Routing happens in the background."}];function W(){const e=location.protocol==="https:"?"wss:":"ws:",s=new URLSearchParams({thread_id:N});return`${e}//${location.host}${E}/chat/ws?${s}`}function u(e,s=!0){k.textContent=e,k.className=s?"status ok":"status err"}function c(e){A.textContent=e}function h(){f.innerHTML=p.map(e=>`
        <article class="bubble bubble-${e.role}">
          <span class="bubble-label">${e.role==="user"?"You":e.role==="assistant"?"Agent":"System"}</span>
          <div class="bubble-body">${t(e.content)}</div>
        </article>
      `).join(""),f.scrollTop=f.scrollHeight}function t(e){return e.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;")}function O(e){const s=e.toLowerCase();return s.includes("rain")||s.includes("drizzle")?"🌧️":s.includes("snow")?"❄️":s.includes("cloud")||s.includes("overcast")?"☁️":s.includes("clear")||s.includes("sun")?"☀️":s.includes("mist")||s.includes("fog")?"🌫️":"🌤️"}function P(e){if(e.status==="error"||e.error){i.className="word-widget error",i.innerHTML=`
      <p class="word-label">Word of the day</p>
      <p class="word-error">${t(e.error??"Word unavailable")}</p>
    `;return}i.className="word-widget",i.innerHTML=`
    <div class="word-header">
      <p class="word-label">Word of the day</p>
      ${e.source?`<span class="word-source">${t(e.source)}</span>`:""}
    </div>
    <div class="word-body">
      <div class="word-primary">
        <p class="word-title">${t(e.word??"")}</p>
        <p class="word-meta">${t([e.part_of_speech,e.pronunciation].filter(Boolean).join(" · "))}</p>
      </div>
      <div class="word-copy">
        <p class="word-definition">${t(e.definition??"")}</p>
        ${e.etymology?`<p class="word-etymology">${t(e.etymology)}</p>`:""}
      </div>
      ${e.example?`<blockquote class="word-example">${t(e.example)}</blockquote>`:""}
    </div>
  `}function j(e){if(e.status==="error"||e.error){a.className="weather-widget error",a.innerHTML=`
      <span class="weather-icon">⚠️</span>
      <div class="weather-copy">
        <p class="weather-city">${t(e.city??v)}</p>
        <p class="weather-desc">${t(e.error??"Weather unavailable")}</p>
      </div>
    `;return}a.className="weather-widget",a.innerHTML=`
    <span class="weather-icon">${O(e.description??"")}</span>
    <div class="weather-copy">
      <p class="weather-city">${t(e.city??v)}</p>
      <p class="weather-temp">${t(e.temp_c??"—")}°C · ${t(e.temp_f??"—")}°F</p>
      <p class="weather-desc">${t(e.description??"")}</p>
    </div>
  `}function I(e){const s=[e.source,e.published].filter(Boolean).join(" · "),g=e.url?`<a href="${t(e.url)}" target="_blank" rel="noopener noreferrer">${t(e.title)}</a>`:t(e.title);return`
    <article class="news-card">
      ${s?`<p class="news-meta">${t(s)}</p>`:""}
      <h3 class="news-title">${g}</h3>
    </article>
  `}function B(e){const s=[e.change,e.stars?`${e.stars.toLocaleString()} stars`:"",e.forks?`${e.forks.toLocaleString()} forks`:""].filter(Boolean);return`
    <li class="repo-item">
      <a href="${t(e.url)}" target="_blank" rel="noopener noreferrer" class="repo-name">${t(e.name)}</a>
      ${e.language?`<span class="repo-lang">${t(e.language)}</span>`:""}
      ${s.length?`<p class="repo-stats">${t(s.join(" · "))}</p>`:""}
      ${e.description?`<p class="repo-desc">${t(e.description)}</p>`:""}
    </li>
  `}function D(e){const s=e.status==="error"?`<p class="panel-error">${t(e.error??"GitHub unavailable")}</p>`:e.repos.length?`<ul class="repo-list">${e.repos.map(B).join("")}</ul>`:'<p class="muted">No trending repositories found.</p>';y.innerHTML=`
    <div class="block-head">
      <h3>GitHub trending</h3>
      ${e.provider?`<span class="muted tiny">${t(e.provider)}</span>`:""}
    </div>
    <div class="github-scroll">${s}</div>
  `}function R(e){x.textContent=e.greeting,M.textContent=e.date,P(e.vocabulary),j(e.weather),D(e.github);const s=e.news.status==="error"?`<p class="panel-error">${t(e.news.error??"News unavailable")}</p>`:e.news.articles.length?`<div class="news-grid">${e.news.articles.map(I).join("")}</div>`:'<p class="muted">No headlines found.</p>';b.innerHTML=`
    <section class="dashboard-block">
      <div class="block-head">
        <h3>News</h3>
        <span class="chip">${t(e.news.topic??q)}</span>
        ${e.news.provider?`<span class="muted tiny">${t(e.news.provider)}</span>`:""}
      </div>
      ${s}
    </section>
  `}async function C(){b.innerHTML='<div class="dashboard-loading">Loading your daily briefing…</div>',y.innerHTML='<div class="dashboard-loading">Loading trending repos…</div>',i.className="word-widget loading",i.textContent="Loading word…",a.className="weather-widget loading",a.textContent="Loading weather…";try{const e=new URLSearchParams({city:v,news_topic:q}),s=await fetch(`${E}/dashboard?${e}`);if(!s.ok)throw new Error(await s.text());R(await s.json())}catch(e){const s=e instanceof Error?e.message:"Failed to load dashboard";b.innerHTML=`<p class="error">${t(s)}</p>`,y.innerHTML=`<p class="panel-error">${t(s)}</p>`,i.className="word-widget error",i.textContent="Word unavailable",a.className="weather-widget error",a.textContent="Weather unavailable"}}function H(){o=new WebSocket(W()),o.addEventListener("open",()=>{u(`Live · ${N.slice(0,8)}`),d.disabled=!1}),o.addEventListener("close",()=>{u("Reconnecting…",!1),d.disabled=!0,setTimeout(H,2e3)}),o.addEventListener("error",()=>{u("Connection error",!1)}),o.addEventListener("message",e=>{U(JSON.parse(e.data))})}function U(e){switch(e.type){case"connected":u(`Live · ${e.thread_id.slice(0,8)}`);break;case"start":l=!0,m="",d.disabled=!0,c("Agent is thinking…");break;case"token":m+=e.content,c("Agent is responding…");break;case"tool_start":c(`Using ${e.name}…`);break;case"tool_end":c(`${e.name} finished`);break;case"done":{l=!1,d.disabled=!1;const s=e.response||m;p.push({role:"assistant",content:s||"Done."}),h(),c("");break}case"error":l=!1,d.disabled=!1,p.push({role:"assistant",content:e.message}),h(),c("");break}}function T(){const e=$.value.trim();!e||!o||o.readyState!==WebSocket.OPEN||l||(p.push({role:"user",content:e}),h(),$.value="",o.send(JSON.stringify({type:"chat",message:e})))}d.addEventListener("click",()=>T());_.addEventListener("click",()=>void C());$.addEventListener("keydown",e=>{e.key==="Enter"&&!e.shiftKey&&(e.preventDefault(),T())});h();H();C();
