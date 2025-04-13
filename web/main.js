(() => {
  const $ = (id) => document.getElementById(id);
  const status = $("status");
  const editor = $("editor");
  const log = $("log");
  const docIdInput = $("docId");
  const btnCreate = $("btnCreate");
  const btnConnect = $("btnConnect");

  let ws = null;
  let suppressLocal = false;
  let lastText = "";

  function setStatus(t) { status.textContent = t; }
  function addLog(obj) {
    const line = document.createElement("div");
    line.textContent = `[${new Date().toLocaleTimeString()}] ${typeof obj === 'string' ? obj : JSON.stringify(obj)}`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
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
    setStatus("connecting...");
    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = (e) => addLog({ error: 'ws', details: e });
    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (data.type === 'snapshot') {
        suppressLocal = true;
        editor.value = data.text || "";
        lastText = editor.value;
        setTimeout(() => (suppressLocal = false), 0);
        addLog({ snapshot: { version: data.version } });
      } else if (data.type === 'doc.update') {
        suppressLocal = true;
        editor.value = data.text || "";
        lastText = editor.value;
        setTimeout(() => (suppressLocal = false), 0);
      } else if (data.type === 'ack') {
        // keep editor in sync with authoritative text if provided
        if (typeof data.text === 'string') {
          suppressLocal = true;
          editor.value = data.text;
          lastText = editor.value;
          setTimeout(() => (suppressLocal = false), 0);
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
      docIdInput.value = data.id;
      addLog({ create: data });
    } catch (e) {
      addLog({ error: 'create_failed', details: String(e) });
    }
  };

  btnConnect.onclick = () => {
    const docId = (docIdInput.value || '').trim();
    if (!docId) { alert('Enter a document ID or click Create'); return; }
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
})();

