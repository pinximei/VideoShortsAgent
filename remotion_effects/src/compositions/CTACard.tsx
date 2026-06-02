import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';
import {MotionSlideShell} from '../motion/decorations/MotionSlideShell';
import {SlideCaptionLayer} from '../motion/text/SlideCaptionLayer';
import type {MotionParams} from '../motion/types';
import {getLayoutZones} from '../motion/layout/safeZones';

/**
 * CTACard - 行动号召卡组件（升级版）
 *
 * 大号 CTA 文字 + 呼吸光圈 + 渐变流动按钮 + 倒影 + 打字机标题 + 箭头动画
 */
interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface CTACardProps {
  heading?: string;
  ctaText?: string;
  hookText?: string;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  colors?: string[];
  textColor?: string;
  accentColor?: string;
  imagePath?: string;
  sentences?: Sentence[];
  cameraPan?: string;
  particleType?: string;
  colorMood?: string;
  headingStartFrame?: number;
  accentColor2?: string;
  backgroundVariant?: string;
  useWeb3Background?: boolean;
  overlayOpacity?: number;
  decorationStyle?: string;
  textEffect?: 'glitch' | 'neon' | 'cinematic' | 'classic';
  motionProfile?: string;
  motionParams?: MotionParams;
  backgroundColor?: string;
  cssDecorations?: string[];
  captionMode?: string;
  captionPlatform?: string;
  broadcastFrame?: boolean;
  suppressBottomCaption?: boolean;
}

