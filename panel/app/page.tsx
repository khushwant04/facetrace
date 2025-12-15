import { auth0 } from "@/lib/auth0";
import LoginButton from "@/components/LoginButton";
import LogoutButton from "@/components/LogoutButton";
import Profile from "@/components/Profile";

export default async function Home() {
  const session = await auth0.getSession();
  const user = session?.user;

  return (
    <div className="app-container">
      <div className="main-card-wrapper">
        <img
          src="https://cdn.auth0.com/quantum-assets/dist/latest/logos/auth0/auth0-lockup-en-ondark.png"
          alt="Auth0 Logo"
          className="auth0-logo"
        />
        <h1 className="main-title">FaceTrace</h1>
        
        <div className="action-card">
          {user ? (
            <div className="logged-in-section">
              <p className="logged-in-message">✅ Successfully logged in!</p>
              <Profile />
              <LogoutButton />
            </div>
          ) : (
            <>
              <p className="action-text">
                Welcome! Please log in to access your dashboard.
              </p>
              <LoginButton />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
