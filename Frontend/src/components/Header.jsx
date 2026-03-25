import { Shield, HelpCircle, History } from 'lucide-react';

const Header = () => {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur">
      <div className="container-page h-16 flex items-center gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/10 border border-blue-200/50">
            <Shield className="w-6 h-6 text-blue-700" />
          </div>
          <div className="min-w-0">
            <h1 className="text-[15px] sm:text-base font-semibold text-slate-900 leading-tight truncate">
              Customs X-ray Intelligence Platform
            </h1>
            <p className="hidden sm:block text-xs text-slate-500 truncate">
              AI-assisted inspection dashboard
            </p>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden md:inline-flex badge badge-slate">
            Model: Demo
          </span>
          <span className="hidden md:inline-flex badge badge-success">
            Status: Ready
          </span>

          <button className="btn-secondary px-3 py-2" type="button">
            <History className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </button>
          <button className="btn-secondary px-3 py-2" type="button" aria-label="Help">
            <HelpCircle className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
