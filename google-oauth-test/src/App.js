import React from "react";
import { GoogleLogin } from "@react-oauth/google";

function App() {
  const handleSuccess = credentialResponse => {
    // При успіху сюди прилітає об’єкт з JWT-креденшелом
    console.log("✅ credentialResponse:", credentialResponse);
  };

  const handleError = () => {
    console.error("❌ Login Failed");
  };

  return (
    <div style={{ margin: "100px", textAlign: "center" }}>
      <h1>Google OAuth Test</h1>
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={handleError}
        text="signin_with"   // one of: "signin_with" | "signup_with" | "continue_with"
        theme="outline"      // one of: "outline" | "filled_blue" | "filled_black"
        size="large"         // one of: "small" | "medium" | "large"
        useOneTap={false}    // вимикаємо One-Tap, щоб бачити стандартну кнопку
      />
    </div>
  );
}

export default App;
