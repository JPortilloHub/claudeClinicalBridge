import { Link, Outlet, useNavigate } from 'react-router-dom';
import { logout, getStoredUser } from '../api/auth';

export default function Layout() {
  const navigate = useNavigate();
  const user = getStoredUser();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <nav className="app-nav">
        <Link to="/" className="nav-brand">
          Clinical Bridge
        </Link>
        <div className="nav-right">
          {user && <span className="nav-user">{user.full_name || user.username}</span>}
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
