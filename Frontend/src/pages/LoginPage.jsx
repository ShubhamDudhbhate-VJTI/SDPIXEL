import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Shield, User } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const MotionDiv = motion.div;
const MotionForm = motion.form;
const MotionButton = motion.button;

const LoginPage = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/';

  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [shake, setShake] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate(from, { replace: true });
  }, [isAuthenticated, from, navigate]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
      return;
    }
    login(name, password);
    navigate(from, { replace: true });
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-950 via-teal-950 to-cyan-950 flex items-center justify-center p-4">
      <div className="pointer-events-none absolute inset-0">
        <MotionDiv
          className="absolute -top-32 -right-24 h-96 w-96 rounded-full bg-teal-500/25 blur-3xl"
          animate={{ scale: [1, 1.12, 1], opacity: [0.4, 0.65, 0.4] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
        />
        <MotionDiv
          className="absolute -bottom-24 -left-16 h-80 w-80 rounded-full bg-cyan-500/20 blur-3xl"
          animate={{ scale: [1.08, 1, 1.08], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
        />
        <MotionDiv
          className="absolute left-1/2 top-1/2 h-[min(90vw,28rem)] w-[min(90vw,28rem)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-teal-400/10"
          animate={{ rotate: 360 }}
          transition={{ duration: 120, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      <MotionDiv
        initial={{ opacity: 0, y: 28, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 22 }}
        className="relative w-full max-w-md"
      >
        <div className="mb-8 text-center">
          <MotionDiv
            initial={{ scale: 0.85, opacity: 0, rotate: -8 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            transition={{ delay: 0.08, type: 'spring', stiffness: 280, damping: 18 }}
            whileHover={{ scale: 1.05, rotate: 2 }}
            className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 via-teal-600 to-cyan-600 text-white shadow-xl shadow-teal-900/40 animate-pulse-glow"
          >
            <Shield className="w-8 h-8" />
          </MotionDiv>
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="text-2xl font-bold tracking-tight text-white sm:text-3xl"
          >
            Customs X-ray Intelligence
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
            className="mt-2 text-sm text-teal-100/90"
          >
            Sign in to access the inspection workspace.
          </motion.p>
        </div>

        <MotionForm
          animate={shake ? { x: [0, -10, 10, -8, 8, 0] } : {}}
          transition={{ duration: 0.5 }}
          onSubmit={handleSubmit}
          whileHover={{ boxShadow: '0 25px 50px -12px rgba(13, 148, 136, 0.25)' }}
          className="rounded-2xl border border-teal-200/30 bg-white/95 p-6 shadow-2xl shadow-teal-950/30 backdrop-blur-md transition-shadow duration-500"
        >
          <div className="space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Display name
              </span>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Officer Kumar"
                  className="focus-brand w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 transition-all duration-200"
                  autoComplete="username"
                />
              </div>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Password
              </span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="focus-brand w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 transition-all duration-200"
                  autoComplete="current-password"
                />
              </div>
            </label>
          </div>

          <MotionButton
            type="submit"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="btn-primary mt-6 w-full py-3.5 text-base"
          >
            Continue to dashboard
          </MotionButton>

          <p className="mt-4 text-center text-xs text-slate-500">
            Demo mode: use any non-empty password. Credentials stay in this browser only.
          </p>
        </MotionForm>
      </MotionDiv>
    </div>
  );
};

export default LoginPage;
