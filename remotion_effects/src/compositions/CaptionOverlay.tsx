import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';

/**
 * CaptionOverlay - 逐句字幕特效（透明覆盖层）（升级版）
 *
 * 特效：毛玻璃底栏、双层文字、弹入+放大动画、关键词高亮、进度条
 *
 * 支持两种输入：
 * 1. sentences 数组（精确时间轴）：按时间逐句显示
 * 2. text 字符串（兜底）：全程显示单条文字
 */
interface Sentence {
  text: string;
  start: number;  // 秒
  end: number;     // 秒
}

interface CaptionOverlayProps {
  text?: string;
  sentences?: Sentence[];
  style?: 'spring' | 'fade' | 'typewriter';
  accentColor?: string;
}

// 解析文本中的 **粗体** 标记
function parseHighlightedText(
  text: string,
  accentColor: string,
): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // 前面的普通文字
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    // 高亮词
    parts.push(
      <span key={match.index} style={{color: accentColor, fontWeight: 900}}>
        {match[1]}
      </span>
    );
    lastIndex = regex.lastIndex;
  }
  // 剩余文字
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length > 0 ? parts : [text];
}

// 清理文本（去掉 ** 标记）用于描边层
function stripBold(text: string): string {
  return text.replace(/\*\*(.+?)\*\*/g, '$1');
}

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
  text = '',
  sentences = [],
  style = 'spring',
  accentColor = '#00d2ff',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentTime = frame / fps;

  // 找到当前时间应该显示的句子
  let displayText = '';
  let sentenceProgress = 0;
  let isNewSentence = false;

  if (sentences.length > 0) {
    for (let i = 0; i < sentences.length; i++) {
      const s = sentences[i];
      if (currentTime >= s.start && currentTime < s.end) {
        displayText = s.text;
        sentenceProgress = (currentTime - s.start) / (s.end - s.start);
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
    if (frame % 30 === 0) console.log(`[DEBUG-CAPTION] Frame: ${frame} | empty displayText`);
    return <div style={{width: '100%', height: '100%', backgroundColor: 'transparent'}} />;
  }

  // 入场动画
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

  // 从底部弹入
  const textY = interpolate(springValue, [0, 1], [60, 0]);
  // 轻微放大
  const textScale = interpolate(springValue, [0, 1], [0.9, 1]);
  // 淡入
  const textOpacity = interpolate(springValue, [0, 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 底栏淡入（总体）
  const barOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 进度条宽度
  const progressWidth = sentenceProgress * 100;

  const strippedText = stripBold(displayText);

  if (frame % 30 === 0) {
    console.log(`[DEBUG-CAPTION] Frame: ${frame} | displayText: '${displayText}' | sentenceProgress: ${sentenceProgress} | textOpacity: ${textOpacity || 0}`);
  }

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
      {/* 底部毛玻璃底栏 */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 200,
          background: 'rgba(0, 0, 0, 0.4)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          opacity: barOpacity,
        }}
      >
        {/* 顶部亮线 */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 1,
          background: 'linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.3) 50%, transparent 90%)',
        }} />

        {/* 进度条 */}
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: `${progressWidth}%`,
          height: 3,
          background: `linear-gradient(90deg, ${accentColor}80, ${accentColor})`,
          boxShadow: `0 0 8px ${accentColor}60`,
          transition: 'width 0.1s linear',
        }} />
      </div>

      {/* 字幕文字区域 */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 60px',
          opacity: textOpacity,
        }}
      >
        {/* 双层文字容器 */}
        <div style={{
          position: 'relative',
          transform: `translateY(${textY}px) scale(${textScale})`,
        }}>
          {/* 底层：描边文字 */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              fontSize: 52,
              fontWeight: 800,
              color: 'transparent',
              textAlign: 'center',
              lineHeight: 1.5,
              fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
              letterSpacing: 2,
              WebkitTextStroke: '3px rgba(255,255,255,0.3)',
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            {strippedText}
          </div>

          {/* 顶层：填充文字（含高亮） */}
          <div
            style={{
              position: 'relative',
              fontSize: 52,
              fontWeight: 800,
              color: '#FFFFFF',
              textAlign: 'center',
              lineHeight: 1.5,
              textShadow: '0 2px 10px rgba(0,0,0,1), 0 0 20px rgba(0,0,0,0.8)',
              fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
              letterSpacing: 2,
              whiteSpace: 'nowrap',
            }}
          >
            {parseHighlightedText(displayText, accentColor)}
          </div>
        </div>
      </div>
    </div>
  );
};
