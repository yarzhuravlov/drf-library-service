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

  return (
    <div className="p-4">
      {!tokenData && (
        <button onClick={startGoogleLogin} className="px-4 py-2 bg-blue-600 text-white rounded">
          Login with Google
        </button>
      )}

      {tokenData && (
        <div className="mt-4">
          <h2 className="text-xl font-bold">Tokens</h2>
          <pre>{JSON.stringify(tokenData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
