import React from "react";
import { useGoogleLogin } from "@react-oauth/google";

function App() {
  const login = useGoogleLogin({
    flow: "auth-code",            // саме код-флоу
    onSuccess: async codeResp => {
      const { code, state } = codeResp;
      const redirectUri = window.location.origin;

      // готуємо form-urlencoded тіло
      const params = new URLSearchParams();
      params.append("code", code);
      params.append("state", state);
      params.append("redirect_uri", redirectUri);

      const res = await fetch(
        "http://localhost:8000/api/v1/auth/o/google-oauth2/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: params.toString()
        }
      );
      const data = await res.json();
      if (!res.ok) {
        console.error("Social login error:", data);
      } else {
        console.log("✅ Logged in, API tokens:", data);
      }
    },
    onError: () => console.error("Google login failed")
  });

  return (
    <div style={{ textAlign: "center", margin: "100px" }}>
      <h1>Google OAuth Code-Flow</h1>
      <button onClick={() => login()}>Login with Google</button>
    </div>
  );
}

export default App;
