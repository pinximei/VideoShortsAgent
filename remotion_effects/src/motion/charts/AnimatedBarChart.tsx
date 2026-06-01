import React from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {loadFont} from '@remotion/google-fonts/NotoSansSC';
import {BODY_FONT} from '../fonts';

const {fontFamily: chartFont} = loadFont();

/** 柱图：对齐 remotion-dev/skills rules/assets/charts-bar-chart.tsx（spring 逐柱） */
interface Props {
  label?: string;
  unit?: string;
  bars?: number[];
  accentColor?: string;
  accentColor2?: string;
  startFrame?: number;
}

export const AnimatedBarChart: React.FC<Props> = ({
  label = '趋势',
  unit = '',
  bars = [40, 65, 55, 80, 95],
  accentColor = '#3b82f6',
  accentColor2 = '#22d3ee',
  startFrame = 10,
}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const maxV = Math.max(...bars, 1);
  const chartHeight = Math.min(140, height * 0.12);

  return (
    <div
      style={{
        width: '100%',
        maxWidth: 880,
        padding: '20px 24px',
        borderRadius: 18,
        background: 'rgba(15,23,42,0.55)',
        border: `1px solid ${accentColor}44`,
        boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
        fontFamily: chartFont,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 16,
          fontFamily: BODY_FONT,
          fontSize: 22,
          fontWeight: 700,
          color: '#e2e8f0',
        }}
      >
        <span>{label}</span>
        {unit ? <span style={{color: accentColor2, fontSize: 18}}>{unit}</span> : null}
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 12,
          height: chartHeight,
          borderLeft: `2px solid ${accentColor}33`,
          borderBottom: `2px solid ${accentColor}33`,
          paddingLeft: 12,
        }}
      >
        {bars.map((target, i) => {
          const progress = spring({
            frame: frame - i * 5 - startFrame,
            fps,
            config: {damping: 18, stiffness: 80},
          });
          const barHeight = (target / maxV) * chartHeight * progress;
          return (
            <div
              key={i}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                height: '100%',
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: barHeight,
                  minHeight: progress > 0.01 ? 4 : 0,
                  borderRadius: '8px 8px 0 0',
                  background: `linear-gradient(to top, ${accentColor}, ${accentColor2})`,
                  opacity: progress,
                  boxShadow: `0 0 10px ${accentColor}44`,
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
