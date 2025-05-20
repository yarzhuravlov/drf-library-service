import React, { useEffect, useState } from "react";

function App() {
  const [tokenData, setTokenData] = useState(null);
  const redirectUri = window.location.origin;

  // After Google redirect, exchange code+state via query params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (code && state) {
      // Use query params for code, state, redirect_uri
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
  }, []);

  // Start OAuth flow: GET auth_url then redirect
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

  // Стилі без CSS-файлів
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
    fontSize: "2.4rem",
    fontWeight: "700",
    color: "#1b4332",
    marginBottom: "32px",
    textAlign: "center",
    letterSpacing: "1px",
  };

  const buttonStyle = {
    background: "#43aa8b",
    color: "#fff",
    fontSize: "1.2rem",
    fontWeight: "600",
    padding: "20px 48px",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    marginTop: "16px",
    marginBottom: "16px",
    boxShadow: "0 2px 8px 0 rgba(67,170,139,0.1)",
    transition: "background 0.2s",
  };

  const buttonHoverStyle = {
    background: "#38b000",
  };

  // Для ховер-ефекту
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div style={wrapperStyle}>
      <div style={cardStyle}>
        <div style={titleStyle}>Welcome to ReadRiot Library</div>
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
