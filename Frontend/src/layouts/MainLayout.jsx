import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Menu } from 'lucide-react';
import Header from '../components/Header';
import NavDrawer from '../components/NavDrawer';
import { useAuth } from '../context/AuthContext';

const MotionButton = motion.button;
const MotionDiv = motion.div;

const MainLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-shell">
      <Header onLogout={handleLogout} userName={user?.name} />

      <div className="container-page border-b border-teal-100/30">
        <div className="flex items-center py-3">
          <MotionButton
            type="button"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => setNavOpen(true)}
            className="group inline-flex items-center gap-2 rounded-xl border border-teal-100 bg-white/90 px-4 py-2.5 text-sm font-semibold text-teal-950 shadow-sm transition-all duration-300 hover:border-teal-200 hover:bg-gradient-to-r hover:from-teal-50 hover:to-cyan-50 hover:shadow-md hover:shadow-teal-600/10"
          >
            <motion.span
              className="inline-flex text-teal-600"
              whileHover={{ rotate: 180 }}
              transition={{ type: 'spring', stiffness: 200, damping: 12 }}
            >
              <Menu className="w-5 h-5 transition-transform duration-300 group-hover:scale-110" />
            </motion.span>
            Menu
          </MotionButton>
        </div>
      </div>

      <div className="container-page pb-12">
        <MotionDiv
          key={location.pathname}
          initial={{ opacity: 0, y: 16, filter: 'blur(4px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ type: 'spring', stiffness: 280, damping: 28, mass: 0.8 }}
        >
          <Outlet />
        </MotionDiv>
      </div>

      <NavDrawer open={navOpen} onClose={() => setNavOpen(false)} onLogout={handleLogout} />
    </div>
  );
};

export default MainLayout;
