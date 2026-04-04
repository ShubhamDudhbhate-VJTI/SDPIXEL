import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

const MotionDiv = motion.div;
const MotionH1 = motion.h1;
const MotionP = motion.p;
const MotionH3 = motion.h3;
const MotionLi = motion.li;

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.04 },
  },
};

const item = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 280, damping: 26 },
  },
};

const HomePage = () => {
  return (
    <div className="min-h-[calc(100vh-10.5rem)] flex flex-col">
      <MotionDiv
        variants={container}
        initial="hidden"
        animate="show"
        className="relative flex flex-1 flex-col overflow-hidden rounded-3xl border border-teal-100/70 bg-gradient-to-br from-white via-teal-50/25 to-cyan-50/40 shadow-[0_24px_80px_rgba(13,148,136,0.1)] transition-shadow duration-500 hover:shadow-[0_28px_90px_rgba(13,148,136,0.14)]"
      >
        <div className="pointer-events-none absolute -left-32 top-1/4 h-72 w-72 rounded-full bg-teal-400/15 blur-3xl motion-safe:animate-float-soft" />
        <div className="pointer-events-none absolute -right-24 bottom-0 h-96 w-96 rounded-full bg-cyan-400/12 blur-3xl" />
        <div className="pointer-events-none absolute left-1/2 top-0 h-px w-[min(100%,48rem)] -translate-x-1/2 bg-gradient-to-r from-transparent via-teal-300/50 to-transparent" />

        <div className="relative flex flex-1 flex-col px-6 py-10 sm:px-10 sm:py-14 lg:px-14 lg:py-16">
          <MotionDiv
            variants={item}
            whileHover={{ scale: 1.03, boxShadow: '0 8px 24px rgba(13, 148, 136, 0.2)' }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex w-fit cursor-default items-center gap-2 rounded-full border border-teal-200/90 bg-white/95 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-teal-800 shadow-sm transition-colors duration-300"
          >
            <motion.span
              animate={{ rotate: [0, 12, -12, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Sparkles className="h-3.5 w-3.5 text-teal-600" />
            </motion.span>
            Secure customs workflow
          </MotionDiv>

          <MotionH1
            variants={item}
            className="mt-6 max-w-4xl text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl lg:leading-[1.08]"
          >
            Customs X-ray Intelligence Platform
          </MotionH1>

          <MotionP
            variants={item}
            className="mt-5 max-w-3xl text-xl font-medium leading-snug text-teal-950/90 sm:text-2xl"
          >
            Faster, explainable AI assistance for cargo screening, manifest verification, and risk-aware
            inspection decisions.
          </MotionP>

          <div className="mt-10 grid flex-1 gap-10 lg:grid-cols-12 lg:gap-12 lg:items-start">
            <div className="space-y-6 text-base leading-relaxed text-slate-600 lg:col-span-7">
              <MotionP variants={item} className="max-w-prose">
                The platform brings together X-ray imagery, optional cargo manifest PDFs, and modern computer
                vision so officers can move from raw scans to structured findings in one place. Upload a scan,
                attach supporting documents when available, and run the full analysis pipeline to obtain
                detections, risk context, and visual explanations such as heatmaps and comparisons.
              </MotionP>
              <MotionP variants={item} className="max-w-prose">
                Declared items from manifests can be aligned with model outputs to highlight potential gaps or
                inconsistencies. The interface is designed for training sessions, lab demos, and repeatable
                workflows: every completed run can be recorded with a transaction identifier for later review in
                this browser.
              </MotionP>
              <MotionP variants={item} className="max-w-prose border-l-4 border-teal-500 pl-5 text-slate-700">
                Use the <strong className="font-semibold text-slate-900">Menu</strong> control to open navigation
                and reach <strong className="font-semibold text-slate-900">Start PDF and scan analysis</strong>,{' '}
                <strong className="font-semibold text-slate-900">Lookup transaction</strong>, or{' '}
                <strong className="font-semibold text-slate-900">Help</strong> whenever you need them.
              </MotionP>
            </div>

            <aside className="space-y-6 lg:col-span-5 lg:border-l lg:border-teal-100 lg:pl-10">
              <MotionH3 variants={item} className="text-sm font-bold uppercase tracking-wider text-teal-800/70">
                What you can do here
              </MotionH3>
              <ul className="space-y-5 text-sm leading-relaxed text-slate-600">
                <MotionLi
                  variants={item}
                  whileHover={{ x: 6 }}
                  className="cursor-default rounded-lg py-0.5 transition-colors duration-200 hover:text-teal-900"
                >
                  <span className="font-semibold text-slate-900">Scan analysis</span> — Run detection and risk
                  scoring on cargo X-rays, with optional reference scans for change highlighting.
                </MotionLi>
                <MotionLi
                  variants={item}
                  whileHover={{ x: 6 }}
                  className="cursor-default rounded-lg py-0.5 transition-colors duration-200 hover:text-teal-900"
                >
                  <span className="font-semibold text-slate-900">Manifest intelligence</span> — Extract and
                  compare declared cargo from PDF manifests against automated findings.
                </MotionLi>
                <MotionLi
                  variants={item}
                  whileHover={{ x: 6 }}
                  className="cursor-default rounded-lg py-0.5 transition-colors duration-200 hover:text-teal-900"
                >
                  <span className="font-semibold text-slate-900">Explainability</span> — Review overlays,
                  Grad-CAM-style cues, and reports suitable for briefing or audit trails.
                </MotionLi>
                <MotionLi
                  variants={item}
                  whileHover={{ x: 6 }}
                  className="cursor-default rounded-lg py-0.5 transition-colors duration-200 hover:text-teal-900"
                >
                  <span className="font-semibold text-slate-900">Session history</span> — Retrieve summaries of
                  past runs using the transaction IDs generated after each successful analysis.
                </MotionLi>
              </ul>
            </aside>
          </div>
        </div>
      </MotionDiv>
    </div>
  );
};

export default HomePage;
