import { motion } from 'framer-motion';
import { LogOut, Shield } from 'lucide-react';

const MotionHeader = motion.header;
const MotionDiv = motion.div;
const MotionButton = motion.button;

const Header = ({ onLogout, userName }) => {
  return (
    <MotionHeader
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-40 border-b border-teal-200/40 bg-white/80 backdrop-blur-lg shadow-[0_1px_0_rgba(13,148,136,0.06)]"
    >
      <div className="container-page h-16 flex items-center gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <MotionDiv
            whileHover={{ scale: 1.06, rotate: -2 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
            className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 via-teal-600 to-cyan-500 text-white shadow-lg shadow-teal-600/30 animate-logo-ring"
            aria-hidden
          >
            <Shield className="w-5 h-5 drop-shadow-sm" />
            <span className="absolute inset-0 rounded-xl ring-2 ring-white/35" />
          </MotionDiv>
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.12, duration: 0.35 }}
            className="min-w-0"
          >
            <h1 className="text-[15px] sm:text-base font-semibold text-slate-900 leading-tight truncate">
              Customs X-ray Intelligence Platform
            </h1>
            <p className="hidden sm:block text-xs text-teal-800/70 truncate font-medium">
              AI-assisted inspection dashboard
            </p>
          </motion.div>
        </div>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          {userName ? (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="hidden sm:inline text-xs font-medium text-teal-900/70 max-w-[140px] truncate"
            >
              {userName}
            </motion.span>
          ) : null}
          <MotionButton
            type="button"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={onLogout}
            className="btn-secondary px-3 py-2 text-sm !border-red-100 !bg-red-50/90 !text-red-800 hover:!bg-red-100 hover:!border-red-200"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </MotionButton>
        </div>
      </div>
    </MotionHeader>
  );
};

export default Header;
