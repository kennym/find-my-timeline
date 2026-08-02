(() => {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  const section = document.createElement('div');
  section.className = 'section';
  section.innerHTML = `
    <h2>Apple Authentication</h2>
    <div id="auth-status" class="auth-status">Loading authentication status…</div>
    <p class="auth-help" title="Apple may invalidate a session before the estimated date.">The countdown is an estimate. Apple can expire a session earlier.</p>
    <button id="auth-open" class="auth-button" type="button">Re-authenticate</button>`;
  sidebar.appendChild(section);

  const modal = document.createElement('div');
  modal.className = 'auth-modal';
  modal.innerHTML = `
    <div class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <h2 id="auth-title">Renew Apple session</h2>
      <p id="auth-step">Enter the WebUI administrator password and your Apple ID password.</p>
      <label>WebUI administrator password<input id="auth-admin" type="password" autocomplete="current-password"></label>
      <label id="apple-password-row">Apple ID password<input id="auth-password" type="password" autocomplete="off"></label>
      <label id="auth-code-row" hidden>Apple verification code<input id="auth-code" inputmode="numeric" autocomplete="one-time-code" maxlength="8"></label>
      <p id="auth-error" class="auth-error"></p>
      <p class="auth-security">Passwords and verification codes are sent only to this server, are not written to the database, and must never be exposed through an unprotected internet-facing WebUI. Use HTTPS, a VPN, or an authenticated reverse proxy.</p>
      <div class="auth-actions"><button id="auth-cancel" class="secondary" type="button">Cancel</button><button id="auth-submit" type="button">Start</button></div>
    </div>`;
  document.body.appendChild(modal);

  let waitingForCode = false;
  const statusEl = document.getElementById('auth-status');
  const openButton = document.getElementById('auth-open');
  const submitButton = document.getElementById('auth-submit');
  const errorEl = document.getElementById('auth-error');

  async function loadStatus() {
    const response = await fetch('/api/auth/status', {cache: 'no-store'});
    const status = await response.json();
    const days = status.remaining_days;
    const text = status.state === 'valid' ? `Session active · about ${days} days remaining`
      : status.state === 'warning' ? `Renew soon · about ${days} days remaining`
      : status.state === 'expired' ? 'Estimated session lifetime reached'
      : status.state === 'session_present' ? 'Session found · authentication date unknown'
      : 'No session found';
    statusEl.innerHTML = `<div class="auth-row"><span class="auth-dot ${status.state}"></span><strong>${text}</strong></div><div>${status.username_masked || ''}</div>`;
    openButton.disabled = !status.web_auth_enabled || !status.admin_password_configured;
    openButton.title = status.web_auth_enabled ? '' : 'Enable WEB_AUTH_ENABLED and configure WEB_ADMIN_PASSWORD';
  }

  function adminHeaders() {
    return {'Content-Type': 'application/json', 'X-Admin-Password': document.getElementById('auth-admin').value};
  }

  openButton.addEventListener('click', () => { modal.classList.add('visible'); errorEl.textContent = ''; });
  document.getElementById('auth-cancel').addEventListener('click', () => modal.classList.remove('visible'));

  submitButton.addEventListener('click', async () => {
    errorEl.textContent = '';
    submitButton.disabled = true;
    try {
      const endpoint = waitingForCode ? '/api/auth/verify' : '/api/auth/start';
      const body = waitingForCode
        ? {code: document.getElementById('auth-code').value.trim()}
        : {password: document.getElementById('auth-password').value};
      const response = await fetch(endpoint, {method: 'POST', headers: adminHeaders(), body: JSON.stringify(body)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Authentication failed');
      if (result.requires_2fa) {
        waitingForCode = true;
        document.getElementById('auth-code-row').hidden = false;
        document.getElementById('apple-password-row').hidden = true;
        document.getElementById('auth-step').textContent = 'Enter the new code shown on your trusted Apple device.';
        submitButton.textContent = 'Verify code';
      } else {
        waitingForCode = false;
        modal.classList.remove('visible');
        document.getElementById('auth-password').value = '';
        document.getElementById('auth-code').value = '';
        await loadStatus();
      }
    } catch (error) {
      errorEl.textContent = error.message;
    } finally {
      submitButton.disabled = false;
    }
  });

  loadStatus().catch(() => { statusEl.textContent = 'Authentication status unavailable'; });
  setInterval(loadStatus, 60000);
})();
