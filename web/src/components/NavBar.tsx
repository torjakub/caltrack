import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function NavBar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="navbar">
      <span className="navbar-brand">calTrack</span>
      <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
        Dashboard
      </NavLink>
      <NavLink to="/log" className={({ isActive }) => (isActive ? "active" : "")}>
        Log food
      </NavLink>
      <NavLink to="/profile" className={({ isActive }) => (isActive ? "active" : "")}>
        Profile
      </NavLink>
      <span className="navbar-spacer" />
      <span className="navbar-user">{user.username}</span>
      <button onClick={logout}>Log out</button>
    </nav>
  );
}
