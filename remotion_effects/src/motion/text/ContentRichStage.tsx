import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {DISPLAY_FONT, BODY_FONT} from '../fonts';
import {resolveMotionTheme} from '../types';
import {AnimatedBarChart} from '../charts/AnimatedBarChart';
import {AnimatedLineChart} from '../charts/AnimatedLineChart';

interface Props {
  heading?: string;
  featureLabel?: string;
  summaryLines?: string[];
  kineticPhrases?: string[];
  sceneIndex?: number;
  sceneTotal?: number;
  accentColor?: string;
  accentColor2?: string;
  colorMood?: string;
  vizType?: string;
  showChart?: boolean;
  chartBars?: number[];
  chartSeries?: number[];
  chartLabel?: string;
  chartUnit?: string;
  statValue?: string;
  showKineticWall?: boolean;
  midIcon?: string;
}

/**
 * 中部安全区垂直居中：顶栏场景标 + 底栏字幕留白，主体在中间 1/3~2/3 视觉重心。
 * 图表仅 viz=line|bar 时出现；无图表时用大字 + 可选词芯片。
 */
export const ContentRichStage: React.FC<Props> = ({
  featureLabel = '',
  summaryLines = [],
  kineticPhrases = [],
  sceneIndex = 0,
  sceneTotal = 3,
  accentColor = '#3b82f6',
  accentColor2 = '#22d3ee',
  colorMood = 'warm',
  vizType = 'none',
  showChart = false,
  chartBars = [],
  chartSeries = [],
  chartLabel = '',
  chartUnit = '',
  statValue = '',
  showKineticWall = false,
  midIcon = '',
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const theme = resolveMotionTheme('tiktok', colorMood);

  const hero = (summaryLines[0] || featureLabel || '核心亮点').slice(0, 16);
  const subLines = summaryLines.length > 1 ? summaryLines.slice(1, 3) : [];
  const viz = (vizType || 'none').toLowerCase();
  const series = (chartSeries.length ? chartSeries : chartBars).filter((n) => Number(n) > 0);
  const showLine = showChart && viz === 'line' && series.length >= 3;
  const showBar = showChart && viz === 'bar' && series.length >= 2;
  const showStat = viz === 'stat' && Boolean(statValue);
  const icon = (midIcon || '').trim() || (showLine ? '📈' : showStat ? '⭐' : '');

  const enter = spring({frame, fps, config: {damping: 16, stiffness: 140}});
  const chips = showKineticWall ? kineticPhrases.slice(0, 5) : [];

  const safeTop = Math.round(height * 0.14);
  const safeBottom = Math.round(height * 0.36);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: safeTop - 8,
          left: 32,
          padding: '6px 14px',
          borderRadius: 6,
          border: `1px solid ${accentColor}55`,
          fontFamily: BODY_FONT,
          fontSize: 18,
          fontWeight: 700,
          color: accentColor,
          opacity: enter,
          zIndex: 22,
        }}
      >
        {sceneIndex + 1}/{sceneTotal}
      </div>

      <div
        style={{
          position: 'absolute',
          top: safeTop,
          bottom: safeBottom,
          left: 40,
          right: 40,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 20,
          gap: 20,
        }}
      >
        {icon ? (
          <div
            style={{
              fontSize: 56,
              lineHeight: 1,
              opacity: enter,
              transform: `scale(${interpolate(enter, [0, 1], [1.3, 1])})`,
            }}
          >
            {icon}
          </div>
        ) : null}

        <div
          style={{
            fontFamily: DISPLAY_FONT,
            fontSize: Math.min(72, Math.floor(width / Math.max(6, hero.length * 0.55))),
            fontWeight: 900,
            color: theme.fg,
            textAlign: 'center',
            lineHeight: 1.15,
            maxWidth: width * 0.88,
            opacity: enter,
            transform: `translateY(${(1 - enter) * 24}px)`,
            textShadow: `0 4px 24px rgba(0,0,0,0.5)`,
          }}
        >
          {hero}
        </div>

        {subLines.map((line, i) => {
          const s = spring({
            frame: Math.max(0, frame - 10 - i * 8),
            fps,
            config: {damping: 18, stiffness: 120},
          });
          return (
            <div
              key={`${i}-${line}`}
              style={{
                fontFamily: BODY_FONT,
                fontSize: 32,
                fontWeight: 600,
                color: theme.fg,
                opacity: s * 0.92,
                textAlign: 'center',
                maxWidth: width * 0.85,
              }}
            >
              {line}
            </div>
          );
        })}

        {showStat ? (
          <div
            style={{
              fontFamily: DISPLAY_FONT,
              fontSize: 48,
              fontWeight: 900,
              color: accentColor2,
              opacity: spring({frame: Math.max(0, frame - 14), fps}),
              textShadow: `0 0 20px ${accentColor2}66`,
            }}
          >
            {statValue}
          </div>
        ) : null}

        {showLine ? (
          <div style={{width: '100%', maxWidth: 820, marginTop: 8}}>
            <AnimatedLineChart
              label={chartLabel || '趋势'}
              unit={chartUnit}
              series={series}
              accentColor={accentColor}
              accentColor2={accentColor2}
              startFrame={20}
            />
          </div>
        ) : null}

        {showBar ? (
          <div style={{width: '100%', maxWidth: 820, marginTop: 8}}>
            <AnimatedBarChart
              label={chartLabel || '对比'}
              unit={chartUnit}
              bars={series}
              accentColor={accentColor}
              accentColor2={accentColor2}
              startFrame={20}
            />
          </div>
        ) : null}

        {chips.length > 0 && !showLine && !showBar ? (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: 8,
              maxWidth: width * 0.9,
              marginTop: 12,
            }}
          >
            {chips.map((word, i) => {
              const s = spring({
                frame: Math.max(0, frame - 24 - i * 4),
                fps,
                config: {damping: 14, stiffness: 180},
              });
              return (
                <span
                  key={`${i}-${word}`}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 8,
                    background: `${accentColor}22`,
                    border: `1px solid ${accentColor}44`,
                    fontFamily: BODY_FONT,
                    fontSize: 22,
                    fontWeight: 700,
                    color: theme.fg,
                    opacity: s,
                  }}
                >
                  {word}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </>
  );
};
