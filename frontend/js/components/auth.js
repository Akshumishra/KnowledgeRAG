import * as API from '../api.js';
import { setTokens } from '../api.js';

// Password validation rules — same as backend schema
const PASSWORD_RULES = [
  { id: 'len',     label: 'At least 8 characters',           test: v => v.length >= 8 },
  { id: 'upper',   label: 'At least one uppercase letter',    test: v => /[A-Z]/.test(v) },
  { id: 'lower',   label: 'At least one lowercase letter',    test: v => /[a-z]/.test(v) },
  { id: 'digit',   label: 'At least one digit',               test: v => /[0-9]/.test(v) },
  { id: 'special', label: 'At least one special character',   test: v => /[!@#$%^&*()\-_=+[\]{}|;:'",.<>/?`~]/.test(v) },
];

function passwordChecklist(password) {
  return PASSWORD_RULES.map(r => {
    const pass = r.test(password);
    return `
      <div class="pw-rule ${pass ? 'pw-rule-pass' : 'pw-rule-fail'}" data-rule="${r.id}">
        <span class="pw-rule-icon">${pass ? '&#10003;' : '&#8722;'}</span>
        ${r.label}
      </div>`;
  }).join('');
}

function allRulesPass(password) {
  return PASSWORD_RULES.every(r => r.test(password));
}

export function renderAuth(onSuccess) {
  // modes: 'login' | 'register' | 'verify' | 'forgot' | 'reset'
  let mode = 'login';
  let tempEmail = '';

  const existingPage = document.getElementById('auth-page');
  if (existingPage) {
    existingPage.remove();
  }

  const page = document.createElement('div');
  page.id = 'auth-page';
  document.body.appendChild(page);

  const render = () => {
    let title = '';
    let formHtml = '';
    let footerHtml = '';

    if (mode === 'register') {
      title = 'Create an Account';
      formHtml = `
        <div class="form-group">
          <label class="form-label">Full Name</label>
          <input id="full-name" class="form-control" type="text" placeholder="Jane Doe" required />
        </div>
        <div class="form-group">
          <label class="form-label">Email</label>
          <input id="email" class="form-control" type="email" placeholder="jane@company.com" required />
        </div>
        <div class="form-group">
          <label class="form-label">Password</label>
          <div class="pw-field-wrap">
            <input id="password" class="form-control pw-input" type="password" placeholder="••••••••" required minlength="8" autocomplete="new-password" />
            <button type="button" class="pw-eye-btn" id="pw-toggle" title="Show / hide password" aria-label="Toggle password visibility">
              <svg id="pw-eye-icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
          <div class="pw-rules" id="pw-rules">
            ${passwordChecklist('')}
          </div>
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%;padding:12px;font-size:14px;font-weight:600;margin-top:4px;border-radius:10px;" disabled>Create Account</button>
      `;
      footerHtml = `
        <span style="color:var(--c-text-2);">Already have an account?</span> 
        <a id="btn-login" style="cursor:pointer;font-weight:500;">Sign in here</a>
      `;
    } else if (mode === 'login') {
      title = 'Welcome back';
      formHtml = `
        <div class="form-group">
          <label class="form-label">Email</label>
          <input id="email" class="form-control" type="email" placeholder="jane@company.com" required />
        </div>
        <div class="form-group">
          <label class="form-label">Password</label>
          <div class="pw-field-wrap">
            <input id="password" class="form-control pw-input" type="password" placeholder="••••••••" required autocomplete="current-password" />
            <button type="button" class="pw-eye-btn" id="pw-toggle" title="Show / hide password" aria-label="Toggle password visibility">
              <svg id="pw-eye-icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%;padding:12px;font-size:14px;font-weight:600;margin-top:4px;border-radius:10px;">Sign In</button>
        <div style="text-align:center;margin-top:12px;">
          <a id="btn-forgot" style="cursor:pointer;font-size:13px;font-weight:500;">Forgot Password?</a>
        </div>
      `;
      footerHtml = `
        <span style="color:var(--c-text-2);">Don't have an account?</span> 
        <a id="btn-register" style="cursor:pointer;font-weight:500;">Register here</a>
      `;
    } else if (mode === 'verify') {
      title = 'Verify your Email';
      formHtml = `
        <p style="font-size:14px;color:var(--c-text-2);margin-bottom:16px;">We sent a 6-digit verification code to <strong>${tempEmail}</strong>.</p>
        <div class="form-group">
          <label class="form-label">Verification Code</label>
          <input id="otp" class="form-control" type="text" placeholder="123456" required maxlength="6" minlength="6" autocomplete="off" />
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%;padding:12px;font-size:14px;font-weight:600;margin-top:4px;border-radius:10px;">Verify & Sign In</button>
      `;
      footerHtml = `
        <a id="btn-login" style="cursor:pointer;font-weight:500;">Back to login</a>
        <span style="color:var(--c-text-2); margin:0 8px;">|</span>
        <a id="btn-resend-otp" style="cursor:pointer;font-weight:500;">Resend OTP</a>
      `;
    } else if (mode === 'forgot') {
      title = 'Reset Password';
      formHtml = `
        <p style="font-size:14px;color:var(--c-text-2);margin-bottom:16px;">Enter your email and we will send you a reset code.</p>
        <div class="form-group">
          <label class="form-label">Email</label>
          <input id="email" class="form-control" type="email" placeholder="jane@company.com" required />
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%;padding:12px;font-size:14px;font-weight:600;margin-top:4px;border-radius:10px;">Send Reset Code</button>
      `;
      footerHtml = `
        <a id="btn-login" style="cursor:pointer;font-weight:500;">Back to login</a>
      `;
    } else if (mode === 'reset') {
      title = 'Create New Password';
      formHtml = `
        <p style="font-size:14px;color:var(--c-text-2);margin-bottom:16px;">Enter the 6-digit code sent to <strong>${tempEmail}</strong> and your new password.</p>
        <div class="form-group">
          <label class="form-label">Reset Code (OTP)</label>
          <input id="otp" class="form-control" type="text" placeholder="123456" required maxlength="6" minlength="6" autocomplete="off" />
        </div>
        <div class="form-group">
          <label class="form-label">New Password</label>
          <div class="pw-field-wrap">
            <input id="password" class="form-control pw-input" type="password" placeholder="••••••••" required minlength="8" autocomplete="new-password" />
            <button type="button" class="pw-eye-btn" id="pw-toggle" title="Show / hide password" aria-label="Toggle password visibility">
              <svg id="pw-eye-icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
          <div class="pw-rules" id="pw-rules">
            ${passwordChecklist('')}
          </div>
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%;padding:12px;font-size:14px;font-weight:600;margin-top:4px;border-radius:10px;" disabled>Reset Password</button>
      `;
      footerHtml = `
        <a id="btn-login" style="cursor:pointer;font-weight:500;">Back to login</a>
      `;
    }

    page.innerHTML = `
      <div class="auth-bg">
        <div class="auth-card">
          <div class="auth-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" style="vertical-align:middle;margin-right:8px;">
              <rect width="28" height="28" rx="8" fill="url(#ag)"/>
              <path d="M8 14h12M14 8v12" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
              <defs><linearGradient id="ag" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                <stop stop-color="#6366f1"/><stop offset="1" stop-color="#22d3ee"/>
              </linearGradient></defs>
            </svg>
            KnowledgeAI
          </div>
          <div class="auth-tagline">${title}</div>
          <div id="auth-error" class="auth-error hidden"></div>
          <div id="auth-success" class="auth-success hidden" style="color:var(--c-success);background:rgba(34,197,94,0.1);padding:10px;border-radius:6px;font-size:13px;margin-bottom:16px;"></div>

          <form class="auth-form" id="auth-form">
            ${formHtml}
          </form>

          <div class="auth-toggle" style="margin-top:16px;">
            ${footerHtml}
          </div>
        </div>
      </div>
    `;

    // ── Toggle mode listeners
    page.querySelector('#btn-register')?.addEventListener('click', () => { mode = 'register'; render(); });
    page.querySelector('#btn-login')?.addEventListener('click', () => { mode = 'login'; render(); });
    page.querySelector('#btn-forgot')?.addEventListener('click', () => { mode = 'forgot'; render(); });

    page.querySelector('#btn-resend-otp')?.addEventListener('click', async () => {
      const errEl = page.querySelector('#auth-error');
      const successEl = page.querySelector('#auth-success');
      const btn = page.querySelector('#btn-resend-otp');
      const origText = btn.textContent;
      
      btn.style.pointerEvents = 'none';
      btn.textContent = 'Sending...';
      
      try {
        await API.auth.resendOtp({ email: tempEmail });
        errEl.classList.add('hidden');
        successEl.textContent = 'A new verification code has been sent!';
        successEl.classList.remove('hidden');
      } catch (err) {
        successEl.classList.add('hidden');
        errEl.textContent = err.message || 'Failed to resend OTP.';
        errEl.classList.remove('hidden');
      } finally {
        btn.style.pointerEvents = 'auto';
        btn.textContent = origText;
      }
    });

    // ── Eye toggle
    const pwInput = page.querySelector('#password');
    const pwToggle = page.querySelector('#pw-toggle');
    const pwIcon = page.querySelector('#pw-eye-icon');

    const eyeOpen = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
    const eyeSlash = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>`;

    pwToggle?.addEventListener('click', () => {
      const isHidden = pwInput.type === 'password';
      pwInput.type = isHidden ? 'text' : 'password';
      pwIcon.innerHTML = isHidden ? eyeSlash : eyeOpen;
    });

    // ── Live password validation (register & reset only)
    if (mode === 'register' || mode === 'reset') {
      const rulesEl = page.querySelector('#pw-rules');
      const submitBtn = page.querySelector('#auth-submit');

      pwInput?.addEventListener('input', () => {
        const val = pwInput.value;
        rulesEl.innerHTML = passwordChecklist(val);
        submitBtn.disabled = !allRulesPass(val);
      });
    }

    // ── Form submission
    const form = page.querySelector('#auth-form');
    const errEl = page.querySelector('#auth-error');
    const successEl = page.querySelector('#auth-success');
    const btn = page.querySelector('#auth-submit');
    const origBtnText = btn.textContent;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Client-side guard for password
      if ((mode === 'register' || mode === 'reset') && !allRulesPass(pwInput.value)) {
        errEl.textContent = 'Please satisfy all password requirements before submitting.';
        errEl.classList.remove('hidden');
        return;
      }

      errEl.classList.add('hidden');
      successEl.classList.add('hidden');
      btn.disabled = true;
      btn.textContent = 'Please wait...';

      try {
        if (mode === 'register') {
          tempEmail = page.querySelector('#email').value.trim();
          const payload = {
            email: tempEmail,
            full_name: page.querySelector('#full-name').value.trim(),
            password: pwInput.value
          };
          await API.auth.register(payload);
          mode = 'verify';
          render();
          return;
        }

        if (mode === 'verify') {
          const payload = {
            email: tempEmail,
            otp: page.querySelector('#otp').value.trim()
          };
          const res = await API.auth.verifyEmail(payload);
          API.setTokens(res.access_token, res.refresh_token);
          if (onSuccess) await onSuccess();
          return;
        }

        if (mode === 'forgot') {
          tempEmail = page.querySelector('#email').value.trim();
          await API.auth.forgotPassword(tempEmail);
          mode = 'reset';
          render();
          return;
        }

        if (mode === 'reset') {
          const payload = {
            email: tempEmail,
            otp: page.querySelector('#otp').value.trim(),
            new_password: pwInput.value
          };
          await API.auth.resetPassword(payload);
          mode = 'login';
          render();
          const newSuccessEl = document.querySelector('#auth-success');
          if (newSuccessEl) {
            newSuccessEl.textContent = 'Password has been successfully reset. Please log in.';
            newSuccessEl.classList.remove('hidden');
          }
          return;
        }

        if (mode === 'login') {
          const payload = {
            email: page.querySelector('#email').value.trim(),
            password: pwInput.value
          };
          const res = await API.auth.login(payload);
          API.setTokens(res.access_token, res.refresh_token);
          if (onSuccess) await onSuccess();
        }

      } catch (err) {
        // If login fails because of unverified email, we could switch to verify mode, but the backend doesn't explicitly type the error.
        // We'll just show the error message.
        if (err.message && err.message.toLowerCase().includes('not verified')) {
          tempEmail = page.querySelector('#email').value.trim();
          mode = 'verify';
          render();
          return;
        }
        errEl.textContent = err.message || 'Authentication failed. Please try again.';
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.textContent = origBtnText;
      }
    });
  };

  render();
}
