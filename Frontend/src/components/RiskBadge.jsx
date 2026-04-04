import { motion } from 'framer-motion';
import ScoreRiskBadge from './ScoreRiskBadge';

const RiskBadge = ({ level, score, reason, risk }) => {
  const MotionDiv = motion.div;

  const getGradient = (level) => {
    switch (level) {
      case 'CLEAR':
        return 'from-emerald-700 to-emerald-500';
      case 'SUSPICIOUS':
        return 'from-orange-700 to-orange-500';
      case 'PROHIBITED':
        return 'from-red-700 to-red-500';
      default:
        return 'from-gray-700 to-gray-500';
    }
  };

  const getTextColor = (level) => {
    switch (level) {
      case 'CLEAR':
      case 'SUSPICIOUS':
      case 'PROHIBITED':
        return 'text-white';
      default:
        return 'text-gray-900';
    }
  };

  const getAnimation = (level) => {
    if (level === 'PROHIBITED') {
      return {
        animate: {
          boxShadow: [
            '0 0 20px rgba(198, 40, 40, 0.4)',
            '0 0 30px rgba(198, 40, 40, 0.6)',
            '0 0 20px rgba(198, 40, 40, 0.4)'
          ]
        },
        transition: {
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }
      };
    }
    return {};
  };

  return (
    <div className="space-y-4">
      <MotionDiv
        className={`w-full bg-gradient-to-r ${getGradient(level)} rounded-2xl p-7 sm:p-8 ${getTextColor(level)} shadow-[0_16px_50px_rgba(15,23,42,0.12)]`}
        {...getAnimation(level)}
      >
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest opacity-90">
              Risk assessment
            </div>
            <div className="text-3xl sm:text-4xl font-bold uppercase tracking-wider mt-1">
              {level || 'UNKNOWN'}
            </div>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xs font-semibold uppercase tracking-widest opacity-90">
              Score
            </div>
            <div className="text-2xl sm:text-3xl font-semibold tabular-nums">
              {typeof score === 'number' ? `${score}/100` : '—'}
            </div>
          </div>
        </div>
      </MotionDiv>
      
      {reason && (
        <div className="card">
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Summary</h4>
          <p className="text-slate-700 leading-relaxed">
            {reason}
          </p>
        </div>
      )}

      {risk?.decision && (
        <ScoreRiskBadge
          decision={risk.decision}
          final_risk={risk.final_risk}
          visual_risk={risk.visual_risk}
          data_risk={risk.data_risk}
          risk_breakdown={risk.risk_breakdown}
        />
      )}
    </div>
  );
};

export default RiskBadge;
