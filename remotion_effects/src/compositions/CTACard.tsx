import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';

/**
 * CTACard - 行动号召卡组件
 *
 * 大号 CTA 文字 + 脉冲按钮效果 + 渐变背景。
 * 用于视频结尾的行动引导。
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
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const currentTime = frame / fps;

  // 标题入场
  const titleSpring = spring({
    frame,
    fps,
    config: {damping: 10, stiffness: 100, mass: 0.8},
  });
  const titleScale = interpolate(titleSpring, [0, 1], [0.5, 1]);
  const titleOpacity = interpolate(titleSpring, [0, 0.3], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // CTA 按钮脉冲动画
  const pulse = interpolate(
    frame % 60,
    [0, 15, 30, 60],
    [1, 1.08, 1, 1],
  );
  const ctaSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: {damping: 12, stiffness: 150, mass: 0.5},
  });
  const ctaOpacity = interpolate(ctaSpring, [0, 0.4], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 底部发光效果
  const glowSize = interpolate(
    frame % 90,
    [0, 45, 90],
    [20, 40, 20],
  );

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
      <SlideBackground colors={colors} imagePath={imagePath} />

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
        {/* 标题 */}
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
            {heading}
          </div>
        )}

        {/* CTA 按钮 */}
        {ctaText && (
          <div style={{
            transform: `scale(${pulse})`,
            opacity: ctaOpacity,
            background: `linear-gradient(135deg, ${accentColor}, ${colors[0]})`,
            padding: '28px 80px',
            borderRadius: 60,
            boxShadow: `0 0 ${glowSize}px ${accentColor}80, 0 8px 30px rgba(0,0,0,0.3)`,
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
        )}
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
