(() => {
  const $ = (id) => document.getElementById(id);
  const status = $("status");
  const editor = $("editor");
  const log = $("log");
  const docIdInput = $("docId");
  const btnCreate = $("btnCreate");
  const btnConnect = $("btnConnect");
  const statusPill = $("status");
  const statusText = $("statusText");
  const activeDoc = $("activeDoc");
  const endpoint = $("endpoint");
  const howToToggle = $("howToToggle");
  const howToContent = $("howToContent");
  const howToPanel = howToContent ? howToContent.parentElement : null;

  const LAST_DOC_KEY = "rtc_last_doc_id";

  let ws = null;
  let suppressLocal = false;
  let lastText = "";
  const setActiveDoc = (id) => {
    const val = (id || "").trim();
    activeDoc.textContent = val || "None";
  };

  function setStatus(state, text) {
    statusText.textContent = text || state;
    statusPill.classList.remove("status-connected", "status-connecting");
    if (state === "connected") statusPill.classList.add("status-connected");
    else if (state === "connecting") statusPill.classList.add("status-connecting");
  }
  function addLog(obj) {
    const line = document.createElement("div");
    const ts = document.createElement("span");
    ts.className = "time";
    ts.textContent = new Date().toLocaleTimeString();
    const msg = document.createElement("span");
    msg.textContent = typeof obj === "string" ? obj : JSON.stringify(obj);
    line.appendChild(ts);
    line.appendChild(msg);
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  function setEditorText(nextText, { preserveSelection = false } = {}) {
    const text = typeof nextText === "string" ? nextText : "";
    if (editor.value === text) {
      lastText = text;
      return;
    }

    const active = document.activeElement === editor;
    const prevText = editor.value;
    const prevStart = editor.selectionStart ?? prevText.length;
    const prevEnd = editor.selectionEnd ?? prevText.length;
    const prefix = lcp(prevText, text);
    const suffix = lcs(prevText.slice(prefix), text.slice(prefix));
    const prevMidLen = prevText.length - prefix - suffix;
    const nextMidLen = text.length - prefix - suffix;

    editor.value = text;
    lastText = text;

    if (!preserveSelection || !active) return;

    const adjustIndex = (index) => {
      if (index <= prefix) return index;
      if (index >= prefix + prevMidLen) {
        return Math.max(prefix, index - prevMidLen + nextMidLen);
      }
      return prefix + nextMidLen;
    };

    const nextStart = Math.min(text.length, Math.max(0, adjustIndex(prevStart)));
    const nextEnd = Math.min(text.length, Math.max(nextStart, adjustIndex(prevEnd)));
    editor.setSelectionRange(nextStart, nextEnd);
  }

  function lcp(a, b) {
    const minLen = Math.min(a.length, b.length);
    let i = 0;
    while (i < minLen && a[i] === b[i]) i++;
    return i;
  }
  function lcs(a, b) {
    const minLen = Math.min(a.length, b.length);
    let i = 0;
    while (i < minLen && a[a.length - 1 - i] === b[b.length - 1 - i]) i++;
    return i;
  }

  function connect(docId) {
    if (ws) { ws.close(); ws = null; }
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/v1/ws/docs/${docId}`;
    ws = new WebSocket(url);
    setActiveDoc(docId);
    setStatus("connecting", "Connecting...");
    ws.onopen = () => setStatus("connected", "Connected");
    ws.onclose = () => setStatus("disconnected", "Disconnected");
    ws.onerror = (e) => addLog({ error: 'ws', details: e });
    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (data.type === 'snapshot') {
        suppressLocal = true;
        setEditorText(data.text || "");
        setTimeout(() => (suppressLocal = false), 0);
        addLog({ snapshot: { version: data.version } });
      } else if (data.type === 'doc.update') {
        suppressLocal = true;
        setEditorText(data.text || "", { preserveSelection: true });
        setTimeout(() => (suppressLocal = false), 0);
      } else if (data.type === 'ack') {
        // Do not overwrite local text from ACKs.
        // ACKs can arrive after newer keystrokes and would revert the editor
        // back to stale server text, which feels like input lag or broken caret behavior.
        if (typeof data.text === 'string' && data.text === editor.value) {
          lastText = data.text;
        }
      } else if (data.type === 'nack') {
        addLog({ nack: data });
      }
    };
  }

  btnCreate.onclick = async () => {
    try {
      const res = await fetch('/v1/docs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'Untitled' }) });
      const data = await res.json();
      const newId = String(data.id || "").trim();
      docIdInput.value = newId;
      setActiveDoc(newId);
      localStorage.setItem(LAST_DOC_KEY, newId);
      addLog({ create: data });
    } catch (e) {
      addLog({ error: 'create_failed', details: String(e) });
    }
  };

  btnConnect.onclick = () => {
    const docId = (docIdInput.value || '').trim();
    if (!docId) { alert('Enter a document ID or click Create'); return; }
    setActiveDoc(docId);
    localStorage.setItem(LAST_DOC_KEY, docId);
    connect(docId);
  };

  editor.addEventListener('input', () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (suppressLocal) return;
    const newText = editor.value;
    if (newText === lastText) return;

    const p = lcp(lastText, newText);
    const s = lcs(lastText.slice(p), newText.slice(p));
    const oldMid = lastText.slice(p, lastText.length - s);
    const newMid = newText.slice(p, newText.length - s);

    if (oldMid && !newMid) {
      // deletion
      ws.send(JSON.stringify({ type: 'edit.delete', index: p, length: oldMid.length }));
    } else if (!oldMid && newMid) {
      // insertion
      ws.send(JSON.stringify({ type: 'edit.insert', index: p, text: newMid }));
    } else {
      // replacement = delete then insert
      if (oldMid.length > 0) ws.send(JSON.stringify({ type: 'edit.delete', index: p, length: oldMid.length }));
      if (newMid.length > 0) ws.send(JSON.stringify({ type: 'edit.insert', index: p, text: newMid }));
    }

    lastText = newText; // optimistic
  });

  // Show endpoint info on load
  endpoint.textContent = `Target: ${location.origin}`;

  // Restore last doc id if present
  const storedDoc = localStorage.getItem(LAST_DOC_KEY);
  if (storedDoc) {
    const val = String(storedDoc || "").trim();
    docIdInput.value = val;
    setActiveDoc(val);
  } else if (docIdInput.value.trim()) {
    setActiveDoc(docIdInput.value.trim());
  }
  docIdInput.addEventListener("input", () => {
    const val = docIdInput.value.trim();
    setActiveDoc(val);
  });

  // Collapsible how-to
  if (howToToggle && howToContent) {
    howToToggle.addEventListener("click", () => {
      const isHidden = howToContent.classList.contains("collapsed");
      if (isHidden) {
        howToContent.classList.remove("collapsed");
        howToToggle.textContent = "Hide";
        if (howToPanel) howToPanel.classList.remove("collapsed");
      } else {
        howToContent.classList.add("collapsed");
        howToToggle.textContent = "Show";
        if (howToPanel) howToPanel.classList.add("collapsed");
      }
    });
  }
})();
