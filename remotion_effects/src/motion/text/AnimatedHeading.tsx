import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import type {MotionParams, MotionProfileId} from '../types';
import {resolveMotionTheme} from '../types';
import {DISPLAY_FONT} from '../fonts';
import {
  accentOrangeLastWord,
  headingStyleForDecorations,
} from '../decorations/GithubDailyDecorations';

interface Props {
  text: string;
  subtext?: string;
  profile: MotionProfileId | string;
  params?: MotionParams;
  layout?: 'center' | 'top-heavy';
  cssDecorations?: string[];
  colorMood?: string;
  /** 片头 HookBurst 结束后再入场 */
  startFrame?: number;
}

function splitWords(s: string): string[] {
  return s.split(/(\s+)/).filter((w) => w.trim().length > 0);
}

function splitChars(s: string): string[] {
  return Array.from(s);
}


export const AnimatedHeading: React.FC<Props> = ({
  text,
  subtext = '',
  profile,
  params = {},
  layout = 'center',
  cssDecorations = [],
  colorMood = '',
  startFrame = 0,
}) => {
  const frame = Math.max(0, useCurrentFrame() - startFrame);
  const {fps, width, height} = useVideoConfig();
  const p = String(profile);
  const theme = resolveMotionTheme(p, colorMood);
  const stagger = params.staggerFrames ?? (p.includes('tight') ? 3 : 6);
  const damp = params.springDamping ?? 14;
  const stiff = params.springStiffness ?? 120;
  const hasSub = Boolean((subtext || '').trim());
  const effectiveLayout = hasSub ? 'top-heavy' : layout;

  const wrapper: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width,
    height,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: effectiveLayout === 'top-heavy' ? 'flex-start' : 'center',
    paddingTop: effectiveLayout === 'top-heavy' ? (hasSub ? 168 : 200) : 0,
    paddingLeft: 56,
    paddingRight: 56,
    textAlign: 'center',
    zIndex: 10,
    boxSizing: 'border-box',
    fontFamily: DISPLAY_FONT,
  };

  // 顶栏 Topic 跑马 + 居中标题（G13）
  if (p === 'marquee_ticker') {
    const s = spring({frame, fps, config: {damping: damp, stiffness: stiff}});
    return (
      <div style={{...wrapper, paddingTop: 140}}>
        <div
          style={headingStyleForDecorations(cssDecorations, {
            fontSize: 64,
            fontWeight: 800,
            color: theme.fg,
            opacity: s,
            lineHeight: 1.2,
            maxWidth: 900,
          })}
        >
          {accentOrangeLastWord(text, cssDecorations)}
        </div>
      </div>
    );
  }

  // 极简：单行呼吸，无角标无粒子
  if (p === 'minimal_headline') {
    const breathe = 1 + Math.sin(frame / 18) * 0.02;
    const fade = spring({frame, fps, config: {damping: 22, stiffness: 70}});
    return (
      <div style={wrapper}>
        <div
          style={headingStyleForDecorations(cssDecorations, {
            fontSize: 64,
            fontWeight: 700,
            color: theme.fg,
            lineHeight: 1.2,
            opacity: fade,
            transform: `scale(${breathe})`,
            maxWidth: 900,
          })}
        >
          {accentOrangeLastWord(text, cssDecorations)}
        </div>
        {subtext && (
          <div style={{marginTop: 40, fontSize: 32, color: theme.accent, opacity: fade * 0.9}}>
            {subtext}
          </div>
        )}
      </div>
    );
  }

  // 遮罩横向揭示
  if (p === 'split_mask_reveal') {
    const reveal = interpolate(frame, [0, 22], [0, 100], {extrapolateRight: 'clamp'});
    return (
      <div style={wrapper}>
        <div
          style={{
            fontSize: 72,
            fontWeight: 900,
            color: theme.fg,
            clipPath: `inset(0 ${100 - reveal}% 0 0)`,
            lineHeight: 1.15,
          }}
        >
          {text}
        </div>
      </div>
    );
  }

  // 微震强调（口播钩子）
  if (p === 'shake_emphasis') {
    const enter = spring({frame, fps, config: {damping: damp, stiffness: stiff}});
    const shake = frame > 8 && frame < 28 ? Math.sin(frame * 2.5) * 4 : 0;
    return (
      <div style={{...wrapper, transform: `translateX(${shake}px)`}}>
        <div
          style={{
            fontSize: 70,
            fontWeight: 900,
            color: theme.fg,
            opacity: enter,
            transform: `scale(${interpolate(enter, [0, 1], [1.15, 1])})`,
          }}
        >
          {text}
        </div>
      </div>
    );
  }

  // 分栏（左文，右侧留给配图区）
  if (p === 'product_split_frame') {
    const s = spring({frame, fps, config: {damping: damp, stiffness: stiff}});
    return (
      <div
        style={{
          ...wrapper,
          alignItems: 'flex-start',
          textAlign: 'left',
          paddingTop: 220,
          paddingLeft: 72,
          maxWidth: '58%',
        }}
      >
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: theme.fg,
            opacity: s,
            transform: `translateY(${(1 - s) * 30}px)`,
            lineHeight: 1.2,
          }}
        >
          {text}
        </div>
        {subtext && (
          <div style={{marginTop: 24, fontSize: 30, color: theme.accent, opacity: s}}>{subtext}</div>
        )}
      </div>
    );
  }

  // TikTok 短语分页（每页 3~4 词，切页 spring）
  if (p === 'tiktok_phrase_pages') {
    const words = splitWords(text);
    const perPage = 4;
    const pageMs = params.wordsPerPageMs ?? 1000;
    const pageFrames = Math.max(18, Math.round((pageMs / 1000) * fps));
    const pageIdx = Math.min(
      Math.floor(frame / pageFrames),
      Math.max(0, Math.ceil(words.length / perPage) - 1),
    );
    const slice = words.slice(pageIdx * perPage, pageIdx * perPage + perPage);
    const localFrame = frame - pageIdx * pageFrames;
    return (
      <div style={wrapper}>
        <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 14, maxWidth: 920}}>
          {slice.map((unit, i) => {
            const s = spring({
              frame: Math.max(0, localFrame - i * 2),
              fps,
              config: {damping: 14, stiffness: 200},
            });
            return (
              <span
                key={`${pageIdx}-${i}`}
                style={{
                  fontSize: 68,
                  fontWeight: 900,
                  color: i === slice.length - 1 ? theme.accent2 || theme.accent : theme.fg,
                  transform: `scale(${interpolate(s, [0, 1], [1.2, 1])})`,
                  opacity: s,
                }}
              >
                {unit}
              </span>
            );
          })}
        </div>
      </div>
    );
  }

  const showGithubBadge =
    cssDecorations.includes('github-badge') ||
    ((p.includes('github_daily') || p.includes('glitch')) &&
      !p.includes('minimal') &&
      !p.includes('kinetic_slam'));

  const badge = showGithubBadge && (
      <div
        style={{
          marginBottom: 28,
          padding: '10px 22px',
          borderRadius: 8,
          border: `1px solid ${theme.accent}55`,
          color: theme.accent2 || theme.accent,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 2,
          fontFamily: 'Consolas, "Microsoft YaHei", sans-serif',
          opacity: spring({frame, fps, config: {damping: 20, stiffness: 80}}),
        }}
      >
        GITHUB · 今日开源
      </div>
    );

  if (p === 'glitch_hook_clean') {
    const glitchFrames = params.glitchFrames ?? 18;
    const isGlitch = frame < glitchFrames && frame % 4 < 2;
    return (
      <div style={wrapper}>
        <div
          style={{
            fontSize: 76,
            fontWeight: 900,
            color: theme.fg,
            transform: isGlitch ? `translate(${Math.sin(frame) * 6}px, 0)` : 'none',
            textShadow: isGlitch ? `2px 0 #ff0000, -2px 0 #00ffff` : 'none',
            lineHeight: 1.15,
          }}
        >
          {text}
        </div>
        {subtext && (
          <div style={{marginTop: 36, fontSize: 32, color: theme.accent, opacity: frame > glitchFrames ? 1 : 0}}>
            {subtext}
          </div>
        )}
      </div>
    );
  }

  if (p === 'episode_counter') {
    const numSpring = spring({frame, fps, config: {damping: 12, stiffness: 200}});
    const titleSpring = spring({frame: Math.max(0, frame - 10), fps, config: {damping: damp, stiffness: stiff}});
    const num = text.replace(/\D/g, '').slice(0, 3) || '01';
    const rest = text.replace(/^\d+\s*/, '') || text;
    return (
      <div style={wrapper}>
        <div style={{fontSize: 160, fontWeight: 900, color: theme.accent, transform: `scale(${numSpring})`, lineHeight: 1}}>
          {num}
        </div>
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: theme.fg,
            marginTop: 16,
            opacity: titleSpring,
            transform: `translateY(${(1 - titleSpring) * 40}px)`,
          }}
        >
          {rest}
        </div>
      </div>
    );
  }

  if (p === 'typewriter_terminal' || p.includes('terminal')) {
    const chars = splitChars(text);
    const visible = Math.min(chars.length, Math.floor(frame / 2));
    const cursor = frame % 30 < 15 ? '|' : '';
    return (
      <div style={{...wrapper, alignItems: 'flex-start', textAlign: 'left'}}>
        <div style={{fontFamily: 'Consolas, monospace', fontSize: 52, color: theme.accent, lineHeight: 1.3}}>
          {chars.slice(0, visible).join('')}
          <span style={{opacity: 0.9}}>{cursor}</span>
        </div>
      </div>
    );
  }

  const useChar = p === 'flash_hook_smash';
  const units = useChar ? splitChars(text) : splitWords(text);
  const unitStagger = useChar ? 2 : stagger;

  return (
    <div style={wrapper}>
      {badge}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: useChar ? 0 : 12,
          maxWidth: 920,
        }}
      >
        {units.map((unit, i) => {
          const delay = i * unitStagger;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: damp, stiffness: stiff, mass: useChar ? 0.4 : 0.8},
          });
          const scale = interpolate(s, [0, 1], [useChar ? 1.8 : 1.35, 1]);
          const y = interpolate(s, [0, 1], [useChar ? 60 : 40, 0]);
          return (
            <span
              key={`${unit}-${i}`}
              style={headingStyleForDecorations(
                i === 0 && cssDecorations.includes('text-stroke-yellow') ? cssDecorations : [],
                {
                  display: 'inline-block',
                  fontSize: useChar ? 88 : 72,
                  fontWeight: 900,
                  color: theme.fg,
                  transform: `scale(${scale}) translateY(${y}px)`,
                  opacity: s,
                  lineHeight: 1.1,
                },
              )}
            >
              {unit}
            </span>
          );
        })}
      </div>
      {subtext && (
        <div
          style={{
            marginTop: 44,
            fontSize: 34,
            color: theme.accent,
            lineHeight: 1.25,
            opacity: spring({
              frame: Math.max(0, frame - units.length * unitStagger - 8),
              fps,
              config: {damping: 18, stiffness: 90},
            }),
          }}
        >
          {subtext}
        </div>
      )}
    </div>
  );
};
