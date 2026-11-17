import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, Home, LayoutDashboard, LogOut, Menu, Moon, Sun, Terminal, X } from 'lucide-react';
import { Instructor, Theme } from '../types';
import csuCcisLogo from '../assets/CSU-CCIS.png';
import logoutLeaveArt from '../assets/logout-leave.png';

interface NavbarProps {
  currentView: 'home' | 'instructor' | 'student';
  setCurrentView: (view: 'home' | 'instructor' | 'student') => void;
  instructor: Instructor | null;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  logoutConfirmOpen: boolean;
  setLogoutConfirmOpen: (open: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  setCurrentView,
  instructor,
  onLogout,
  theme,
  onToggleTheme,
  logoutConfirmOpen,
  setLogoutConfirmOpen,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setMenuOpen(false);
  }, [currentView, instructor]);

  useEffect(() => {
    if (!menuOpen && !logoutConfirmOpen) return;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (logoutConfirmOpen) {
        setLogoutConfirmOpen(false);
      } else {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = oldOverflow;
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen, logoutConfirmOpen, setLogoutConfirmOpen]);

  useEffect(() => {
    if (menuOpen) closeButtonRef.current?.focus();
  }, [menuOpen]);

  const goTo = (view: 'home' | 'instructor' | 'student') => {
    setCurrentView(view);
    setMenuOpen(false);
  };

  const openLogout = () => {
    setMenuOpen(false);
    setLogoutConfirmOpen(true);
  };

  const initials = instructor?.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'IN';

  const menuItemClass = (active: boolean) =>
    `ca-menu-link ${active ? 'is-active' : ''}`;

  return (
    <>
      <header className="ca-navbar fixed inset-x-0 top-0 z-40 text-ca-ink" role="banner">
        <div className="ca-navbar-inner max-w-7xl mx-auto px-3 sm:px-6 flex items-center justify-between gap-1.5 sm:gap-2">
          <button
            type="button"
            onClick={() => goTo('home')}
            aria-label="Go to CodeAuthentic home"
            className="ca-brand-link flex items-center gap-2 sm:gap-2.5 min-w-0 group"
          >
            <span className="ca-brand-icon shrink-0">
              <img src={csuCcisLogo} alt="" className="w-full h-full object-contain" />
            </span>
            <span className="min-w-0 text-left">
              <span className="block font-extrabold tracking-tight text-[14px] min-[375px]:text-base sm:text-lg whitespace-nowrap leading-tight text-ca-ink group-hover:text-ca-brand transition-colors">
                Code<span className="text-ca-brand">Authentic</span>
              </span>
              <span className="hidden sm:block text-[10px] leading-tight text-ca-muted font-medium mt-0.5">
                CCIS · AI Code Detector
              </span>
            </span>
          </button>

          <div className="flex items-center justify-end gap-1 sm:gap-2 shrink-0">
            <button
              type="button"
              onClick={onToggleTheme}
              className="ca-header-action"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
            </button>

            {instructor && (
              <button
                type="button"
                onClick={openLogout}
                className="ca-header-action ca-header-logout"
                aria-label="Log out of instructor account"
                title="Log out"
              >
                <LogOut className="h-[18px] w-[18px]" />
                <span className="hidden lg:inline text-xs font-semibold">Log out</span>
              </button>
            )}

            <button
              type="button"
              ref={menuButtonRef}
              onClick={() => setMenuOpen((open) => !open)}
              aria-label={instructor ? 'Open account and navigation menu' : 'Open navigation menu'}
              aria-expanded={menuOpen}
              aria-controls="ca-account-menu"
              className={`ca-profile-trigger ${menuOpen ? 'is-open' : ''}`}
              title={instructor ? 'Account and navigation' : 'Menu'}
            >
              {instructor ? (
                <>
                  <span className="ca-profile-avatar" aria-hidden="true">{initials}</span>
                  <span className="ca-profile-caret md:hidden" aria-hidden="true"><ChevronDown className="w-2.5 h-2.5" /></span>
                  <span className="ca-profile-label hidden md:flex flex-col items-start min-w-0">
                    <span className="truncate w-full text-[12px] font-bold leading-tight">{instructor.name}</span>
                    <span className="truncate w-full text-[10px] text-ca-muted leading-tight">Instructor</span>
                  </span>
                  <ChevronDown className="hidden md:block h-3.5 w-3.5 text-ca-muted shrink-0" aria-hidden="true" />
                </>
              ) : (
                <>
                  <Menu className="h-[20px] w-[20px]" aria-hidden="true" />
                  <span className="hidden sm:inline text-sm font-semibold">Menu</span>
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <>
          <button
            type="button"
            className="ca-menu-backdrop"
            aria-label="Close account menu"
            onClick={() => setMenuOpen(false)}
          />
          <aside id="ca-account-menu" className="ca-account-menu" aria-label="Account and navigation">
            <div className="ca-menu-heading">
              <div className="min-w-0">
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-ca-faint">{instructor ? 'Signed in as' : 'Welcome to'}</span>
                <p className="text-sm font-bold text-ca-ink truncate">{instructor ? instructor.name : 'CodeAuthentic'}</p>
                {instructor && <p className="text-[11px] text-ca-muted truncate">{instructor.idNumber}</p>}
              </div>
              <button
                type="button"
                ref={closeButtonRef}
                onClick={() => { setMenuOpen(false); menuButtonRef.current?.focus(); }}
                className="ca-menu-close"
                aria-label="Close menu"
              >
                <X className="w-[17px] h-[17px]" />
              </button>
            </div>

            <p className="ca-menu-overline">Navigation</p>
            <nav aria-label="Main navigation" className="space-y-1">
              <button type="button" onClick={() => goTo('home')} className={menuItemClass(currentView === 'home')} aria-current={currentView === 'home' ? 'page' : undefined}>
                <Home className="w-[17px] h-[17px]" /> <span>Home</span>
              </button>
              <button type="button" onClick={() => goTo('instructor')} className={menuItemClass(currentView === 'instructor')} aria-current={currentView === 'instructor' ? 'page' : undefined}>
                <LayoutDashboard className="w-[17px] h-[17px]" /> <span>{instructor ? 'Instructor Dashboard' : 'Instructor Login'}</span>
              </button>
              <button type="button" onClick={() => goTo('student')} className={menuItemClass(currentView === 'student')} aria-current={currentView === 'student' ? 'page' : undefined}>
                <Terminal className="w-[17px] h-[17px]" /> <span>Student Portal</span>
              </button>
            </nav>

            <div className="ca-menu-divider" />
            <button type="button" onClick={onToggleTheme} className="ca-menu-link" aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
              {theme === 'dark' ? <Sun className="w-[17px] h-[17px]" /> : <Moon className="w-[17px] h-[17px]" />}
              <span className="flex-1 text-left">{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
              <span className="text-[10px] text-ca-muted">{theme === 'dark' ? 'Dark is on' : 'Light is on'}</span>
            </button>
            {instructor && (
              <button type="button" onClick={openLogout} className="ca-menu-link ca-menu-link-danger">
                <LogOut className="w-[17px] h-[17px]" /><span>Log out</span>
              </button>
            )}
          </aside>
        </>
      )}

      {logoutConfirmOpen && (
        <div
          className="ca-logout-overlay fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 ca-fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-confirm-title"
          aria-describedby="logout-confirm-description"
        >
          <button
            type="button"
            className="absolute inset-0 cursor-default"
            aria-label="Dismiss logout confirmation"
            onClick={() => setLogoutConfirmOpen(false)}
          />
          <div className="ca-logout-card relative w-full max-w-md max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-[28px] p-5 sm:p-7 text-center ca-fade-up">
            <button
              type="button"
              onClick={() => setLogoutConfirmOpen(false)}
              className="ca-logout-close absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-full text-ca-muted transition-colors cursor-pointer"
              aria-label="Close logout dialog"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="ca-logout-shell">
              <div className="ca-logout-badge">Session ending</div>

              <div className="ca-logout-illustration">
                <div className="ca-logout-illustration-ring" aria-hidden="true" />
                <img
                  src={logoutLeaveArt}
                  alt=""
                  className="ca-logout-image"
                  aria-hidden="true"
                />
              </div>

              <div className="ca-logout-copy">
                <h2
                  id="logout-confirm-title"
                  className="font-display text-2xl sm:text-[2rem] leading-tight font-bold text-ca-ink"
                >
                  Come back soon
                  <span className="text-ca-brand">.</span>
                </h2>
                <p
                  id="logout-confirm-description"
                  className="mt-3 text-sm sm:text-[15px] leading-6 text-ca-muted"
                >
                  You are about to securely sign out of your CodeAuthentic instructor workspace.
                  You can log back in anytime to continue managing lobbies and reviewing submissions.
                </p>
              </div>

              <div className="ca-logout-note">
                <span className="ca-logout-note-dot" aria-hidden="true" />
                Your current session will be closed on this device.
              </div>

              <div className="mt-7 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setLogoutConfirmOpen(false)}
                  className="ca-logout-btn ca-logout-btn-secondary"
                >
                  Stay here
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLogoutConfirmOpen(false);
                    onLogout();
                  }}
                  className="ca-logout-btn ca-logout-btn-primary"
                >
                  Yes, log out
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
