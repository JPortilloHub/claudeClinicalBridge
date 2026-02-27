import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { logout, getStoredUser } from '../api/auth';

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();

  // Workflow detail pages need full viewport width for split-pane layout
  const isWorkflowDetail =
    /^\/workflows\/[^/]+$/.test(location.pathname) &&
    location.pathname !== '/workflows/new';

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
      <main className={`app-main ${isWorkflowDetail ? 'app-main--full-width' : ''}`}>
        <Outlet />
      </main>
    </div>
  );
}
