import { auth0 } from "@/lib/auth0";

export default async function TokenPage() {
  const session = await auth0.getSession();

  if (!session) {
    return (
      <div style={{ padding: "2rem", fontFamily: "monospace" }}>
        <h1>Not logged in</h1>
        <a href="/auth/login">Login first</a>
      </div>
    );
  }

  // Get access token
  let tokenSet = null;
  try {
    tokenSet = await auth0.getAccessToken();
  } catch (e) {
    console.error("Error getting access token:", e);
  }

  // The session contains the ID token claims directly
  const user = session.user;
  const sub = user.sub || "";
  const email = user.email || "";

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "monospace",
        background: "#1a1e27",
        color: "#e2e8f0",
        minHeight: "100vh",
        maxWidth: "900px",
        margin: "0 auto",
      }}
    >
      <h1 style={{ color: "#63b3ed", marginBottom: "2rem" }}>
        🔐 Auth0 Session Info
      </h1>

      <div
        style={{
          background: "#2d313c",
          padding: "1.5rem",
          borderRadius: "8px",
          marginBottom: "2rem",
        }}
      >
        <h2 style={{ color: "#68d391", marginTop: 0 }}>✅ You are logged in!</h2>
        <p>
          <strong>Email:</strong> {email}
        </p>
        <p>
          <strong>Auth0 User ID (sub):</strong> {sub}
        </p>
      </div>

      <div
        style={{
          background: "#2d313c",
          padding: "1.5rem",
          borderRadius: "8px",
          marginBottom: "2rem",
        }}
      >
        <h2 style={{ color: "#f6ad55", marginTop: 0 }}>
          🚀 Bootstrap Command
        </h2>
        <p>Copy and run this in your terminal to create your organization:</p>
        <pre
          style={{
            background: "#1a1e27",
            padding: "1rem",
            borderRadius: "8px",
            overflow: "auto",
            fontSize: "0.85rem",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}
        >
          {`curl -X POST "http://localhost:8000/api/v1/auth/bootstrap-direct" \\
  -H "Content-Type: application/json" \\
  -d '{
    "org_name": "FaceTrace",
    "org_slug": "facetrace",
    "org_email": "${email}",
    "auth0_user_id": "${sub}",
    "user_email": "${email}"
  }'`}
        </pre>
      </div>

      <div
        style={{
          background: "#2d313c",
          padding: "1.5rem",
          borderRadius: "8px",
          marginBottom: "2rem",
        }}
      >
        <h2 style={{ color: "#63b3ed", marginTop: 0 }}>👤 Full User Info</h2>
        <pre
          style={{
            background: "#1a1e27",
            padding: "1rem",
            borderRadius: "8px",
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {JSON.stringify(user, null, 2)}
        </pre>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <a
          href="/"
          style={{
            color: "#63b3ed",
            textDecoration: "none",
            marginRight: "1rem",
          }}
        >
          ← Back to Home
        </a>
        <a href="/auth/logout" style={{ color: "#fc8181", textDecoration: "none" }}>
          Logout
        </a>
      </div>
    </div>
  );
}
