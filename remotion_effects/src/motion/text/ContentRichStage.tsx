import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {BODY_FONT, DISPLAY_FONT} from '../fonts';
import {resolveMotionTheme} from '../types';
import {AnimatedBarChart} from '../charts/AnimatedBarChart';
import {AnimatedLineChart} from '../charts/AnimatedLineChart';
import {MidStageEffects} from '../effects/MidStageEffects';
import {HeroTypewriter} from './HeroTypewriter';
import {LiquidShakeText} from './LiquidShakeText';
import {MidInfoPanels} from '../info/MidInfoPanels';
import {getLayoutZones} from '../layout/safeZones';

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
  captionPlatform?: string;
  midHeroMaxChars?: number;
  midHeroFontScale?: number;
  midSafeBottomRatio?: number;
  midSafeTopRatio?: number;
  captionBottomPx?: number;
  staggerFrames?: number;
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
  captionPlatform = '',
  midHeroMaxChars = 16,
  midHeroFontScale = 1,
  midSafeBottomRatio,
  midSafeTopRatio,
  captionBottomPx,
  staggerFrames = 18,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const isXhs =
    captionPlatform === 'xhs' ||
    colorMood === 'xhs-editorial' ||
    colorMood === 'xhs';
  const theme = resolveMotionTheme(isXhs ? 'xhs' : 'tiktok', colorMood);
  const zones = getLayoutZones(captionPlatform, height, {
    captionBottomPx,
    midSafeBottomRatio,
    midSafeTopRatio,
  });

  const heroMax = midHeroMaxChars || (isXhs ? 14 : 16);
  const hero = (featureLabel || summaryLines[0] || '').slice(0, heroMax);
  const layoutKind = (midInfoLayout || '').toLowerCase();
  const panelMax = isXhs ? 2 : layoutKind === 'steps' || layoutKind === 'framed' ? 4 : 3;
  const panelLines = featureLabel
    ? summaryLines.slice(0, panelMax)
    : summaryLines.length > 1
      ? summaryLines.slice(1, panelMax + 1)
      : summaryLines.slice(0, panelMax);
  const usePanelLayout = ['keywords', 'steps', 'compare', 'framed'].includes(
    (midInfoLayout || '').toLowerCase(),
  );
  const stagger = Math.max(14, staggerFrames ?? 18);
  const panelFrame =
    panelRevealFrame > 0
      ? panelRevealFrame
      : summaryRevealFrames[0] ?? 18;
  const heroFrame = Math.max(0, panelFrame - 12);
  const subtitleRevealFrames: number[] =
    summaryRevealFrames.length >= panelLines.length
      ? summaryRevealFrames.map((f, i, arr) =>
          i === 0 ? f : Math.max(f, (arr[i - 1] ?? 0) + stagger),
        )
      : panelLines.map((_, i) => panelFrame + i * stagger);
  const viz = (vizType || 'none').toLowerCase();
  const series = (chartSeries.length ? chartSeries : chartBars).filter((n) => Number(n) > 0);
  const showLine = showChart && viz === 'line' && series.length >= 3;
  const showBar = showChart && viz === 'bar' && series.length >= 2;
  const showStat = viz === 'stat' && Boolean(statValue);
  const icon = (midIcon || '').trim() || (showLine ? '📈' : showStat ? '⭐' : '');

  const effects = [
    'glow_ring',
    'typewriter',
    'particle_dust',
    'bracket_slam',
    'glow_scan',
    'liquid_shake',
  ];
  const effect =
    midEffect && midEffect !== 'auto'
      ? midEffect
      : effects[sceneIndex % effects.length];
  const useTypewriter = effect === 'typewriter';
  const useLiquidShake =
    effect === 'liquid_shake' || effect === 'shake_emphasis' || effect === 'glow_scan';

  const enter = spring({
    frame: Math.max(0, frame - heroFrame),
    fps,
    config: isXhs
      ? {damping: 22, stiffness: 90}
      : {damping: 16, stiffness: 140},
  });
  const chips = showKineticWall ? kineticPhrases.slice(0, isXhs ? 3 : 4) : [];
  const heroBase = isXhs ? 50 : 88;
  const hasBelowHero =
    panelLines.length > 0 || usePanelLayout || chips.length > 0;
  const heroSize = Math.min(
    heroBase * midHeroFontScale,
    Math.floor(width / Math.max(isXhs ? 6 : 5, hero.length * (isXhs ? 0.46 : 0.52))),
  );

  const safeTop = Math.round(height * zones.midSafeTopRatio);
  const safeBottom = Math.round(height * zones.midSafeBottomRatio);

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
          maxHeight: height - safeTop - safeBottom,
          overflow: 'hidden',
        }}
      >
        {/* 主标题区：始终水平居中，不与子标题列共左缘 */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            gap: isXhs ? 18 : 14,
            flexShrink: 0,
          }}
        >
        {icon ? (
          <div
            style={{
              fontSize: 52,
              lineHeight: 1,
              opacity: enter,
              alignSelf: 'center',
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
        ) : useLiquidShake ? (
          <LiquidShakeText
            text={hero}
            fontSize={heroSize}
            color={theme.fg}
            accentColor={accentColor2}
            startFrame={heroFrame}
            settleFrames={28}
          />
        ) : (
          <div
            style={{
              fontFamily: DISPLAY_FONT,
              fontSize: heroSize,
              fontWeight: 900,
              color: theme.fg,
              textAlign: 'center',
              lineHeight: isXhs ? 1.28 : 1.12,
              letterSpacing: isXhs ? 2 : 0,
              maxWidth: width * 0.84,
              opacity: enter,
              transform: `translateY(${(1 - enter) * 20}px) scale(${interpolate(enter, [0, 1], [1.08, 1])})`,
              textShadow: `0 4px 28px rgba(0,0,0,0.55), 0 0 40px ${accentColor}33`,
              wordBreak: 'keep-all',
              alignSelf: 'center',
            }}
          >
            {hero}
          </div>
        )}
        </div>

        {hasBelowHero && (usePanelLayout || panelLines.length > 0) ? (
          <div
            style={{
              width: Math.min(width * 0.72, 520),
              height: 2,
              marginTop: isXhs ? 16 : 20,
              marginBottom: isXhs ? 4 : 8,
              alignSelf: 'center',
              background: `linear-gradient(90deg, transparent, ${accentColor}88, transparent)`,
              opacity: enter * 0.85,
              flexShrink: 0,
            }}
          />
        ) : null}

        {!usePanelLayout && panelLines.length > 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              alignSelf: 'center',
              gap: 20,
              marginTop: isXhs ? 20 : 28,
            }}
          >
            {panelLines.map((line, i) => {
              const lineFrame = subtitleRevealFrames[i] ?? panelFrame + i * stagger;
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
                    fontSize: isXhs ? 28 : 34,
                    fontWeight: 600,
                    color: theme.fg,
                    opacity: s * 0.9,
                    textAlign: 'left',
                    lineHeight: isXhs ? 1.35 : 1.22,
                    letterSpacing: 0,
                    maxWidth: width * 0.82,
                    wordBreak: 'keep-all',
                  }}
                >
                  {line}
                </div>
              );
            })}
          </div>
        ) : null}

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

        {!showLine && !showBar && !showStat && usePanelLayout ? (
          <div
            style={{
              alignSelf: 'center',
              marginTop: isXhs ? 20 : 28,
              width: 'fit-content',
              maxWidth: '100%',
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <MidInfoPanels
              layout={midInfoLayout}
              summaryLines={panelLines}
              kineticPhrases={kineticPhrases}
              accentColor={accentColor}
              accentColor2={accentColor2}
              panelRevealFrame={panelFrame}
              stepRevealFrames={subtitleRevealFrames}
            />
          </div>
        ) : null}

        {chips.length > 0 && !showLine && !showBar && midInfoLayout === 'none' ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              alignSelf: 'center',
              gap: 16,
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
