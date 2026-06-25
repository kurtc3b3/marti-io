(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))m(s);new MutationObserver(s=>{for(const n of s)if(n.type==="childList")for(const h of n.addedNodes)h.tagName==="LINK"&&h.rel==="modulepreload"&&m(h)}).observe(document,{childList:!0,subtree:!0});function k(s){const n={};return s.integrity&&(n.integrity=s.integrity),s.referrerPolicy&&(n.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?n.credentials="include":s.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function m(s){if(s.ep)return;s.ep=!0;const n=k(s);fetch(s.href,n)}})();const S="/api",L=`web-${crypto.randomUUID()}`,q=localStorage.getItem("dashboard_city")??"London",y=document.querySelector("#app");if(!y)throw new Error("Missing #app");y.className="layout";y.innerHTML=`
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
`;const A=document.querySelector("#greeting"),C=document.querySelector("#date"),v=document.querySelector("#status"),g=document.querySelector("#dashboard"),x=document.querySelector("#refresh-dashboard"),p=document.querySelector("#chat-log"),O=document.querySelector("#chat-status"),b=document.querySelector("#message"),a=document.querySelector("#send");let r=null,c=!1,f="";const d=[{role:"system",content:"Connected to your daily agents. Routing happens in the background."}];function N(){const e=location.protocol==="https:"?"wss:":"ws:",t=new URLSearchParams({thread_id:L});return`${e}//${location.host}${S}/chat/ws?${t}`}function i(e,t=!0){v.textContent=e,v.className=t?"status ok":"status err"}function o(e){O.textContent=e}function l(){p.innerHTML=d.map(e=>`
        <article class="bubble bubble-${e.role}">
          <span class="bubble-label">${e.role==="user"?"You":e.role==="assistant"?"Agent":"System"}</span>
          <div class="bubble-body">${u(e.content)}</div>
        </article>
      `).join(""),p.scrollTop=p.scrollHeight}function u(e){return e.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")}function P(e){A.textContent=e.greeting,C.textContent=e.date,g.innerHTML=e.cards.map(t=>`
        <article class="dash-card ${t.status==="error"?"dash-card-error":""}">
          <h3>${u(t.title)}</h3>
          <p>${u(t.content)}</p>
        </article>
      `).join("")}async function w(){g.textContent="Loading daily cards…";try{const e=new URLSearchParams({city:q}),t=await fetch(`${S}/dashboard?${e}`);if(!t.ok)throw new Error(await t.text());P(await t.json())}catch(e){g.innerHTML=`<p class="error">${u(e instanceof Error?e.message:"Failed to load dashboard")}</p>`}}function E(){r=new WebSocket(N()),r.addEventListener("open",()=>{i(`Live · ${L.slice(0,8)}`),a.disabled=!1}),r.addEventListener("close",()=>{i("Reconnecting…",!1),a.disabled=!0,setTimeout(E,2e3)}),r.addEventListener("error",()=>{i("Connection error",!1)}),r.addEventListener("message",e=>{H(JSON.parse(e.data))})}function H(e){switch(e.type){case"connected":i(`Live · ${e.thread_id.slice(0,8)}`);break;case"start":c=!0,f="",a.disabled=!0,o("Agent is thinking…");break;case"token":f+=e.content,o("Agent is responding…");break;case"tool_start":o(`Using ${e.name}…`);break;case"tool_end":o(`${e.name} finished`);break;case"done":{c=!1,a.disabled=!1;const t=e.response||f;d.push({role:"assistant",content:t||"Done."}),l(),o("");break}case"error":c=!1,a.disabled=!1,d.push({role:"assistant",content:e.message}),l(),o("");break}}function $(){const e=b.value.trim();!e||!r||r.readyState!==WebSocket.OPEN||c||(d.push({role:"user",content:e}),l(),b.value="",r.send(JSON.stringify({type:"chat",message:e})))}a.addEventListener("click",()=>$());x.addEventListener("click",()=>void w());b.addEventListener("keydown",e=>{e.key==="Enter"&&!e.shiftKey&&(e.preventDefault(),$())});l();E();w();
