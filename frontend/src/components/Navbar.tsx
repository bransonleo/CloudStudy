import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './Navbar.module.css';

export default function Navbar() {
  const { isAuthenticated, userEmail, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className={styles.navbar}>
      <Link to="/" className={styles.brand}>CloudStudy</Link>

      {isAuthenticated && (
        <div className={styles.links}>
          <Link to="/">Dashboard</Link>
          <Link to="/upload">Upload</Link>
          <Link to="/history">History</Link>
        </div>
      )}

      <div className={styles.right}>
        {isAuthenticated ? (
          <>
            <span className={styles.email}>{userEmail}</span>
            <Link to="/settings/2fa" className={styles.settingsLink}>2FA</Link>
            <button onClick={handleLogout} className={styles.logoutBtn}>Logout</button>
          </>
        ) : (
          <Link to="/login">Login</Link>
        )}
      </div>
    </nav>
  );
}
