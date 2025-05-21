import React, { useEffect, useState } from "react";

// Парсимо uid і token з адреси
function getActivationParams() {
  const match = window.location.pathname.match(/\/activate\/([^/]+)\/([^/]+)\/?/);
  if (match) {
    return { uid: match[1], token: match[2] };
  }
  return null;
}

function App() {
  // Registration state
  const [form, setForm] = useState({
    email: "",
    password: "",
    re_password: "",
  });
  const [regError, setRegError] = useState(null);
  const [regSuccess, setRegSuccess] = useState(false);

  // Activation state
  const [activationStatus, setActivationStatus] = useState(null);

  // Google login
  const [tokenData, setTokenData] = useState(null);
  const [isHovered, setIsHovered] = useState(false);

  const redirectUri = window.location.origin;

  // --- Реєстрація ---
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleRegister = (e) => {
    e.preventDefault();
    setRegError(null);
    setRegSuccess(false);
    fetch("http://localhost:8000/api/v1/auth/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(form),
    })
      .then(async (res) => {
        if (res.ok) {
          setRegSuccess(true);
          setForm({ email: "", password: "", re_password: "" });
        } else {
          const data = await res.json();
          setRegError(
            typeof data === "string"
              ? data
              : Object.values(data).flat().join(" ")
          );
        }
      })
      .catch(() => setRegError("Network error"));
  };

  // --- Google ---
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (code && state) {
      const url = `http://localhost:8000/api/v1/auth/o/google-oauth2/?state=${encodeURIComponent(
        state
      )}&code=${encodeURIComponent(code)}&redirect_uri=${encodeURIComponent(
        redirectUri
      )}`;

      fetch(url, {
        method: "POST",
        credentials: "include",
      })
        .then((res) => res.json())
        .then((data) => setTokenData(data))
        .catch((err) => console.error("Token exchange error:", err));
    }
  }, [redirectUri]);

  const startGoogleLogin = () => {
    fetch(
      `http://localhost:8000/api/v1/auth/o/google-oauth2/?redirect_uri=${encodeURIComponent(
        redirectUri
      )}`,
      { credentials: "include" }
    )
      .then((res) => res.json())
      .then(({ authorization_url }) => {
        window.location.href = authorization_url;
      })
      .catch((err) => console.error("Auth URL fetch error:", err));
  };

  // --- Активація через лінк ---
  useEffect(() => {
    const params = getActivationParams();
    if (params) {
      setActivationStatus("loading");
      fetch("http://localhost:8000/api/v1/auth/users/activation/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ uid: params.uid, token: params.token }),
      })
        .then(async (res) => {
          if (res.status === 204) setActivationStatus("success");
          else setActivationStatus("failed");
        })
        .catch(() => setActivationStatus("failed"));
    }
  }, []);

  // --- UI ---

  // Стилі
  const wrapperStyle = {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    background: "#f8fafc",
  };

  const cardStyle = {
    background: "#fff",
    padding: "40px 32px 32px 32px",
    borderRadius: "24px",
    boxShadow: "0 4px 32px 0 rgba(0,0,0,0.12)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    minWidth: "340px",
    maxWidth: "95vw",
  };

  const titleStyle = {
    fontSize: "2.2rem",
    fontWeight: "700",
    color: "#1b4332",
    marginBottom: "24px",
    textAlign: "center",
    letterSpacing: "1px",
  };

  const buttonStyle = {
    background: "#43aa8b",
    color: "#fff",
    fontSize: "1.1rem",
    fontWeight: "600",
    padding: "14px 32px",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    marginTop: "16px",
    marginBottom: "12px",
    boxShadow: "0 2px 8px 0 rgba(67,170,139,0.1)",
    transition: "background 0.2s",
  };

  const buttonHoverStyle = {
    background: "#38b000",
  };

  // --- Routing-логіка прямо тут ---
  const activationParams = getActivationParams();
  if (activationParams) {
    // Сторінка активації
    return (
      <div style={wrapperStyle}>
        <div style={cardStyle}>
          <div style={titleStyle}>Account Activation</div>
          {activationStatus === "loading" && <p>Activating...</p>}
          {activationStatus === "success" && (
            <p style={{ color: "#38b000", fontWeight: "600" }}>
              Your account has been activated! <br /> You can now log in.
            </p>
          )}
          {activationStatus === "failed" && (
            <p style={{ color: "#d90429", fontWeight: "600" }}>
              Activation failed. <br /> This link is invalid or has already been used.
            </p>
          )}
        </div>
      </div>
    );
  }

  // Головна сторінка — форма реєстрації та Google login
  return (
    <div style={wrapperStyle}>
      <div style={cardStyle}>
        <div style={titleStyle}>Welcome to ReadRiot Library</div>
        {/* Реєстрація */}
        <form style={{ width: "100%" }} onSubmit={handleRegister}>
          <input
            style={{
              width: "100%",
              marginBottom: "12px",
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid #ccc",
              fontSize: "1rem",
            }}
            required
            type="email"
            name="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
          />
          <input
            style={{
              width: "100%",
              marginBottom: "12px",
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid #ccc",
              fontSize: "1rem",
            }}
            required
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
          />
          <input
            style={{
              width: "100%",
              marginBottom: "8px",
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid #ccc",
              fontSize: "1rem",
            }}
            required
            type="password"
            name="re_password"
            placeholder="Repeat Password"
            value={form.re_password}
            onChange={handleChange}
          />
          <button
            type="submit"
            style={buttonStyle}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            disabled={regSuccess}
          >
            Register
          </button>
        </form>
        {/* Відображення результату реєстрації */}
        {regError && (
          <div style={{ color: "#d90429", marginBottom: "8px", fontWeight: 600 }}>
            {regError}
          </div>
        )}
        {regSuccess && (
          <div style={{ color: "#38b000", marginBottom: "8px", fontWeight: 600 }}>
            Registration successful!<br />
            Please check your email to activate your account.
          </div>
        )}

        {/* Google Login */}
        {!tokenData && (
          <button
            style={isHovered ? { ...buttonStyle, ...buttonHoverStyle } : buttonStyle}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={startGoogleLogin}
          >
            Login with Google
          </button>
        )}
        {/* Token info (Google login) */}
        {tokenData && (
          <div style={{ marginTop: "24px", width: "100%" }}>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "700" }}>Tokens</h2>
            <pre
              style={{
                background: "#f1faee",
                borderRadius: "8px",
                padding: "12px",
                fontSize: "1rem",
                marginTop: "8px",
                overflowX: "auto",
                color: "#3a3a3a",
              }}
            >
              {JSON.stringify(tokenData, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
