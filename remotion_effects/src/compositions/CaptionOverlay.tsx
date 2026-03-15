import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';

/**
 * CaptionOverlay - 逐句字幕特效（透明覆盖层）
 *
 * 支持两种输入：
 * 1. sentences 数组（精确时间轴）：按时间逐句显示
 * 2. text 字符串（兜底）：全程显示单条文字
 *
 * 背景完全透明，用于叠加到视频上。
 */
interface Sentence {
  text: string;
  start: number;  // 秒
  end: number;     // 秒
}

interface CaptionOverlayProps {
  text?: string;
  sentences?: Sentence[];
  style: 'spring' | 'fade' | 'typewriter';
}

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
  text = '',
  sentences = [],
  style = 'spring',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentTime = frame / fps;

  // 找到当前时间应该显示的句子
  let displayText = '';
  let sentenceProgress = 0; // 当前句子的进度（0~1）
  let isNewSentence = false;

  if (sentences.length > 0) {
    for (let i = 0; i < sentences.length; i++) {
      const s = sentences[i];
      if (currentTime >= s.start && currentTime < s.end) {
        displayText = s.text;
        sentenceProgress = (currentTime - s.start) / (s.end - s.start);
        // 判断是否刚进入新句子（前 0.3 秒内）
        isNewSentence = (currentTime - s.start) < 0.3;
        break;
      }
    }
  } else if (text) {
    displayText = text;
    sentenceProgress = 1;
    isNewSentence = frame < 10;
  }

  if (!displayText) {
    // 当前时间没有句子要显示，返回空透明层
    return <div style={{width: '100%', height: '100%', backgroundColor: 'transparent'}} />;
  }

  // 入场动画（每句话触发一次）
  const sentenceFrame = sentences.length > 0
    ? (() => {
        const s = sentences.find(s => currentTime >= s.start && currentTime < s.end);
        return s ? Math.round((currentTime - s.start) * fps) : frame;
      })()
    : frame;

  const springValue = spring({
    frame: sentenceFrame,
    fps,
    config: {damping: 14, stiffness: 150, mass: 0.6},
  });

  // 文字位移（从底部弹入）
  const textY = interpolate(springValue, [0, 1], [80, 0]);

  // 文字透明度（淡入）
  const textOpacity = interpolate(springValue, [0, 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 底栏高度
  const barHeight = interpolate(springValue, [0, 1], [0, 180]);

  // 发光脉冲
  const glowIntensity = interpolate(
    frame % 60,
    [0, 30, 60],
    [2, 5, 2],
    {extrapolateRight: 'clamp'}
  );

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'transparent',
      }}
    >
      {/* 底部字幕区域 */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          opacity: textOpacity,
        }}
      >
        {/* 字幕文字区域（无渐变背景，纯透明） */}
        <div
          style={{
            height: 180,
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center',
            padding: '0 60px 50px',
          }}
        >
          {/* 字幕文字 */}
          <div
            style={{
              transform: `translateY(${textY}px)`,
              fontSize: 52,
              fontWeight: 800,
              color: '#FFFFFF',
              textAlign: 'center',
              lineHeight: 1.5,
              textShadow: `0 0 ${glowIntensity}px rgba(255,215,0,0.6), 0 2px 10px rgba(0,0,0,1), 0 0 20px rgba(0,0,0,0.8)`,
              fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
              letterSpacing: 2,
              WebkitTextStroke: '1px rgba(0,0,0,0.5)',
            }}
          >
            {displayText}
          </div>
        </div>
      </div>
    </div>
  );
};
