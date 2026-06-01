import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {BODY_FONT, DISPLAY_FONT} from '../fonts';
import {resolveMotionTheme} from '../types';
import {AnimatedBarChart} from '../charts/AnimatedBarChart';
import {AnimatedLineChart} from '../charts/AnimatedLineChart';
import {MidStageEffects} from '../effects/MidStageEffects';
import {HeroTypewriter} from './HeroTypewriter';
import {MidInfoPanels} from '../info/MidInfoPanels';

interface Props {
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
  midEffect?: string;
  midInfoLayout?: string;
  summaryRevealFrames?: number[];
  panelRevealFrame?: number;
}

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
  midEffect = 'glow_ring',
  midInfoLayout = 'keywords',
  summaryRevealFrames = [],
  panelRevealFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const theme = resolveMotionTheme('tiktok', colorMood);

  const hero = (summaryLines[0] || featureLabel || '核心亮点').slice(0, 16);
  const subLines = summaryLines.length > 1 ? summaryLines.slice(1, 3) : [];
  const heroFrame = summaryRevealFrames[0] ?? 0;
  const panelFrame = panelRevealFrame > 0 ? panelRevealFrame : summaryRevealFrames[1] ?? 18;
  const viz = (vizType || 'none').toLowerCase();
  const series = (chartSeries.length ? chartSeries : chartBars).filter((n) => Number(n) > 0);
  const showLine = showChart && viz === 'line' && series.length >= 3;
  const showBar = showChart && viz === 'bar' && series.length >= 2;
  const showStat = viz === 'stat' && Boolean(statValue);
  const icon = (midIcon || '').trim() || (showLine ? '📈' : showStat ? '⭐' : '');

  const effects = ['glow_ring', 'typewriter', 'particle_dust', 'bracket_slam', 'glow_scan'];
  const effect =
    midEffect && midEffect !== 'auto'
      ? midEffect
      : effects[sceneIndex % effects.length];
  const useTypewriter = effect === 'typewriter';

  const enter = spring({
    frame: Math.max(0, frame - heroFrame),
    fps,
    config: {damping: 16, stiffness: 140},
  });
  const chips = showKineticWall ? kineticPhrases.slice(0, 4) : [];
  const heroSize = Math.min(72, Math.floor(width / Math.max(5, hero.length * 0.52)));

  const safeTop = Math.round(height * 0.14);
  const safeBottom = Math.round(height * 0.36);

  return (
    <>
      <MidStageEffects
        effect={effect === 'kinetic_wall' ? 'particle_dust' : effect}
        accentColor={accentColor}
        accentColor2={accentColor2}
        width={width}
        height={height}
      />

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
          gap: 18,
        }}
      >
        {icon ? (
          <div
            style={{
              fontSize: 52,
              lineHeight: 1,
              opacity: enter,
              transform: `scale(${interpolate(enter, [0, 1], [1.25, 1])})`,
            }}
          >
            {icon}
          </div>
        ) : null}

        {useTypewriter ? (
          <HeroTypewriter
            text={hero}
            fontSize={heroSize}
            color={theme.fg}
            accentColor={accentColor2}
            startFrame={heroFrame}
          />
        ) : (
          <div
            style={{
              fontFamily: DISPLAY_FONT,
              fontSize: heroSize,
              fontWeight: 900,
              color: theme.fg,
              textAlign: 'center',
              lineHeight: 1.15,
              maxWidth: width * 0.88,
              opacity: enter,
              transform: `translateY(${(1 - enter) * 20}px) scale(${interpolate(enter, [0, 1], [1.08, 1])})`,
              textShadow: `0 4px 28px rgba(0,0,0,0.55), 0 0 40px ${accentColor}33`,
              wordBreak: 'keep-all',
            }}
          >
            {hero}
          </div>
        )}

        {subLines.map((line, i) => {
          const lineFrame = summaryRevealFrames[i + 1] ?? heroFrame + 12 + i * 10;
          const s = spring({
            frame: Math.max(0, frame - lineFrame),
            fps,
            config: {damping: 18, stiffness: 120},
          });
          return (
            <div
              key={`${i}-${line}`}
              style={{
                fontFamily: BODY_FONT,
                fontSize: 30,
                fontWeight: 600,
                color: theme.fg,
                opacity: s * 0.9,
                textAlign: 'center',
                maxWidth: width * 0.85,
                wordBreak: 'keep-all',
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
              opacity: spring({frame: Math.max(0, frame - 16), fps, config: {damping: 10, stiffness: 200}}),
              textShadow: `0 0 24px ${accentColor2}88`,
            }}
          >
            {statValue}
          </div>
        ) : null}

        {showLine ? (
          <div style={{width: '100%', maxWidth: 820}}>
            <AnimatedLineChart
              label={chartLabel || '趋势'}
              unit={chartUnit}
              series={series}
              accentColor={accentColor}
              accentColor2={accentColor2}
              startFrame={22}
            />
          </div>
        ) : null}

        {showBar ? (
          <div style={{width: '100%', maxWidth: 820}}>
            <AnimatedBarChart
              label={chartLabel || '对比'}
              unit={chartUnit}
              bars={series}
              accentColor={accentColor}
              accentColor2={accentColor2}
              startFrame={22}
            />
          </div>
        ) : null}

        {!showLine && !showBar && !showStat ? (
          <MidInfoPanels
            layout={midInfoLayout}
            summaryLines={summaryLines}
            kineticPhrases={kineticPhrases}
            accentColor={accentColor}
            accentColor2={accentColor2}
            panelRevealFrame={panelFrame}
            stepRevealFrames={summaryRevealFrames.slice(1)}
          />
        ) : null}

        {chips.length > 0 && !showLine && !showBar && midInfoLayout === 'none' ? (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: 8,
              maxWidth: width * 0.9,
            }}
          >
            {chips.map((word, i) => {
              const s = spring({
                frame: Math.max(0, frame - 28 - i * 5),
                fps,
                config: {damping: 14, stiffness: 180},
              });
              return (
                <span
                  key={`${i}-${word}`}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 8,
                    background: `${accentColor}28`,
                    border: `1px solid ${accentColor}55`,
                    fontFamily: BODY_FONT,
                    fontSize: 22,
                    fontWeight: 700,
                    color: theme.fg,
                    opacity: s,
                    transform: `translateY(${(1 - s) * 10}px)`,
                    wordBreak: 'keep-all',
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
