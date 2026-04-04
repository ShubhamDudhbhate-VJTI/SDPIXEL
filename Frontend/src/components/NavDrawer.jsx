import { AnimatePresence, motion } from 'framer-motion';
import { FileSearch, HelpCircle, History, LogOut, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const MotionButton = motion.button;
const MotionAside = motion.aside;
const MotionNav = motion.nav;
const MotionDiv = motion.div;

const linkBase =
  'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-300 ease-out';

const navContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.12 },
  },
};

const navItem = {
  hidden: { opacity: 0, x: -20 },
  show: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 320, damping: 26 },
  },
};

const activeLink =
  'bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-lg shadow-teal-600/30 scale-[1.02]';
const inactiveLink =
  'text-slate-800 hover:bg-teal-50/90 hover:translate-x-1 hover:shadow-sm border border-transparent hover:border-teal-100';

const NavDrawer = ({ open, onClose, onLogout }) => {
  return (
    <AnimatePresence mode="sync">
      {open ? (
        <>
          <MotionButton
            key="nav-backdrop"
            type="button"
            aria-label="Close menu"
            className="fixed inset-0 z-[60] bg-slate-950/50 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            onClick={onClose}
          />

          <MotionAside
            key="nav-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="nav-drawer-title"
            className="fixed left-0 top-0 z-[70] flex h-full w-[min(100vw-3rem,320px)] flex-col border-r border-teal-100/80 bg-gradient-to-b from-white via-teal-50/20 to-cyan-50/30 shadow-2xl shadow-teal-900/10 backdrop-blur-xl"
            initial={{ x: '-105%' }}
            animate={{ x: 0 }}
            exit={{ x: '-105%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 340 }}
          >
            <div className="flex items-center justify-between border-b border-teal-100/60 bg-white/40 px-4 py-4 backdrop-blur-sm">
              <motion.div
                id="nav-drawer-title"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="text-sm font-bold tracking-tight text-teal-950"
              >
                Navigation
              </motion.div>
              <MotionButton
                type="button"
                onClick={onClose}
                whileHover={{ scale: 1.08, rotate: 90 }}
                whileTap={{ scale: 0.92 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-teal-100 bg-white text-teal-800 shadow-sm hover:bg-teal-50"
                aria-label="Close sidebar"
              >
                <X className="w-5 h-5" />
              </MotionButton>
            </div>

            <MotionNav
              variants={navContainer}
              initial="hidden"
              animate="show"
              className="flex-1 space-y-2 overflow-y-auto p-3"
            >
              <MotionDiv variants={navItem}>
                <NavLink
                  to="/analyze"
                  onClick={onClose}
                  className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
                >
                  <FileSearch className="w-5 h-5 shrink-0" />
                  Start PDF and scan analysis
                </NavLink>
              </MotionDiv>
              <MotionDiv variants={navItem}>
                <NavLink
                  to="/history"
                  onClick={onClose}
                  className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
                >
                  <History className="w-5 h-5 shrink-0" />
                  Lookup transaction
                </NavLink>
              </MotionDiv>
              <MotionDiv variants={navItem}>
                <NavLink
                  to="/help"
                  onClick={onClose}
                  className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
                >
                  <HelpCircle className="w-5 h-5 shrink-0" />
                  Help
                </NavLink>
              </MotionDiv>
            </MotionNav>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, type: 'spring', stiffness: 260, damping: 22 }}
              className="border-t border-teal-100/60 bg-white/30 p-3 backdrop-blur-sm"
            >
              <MotionButton
                type="button"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  onClose();
                  onLogout();
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200/90 bg-red-50/95 px-4 py-3 text-sm font-semibold text-red-800 shadow-sm transition-colors duration-200 hover:bg-red-100"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </MotionButton>
            </motion.div>
          </MotionAside>
        </>
      ) : null}
    </AnimatePresence>
  );
};

export default NavDrawer;
