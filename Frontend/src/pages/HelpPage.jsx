import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, Keyboard, LifeBuoy } from 'lucide-react';

const MotionDiv = motion.div;
const MotionSpan = motion.span;

const faqs = [
  {
    q: 'How do I run an analysis?',
    a: 'Open Menu → Start PDF and scan analysis. Upload an X-ray image (or use Run demo analysis), optionally add a manifest PDF and reference scan, then click Analyze with AI.',
  },
  {
    q: 'Where is my transaction ID?',
    a: 'After each successful run, a banner appears at the top of the analysis page with a copyable ID. The same ID is listed under Lookup transaction → recent IDs.',
  },
  {
    q: 'Is my data sent to a server?',
    a: 'When you upload a real image, the frontend calls your local backend via /api/analyze. Transaction summaries are stored in this browser’s localStorage only.',
  },
  {
    q: 'Keyboard tips',
    a: 'On History, press Enter in the ID field to lookup. Tab through the login form; drawer closes when you pick a route or tap the backdrop.',
  },
];

const HelpPage = () => {
  const [open, setOpen] = useState(0);

  return (
    <div className="mx-auto max-w-3xl space-y-8 pt-2">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-teal-600/10 text-teal-700">
          <LifeBuoy className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Help & shortcuts</h2>
          <p className="mt-1 text-sm text-slate-600">
            Quick answers for navigating the Customs X-ray Intelligence workspace.
          </p>
        </div>
      </div>

      <MotionDiv
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-700"
      >
        <Keyboard className="h-5 w-5 shrink-0 text-teal-600" />
        <span>
          <strong className="font-semibold text-slate-900">Tip:</strong> Use the Menu button (below the header)
          to slide open navigation—links animate and the panel closes on outside click.
        </span>
      </MotionDiv>

      <div className="space-y-2">
        {faqs.map((item, idx) => {
          const isOpen = open === idx;
          return (
            <MotionDiv
              key={item.q}
              layout
              className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 shadow-sm"
            >
              <button
                type="button"
                onClick={() => setOpen(isOpen ? -1 : idx)}
                className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left text-sm font-semibold text-slate-900 hover:bg-slate-50/80"
              >
                {item.q}
                <MotionSpan animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
                  <ChevronDown className="h-5 w-5 shrink-0 text-slate-400" />
                </MotionSpan>
              </button>
              <AnimatePresence initial={false}>
                {isOpen ? (
                  <MotionDiv
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                    className="border-t border-slate-100"
                  >
                    <p className="px-4 py-3 text-sm leading-relaxed text-slate-600">{item.a}</p>
                  </MotionDiv>
                ) : null}
              </AnimatePresence>
            </MotionDiv>
          );
        })}
      </div>
    </div>
  );
};

export default HelpPage;