export const CTACard: React.FC<CTACardProps> = ({
  heading = '',
  ctaText = '',
  hookText = '',
  captionStyle = 'spring',
  colors = ['#e94560', '#533483'],
  textColor = '#ffffff',
  accentColor = '#ffdd57',
  imagePath,
  sentences = [],
  cameraPan = 'zoom-in',
  particleType = 'glow',
  colorMood = '',
  headingStartFrame = 0,
  accentColor2 = '#a855f7',
  backgroundVariant = 'mesh-aurora',
  useWeb3Background = true,
  overlayOpacity = 0.12,
  decorationStyle = 'cyber-grid',
  textEffect = 'neon',
  motionProfile = 'cta_pulse_arrow',
  motionParams = {},
  backgroundColor,
  cssDecorations = [],
  captionMode = '',
  captionPlatform = '',
  broadcastFrame = false,
  suppressBottomCaption = false,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const currentTime = frame / fps;

  if (motionProfile) {
    const pulse = spring({
      frame: Math.max(0, frame - headingStartFrame),
      fps,
      config: {damping: 10, stiffness: 120},
    });
    const ring = interpolate(frame % 45, [0, 45], [1, 1.25]);
    const pulseScale = cssDecorations.includes('pulse-button')
      ? 0.95 + pulse * 0.12
      : 0.95 + pulse * 0.08;
    const zones = getLayoutZones(captionPlatform, height, {
      captionBottomPx: motionParams.captionBottomPx,
      midSafeBottomRatio: motionParams.midSafeBottomRatio,
      midSafeTopRatio: motionParams.midSafeTopRatio,
    });
    const midTop = Math.round(height * zones.midSafeTopRatio);
    const midBottom = Math.round(height * zones.midSafeBottomRatio);
    const titleTop = midTop + Math.round((height - midTop - midBottom) * 0.2);
    return (
      <MotionSlideShell
        width={width}
        height={height}
        motionProfile={motionProfile}
        imagePath={imagePath}
        backgroundColor={backgroundColor}
        cssDecorations={cssDecorations}
        slideRole="cta"
        colorMood={colorMood}
        particleType={particleType}
        broadcastFrame={broadcastFrame}
        captionPlatform={captionPlatform}
        captionBottomPx={motionParams.captionBottomPx}
        midSafeBottomRatio={motionParams.midSafeBottomRatio}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'flex-start',
            paddingTop: titleTop,
            zIndex: 10,
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              fontSize: 80,
              fontWeight: 900,
              fontFamily: '"Microsoft YaHei", sans-serif',
              color: '#f0f6fc',
              marginBottom: 36,
              opacity: pulse,
              textAlign: 'center',
              lineHeight: 1.12,
              wordBreak: 'keep-all',
            }}
          >
            {heading}
          </div>
          <div style={{
            position: 'relative', padding: '22px 56px', borderRadius: 12,
            background: 'linear-gradient(135deg, #238636, #2ea043)',
            fontSize: 36, fontWeight: 800, color: '#fff',
            transform: `scale(${pulseScale})`,
            boxShadow: `0 0 0 ${ring * 8}px #3fb95044`,
          }}>
            {ctaText}
          </div>
        </div>
        {!suppressBottomCaption ? (
          <SlideCaptionLayer
            sentences={sentences}
            captionMode={captionMode}
            captionPlatform={captionPlatform}
            motionProfile={motionProfile}
            motionParams={motionParams}
            captionStyle={captionStyle}
            accentColor={accentColor}
          />
        ) : null}
      </MotionSlideShell>
    );
  }

  // 标题入场 (同步音频时轨)
  const titleSpring = spring({
    frame: Math.max(0, frame - headingStartFrame),
    fps,
    config: {damping: 10, stiffness: 100, mass: 0.8},
  });
  const titleScale = interpolate(titleSpring, [0, 1], [0.5, 1]);
  const titleOpacity = interpolate(titleSpring, [0, 0.3], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 打字机效果：heading 逐字出现
  const headingChars = heading.split('');
  const charsToShow = Math.min(
    headingChars.length,
    Math.floor(frame / 2),  // 每 2 帧一个字
  );

  // 光标闪烁
  const cursorVisible = frame % 30 < 15 && charsToShow < headingChars.length;

  // CTA 按钮入场
  const ctaSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: {damping: 12, stiffness: 150, mass: 0.5},
  });
  const ctaOpacity = interpolate(ctaSpring, [0, 0.4], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 呼吸光圈效果（循环）
  const ringCycle = frame % 90;
  const ringScale = interpolate(ringCycle, [0, 90], [1, 1.5]);
  const ringOpacity = interpolate(ringCycle, [0, 90], [0.6, 0]);

  // 渐变流动（background-position 偏移）
  const gradientShift = interpolate(frame, [0, 120], [0, 200]);

  // 箭头动画（循环上移并淡出）
  const arrowCycle = frame % 45;
  const arrowY = interpolate(arrowCycle, [0, 45], [0, -30]);
  const arrowOpacity = interpolate(arrowCycle, [0, 15, 45], [0, 0.8, 0]);

  // 当前字幕
  let captionText = '';
  if (sentences.length > 0) {
    for (const s of sentences) {
      if (currentTime >= s.start && currentTime < s.end) {
        captionText = s.text;
        break;
      }
    }
  }

  return (
    <div style={{position: 'absolute', top: 0, left: 0, width, height}}>
      <SlideBackground 
        colors={colors} 
        imagePath={imagePath} 
        accentColor={accentColor}
        accentColor2={accentColor2}
        cameraPan={cameraPan}
        particleType={particleType}
        decorationStyle={decorationStyle}
        colorMood={colorMood}
        backgroundVariant={backgroundVariant}
        useWeb3Background={useWeb3Background}
        overlayOpacity={overlayOpacity}
      />

      {/* 主内容居中 */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 80px',
      }}>
        {/* 标题（打字机效果） */}
        {heading && (
          <div style={{
            transform: `scale(${titleScale})`,
            opacity: titleOpacity,
            fontSize: 64,
            fontWeight: 900,
            color: textColor,
            textAlign: 'center',
            marginBottom: 60,
            fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
            textShadow: '0 4px 20px rgba(0,0,0,0.5)',
          }}>
            {headingChars.slice(0, charsToShow).join('')}
            {cursorVisible && (
              <span style={{
                color: accentColor,
                fontWeight: 300,
                marginLeft: 2,
              }}>|</span>
            )}
          </div>
        )}

        {/* CTA 按钮容器 */}
        {ctaText && (
          <div style={{
            opacity: ctaOpacity,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}>
            {/* 按钮 + 光圈的相对定位容器 */}
            <div style={{position: 'relative', display: 'inline-flex'}}>
              {/* 呼吸光圈 */}
              <div style={{
                position: 'absolute',
                top: 0, left: 0, right: 0, bottom: 0,
                borderRadius: 60,
                border: `2px solid ${accentColor}`,
                transform: `scale(${ringScale})`,
                opacity: ringOpacity,
                pointerEvents: 'none',
              }} />

              {/* 按钮本体（渐变流动） */}
              <div style={{
                background: `linear-gradient(135deg, ${accentColor} 0%, ${colors[0]} 50%, ${accentColor} 100%)`,
                backgroundSize: '200% 200%',
                backgroundPosition: `${gradientShift}% 50%`,
                padding: '28px 80px',
                borderRadius: 60,
                boxShadow: `0 0 30px ${accentColor}40, 0 8px 30px rgba(0,0,0,0.3)`,
              }}>
                <div style={{
                  fontSize: 48,
                  fontWeight: 800,
                  color: textColor,
                  fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
                  letterSpacing: 4,
                }}>
                  {ctaText}
                </div>
              </div>
            </div>

            {/* 按钮倒影 */}
            <div style={{
              marginTop: 4,
              background: `linear-gradient(135deg, ${accentColor} 0%, ${colors[0]} 50%, ${accentColor} 100%)`,
              backgroundSize: '200% 200%',
              backgroundPosition: `${gradientShift}% 50%`,
              padding: '28px 80px',
              borderRadius: 60,
              transform: 'scaleY(-1)',
              // 倒影渐变透明遮罩
              WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.25), transparent 70%)',
              maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.25), transparent 70%)',
              opacity: 0.3,
              pointerEvents: 'none',
            }}>
              <div style={{
                fontSize: 48,
                fontWeight: 800,
                color: textColor,
                fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
                letterSpacing: 4,
                visibility: 'hidden',
              }}>
                {ctaText}
              </div>
            </div>
          </div>
        )}

        {/* 向上箭头动画 */}
        <div style={{
          marginTop: 50,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 4,
        }}>
          {[0, 1, 2].map((idx) => {
            const offsetFrame = (frame + idx * 15) % 45;
            const aY = interpolate(offsetFrame, [0, 45], [0, -30]);
            const aO = interpolate(offsetFrame, [0, 15, 45], [0, 0.8, 0]);
            return (
              <div
                key={idx}
                style={{
                  transform: `translateY(${aY}px)`,
                  opacity: aO,
                  fontSize: 28,
                  color: accentColor,
                  fontWeight: 300,
                }}
              >
                ▲
              </div>
            );
          })}
        </div>
      </div>

      {/* 底部字幕 */}
      {captionText && (
        <div style={{
          position: 'absolute',
          bottom: 60,
          left: 0, right: 0,
          textAlign: 'center',
          padding: '0 60px',
        }}>
          <div style={{
            fontSize: 44,
            fontWeight: 700,
            color: textColor,
            textShadow: '0 2px 10px rgba(0,0,0,0.8)',
            fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          }}>
            {captionText}
          </div>
        </div>
      )}
    </div>
  );
};
