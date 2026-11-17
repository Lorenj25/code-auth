// CodeAuthentic - Authentication Handler

function switchTab(tab) {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const alertBox = document.getElementById('alert-box');
  alertBox.style.display = 'none';

  if (tab === 'login') {
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
  } else {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
    tabLogin.classList.remove('active');
    tabRegister.classList.add('active');
  }
}

function showAlert(message, type) {
  const alertBox = document.getElementById('alert-box');
  alertBox.textContent = message;
  alertBox.className = 'alert ' + type;
  alertBox.style.display = 'block';
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('login-btn');

  btn.disabled = true;
  btn.textContent = 'Logging in...';

  try {
    const res = await fetch('/auth/login/json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    localStorage.setItem('codeauthentic_token', data.access_token);
    showAlert('Login successful! Redirecting...', 'success');
    setTimeout(() => {
      window.location.href = '/dashboard';
    }, 600);
  } catch (err) {
    showAlert(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Log In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById('reg-name').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;
  const btn = document.getElementById('reg-btn');

  btn.disabled = true;
  btn.textContent = 'Registering...';
  let accountCreated = false;

  try {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Registration failed');
    }

    accountCreated = true;
    // Keep the classic HTML interface in sync with the React auto-login flow.
    const loginResponse = await fetch('/auth/login/json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!loginResponse.ok) {
      showAlert('Account created! Please sign in.', 'success');
      switchTab('login');
      document.getElementById('login-email').value = email;
      return;
    }
    const loginData = await loginResponse.json();
    localStorage.setItem('codeauthentic_token', loginData.access_token);
    showAlert('Account created! Opening dashboard...', 'success');
    setTimeout(() => { window.location.href = '/dashboard'; }, 600);
  } catch (err) {
    if (accountCreated) {
      switchTab('login');
      document.getElementById('login-email').value = email;
      showAlert('Account created, but automatic sign-in failed. Please sign in.', 'error');
    } else {
      showAlert(err.message, 'error');
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Account';
  }
}
