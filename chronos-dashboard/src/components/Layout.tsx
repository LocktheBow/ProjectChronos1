import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styles from './Layout.module.css';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  
  const isActive = (path: string) => {
    return location.pathname === path || location.pathname === path + '/';
  };
  
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <Link to="/" className={styles.logoLink}>
            <span className={styles.logoIcon}>⏱</span>
            Chronos
          </Link>
          <nav>
            <Link 
              to="/dashboard" 
              className={`${styles.navLink} ${isActive('/dashboard') || isActive('/') ? styles.activeLink : ''}`}
            >
              Dashboard
            </Link>
            <Link 
              to="/relationships" 
              className={`${styles.navLink} ${isActive('/relationships') ? styles.activeLink : ''}`}
            >
              Relationships
            </Link>
            <Link 
              to="/search" 
              className={`${styles.navLink} ${isActive('/search') ? styles.activeLink : ''}`}
            >
              Search
            </Link>
          </nav>
        </div>
      </header>
      <main className={styles.content}>
        {children}
      </main>
    </div>
  );
}