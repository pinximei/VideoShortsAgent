import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';
import {CaptionOverlay} from './CaptionOverlay';

interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface ContentCardProps {
  heading?: string;
  bullets?: string[];
  hookText?: string;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  colors?: string[];
  textColor?: string;
  accentColor?: string;
  imagePath?: string;
  sentences?: Sentence[];
  cameraPan?: string;
  particleType?: string;
  decorationStyle?: string;
  textEffect?: 'glitch' | 'neon' | 'cinematic' | 'classic';
  layoutStyle?: 'center' | 'split-left' | 'split-right' | 'top-heavy';
  colorMood?: string;
  headingStartFrame?: number;
  bulletStartFrames?: number[];
}

export const ContentCard: React.FC<ContentCardProps> = ({
  heading = '',
  bullets = [],
  hookText = '',
  captionStyle = 'spring',
  colors = ['#0f0c29', '#302b63'],
  textColor = '#ffffff',
  accentColor = '#00d2ff',
  imagePath,
  sentences = [],
  cameraPan = 'zoom-in',
  particleType = 'glow',
  decorationStyle = 'none',
  textEffect = 'classic',
  layoutStyle = 'center',
  colorMood = '',
  headingStartFrame = 0,
  bulletStartFrames = [],
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const currentTime = frame / fps;

  // Heading Entry
  const headingSpring = spring({
    frame: Math.max(0, frame - headingStartFrame),
    fps, config: {damping: 14, stiffness: 130, mass: 0.7},
  });
  const headingOpacity = interpolate(headingSpring, [0, 0.4], [0, 1], { extrapolateRight: 'clamp' });
  const headingX = interpolate(headingSpring, [0, 1], [-60, 0]);
  const barPulse = interpolate(frame % 90, [0, 45, 90], [0.6, 1, 0.6]);

  // Decor
  const decorRotate = interpolate(frame, [0, 600], [0, 45]);
  const decorOpacity = interpolate(frame, [0, 20], [0, 0.15], { extrapolateRight: 'clamp' });

  // Layout Styles Logic
  let wrapperStyle: React.CSSProperties = {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    display: 'flex', flexDirection: 'column', padding: '0 80px',
  };
  // captionStyleObj is no longer needed as CaptionOverlay handles its own positioning
  // let captionStyleObj: React.CSSProperties = {
  //   position: 'absolute', left: 0, right: 0, textAlign: 'center', padding: '0 60px', zIndex: 100
  // };

  switch(layoutStyle) {
    case 'split-left':
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'flex-start';
      break;
    case 'split-right':
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'flex-end';
      break;
    case 'top-heavy':
      wrapperStyle.justifyContent = 'flex-start';
      wrapperStyle.alignItems = 'center';
      wrapperStyle.paddingTop = '250px';
      break;
    case 'center':
    default:
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'center';
      break;
  }

  return (
    <div style={{position: 'absolute', top: 0, left: 0, width, height}}>
      <SlideBackground 
        colors={colors} 
        imagePath={imagePath} 
        accentColor={accentColor}
        cameraPan={cameraPan}
        particleType={particleType}
        decorationStyle={decorationStyle}
        colorMood={colorMood}
      />

      {/* Top Right Decor */}
      <div style={{
        position: 'absolute', top: -40, right: -40, width: 200, height: 200,
        borderRadius: '0 0 0 100%', background: `linear-gradient(135deg, ${accentColor}40, transparent)`,
        opacity: decorOpacity, transform: `rotate(${decorRotate}deg)`, pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', top: 30, right: 30, width: 100, height: 100,
        border: `2px solid ${accentColor}30`, borderRadius: '50%',
        opacity: decorOpacity, transform: `rotate(${-decorRotate}deg)`, pointerEvents: 'none',
      }} />

      {/* Main Content Area */}
      <div style={wrapperStyle}>
        {/* Title rendering engine */}
        {textEffect === 'glitch' && (
          <div style={{
            transform: `translateX(${headingX}px)`, opacity: headingOpacity,
            display: 'flex', alignItems: 'center', marginBottom: 50,
          }}>
            <div style={{
              fontSize: 64, fontWeight: 900, textTransform: 'uppercase', color: '#fff',
              fontFamily: '"Impact", "Microsoft YaHei", sans-serif', letterSpacing: 4,
              textShadow: ((frame - headingStartFrame) > 10 && (frame - headingStartFrame) < 25 && frame % 3 === 0) 
                 ? `4px 0px 0px rgba(255,0,0,0.8), -4px 0px 0px rgba(0,255,255,0.8)` 
                 : `1px 0px 0px rgba(255,0,0,0.8), -1px 0px 0px rgba(0,255,255,0.8)`,
              transform: ((frame - headingStartFrame) > 10 && (frame - headingStartFrame) < 25 && frame % 3 === 0) 
                 ? `translateX(${Math.random() * 6 - 3}px)` : 'none',
            }}>
              {heading}
            </div>
          </div>
        )}
        
        {textEffect === 'neon' && (
          <div style={{
            transform: `translateX(${headingX}px)`, opacity: headingOpacity * (((frame - headingStartFrame) > 5 && (frame - headingStartFrame) < 15) && (frame % 2 !== 0) ? 0.3 : 1),
            display: 'flex', alignItems: 'center', marginBottom: 50,
          }}>
            <div style={{
              fontSize: 68, fontWeight: 900, color: '#fff',
              fontFamily: '"Arial Rounded MT Bold", "Microsoft YaHei", sans-serif',
              textShadow: `0 0 10px #fff, 0 0 20px #fff, 0 0 40px ${accentColor}`,
            }}>
              {heading.split('').map((char, i) => (
                <span key={i} style={{ opacity: Math.random() > 0.9 && frame > 20 ? 0.5 : 1 }}>{char}</span>
              ))}
            </div>
          </div>
        )}

        {textEffect === 'cinematic' && (
          <div style={{
            transform: `translateX(${headingX}px)`, opacity: headingOpacity,
            display: 'flex', alignItems: 'center', marginBottom: 50,
          }}>
            <div style={{
              position: 'relative', fontSize: 62, fontWeight: 300, color: textColor,
              fontFamily: '"Times New Roman", "Songti SC", serif',
              letterSpacing: interpolate(Math.max(0, frame - headingStartFrame), [0, 150], [2, 12]),
              textShadow: '0 4px 20px rgba(0,0,0,0.8)'
            }}>
              {heading}
            </div>
          </div>
        )}

        {textEffect === 'classic' && (
          <div style={{
            transform: `translateX(${headingX}px)`, opacity: headingOpacity,
            display: 'flex', alignItems: 'center', marginBottom: 50,
          }}>
            <div style={{
              width: 6, height: 60, background: `linear-gradient(180deg, ${accentColor}, ${accentColor}40)`,
              borderRadius: 3, marginRight: 24, flexShrink: 0,
              boxShadow: `0 0 ${12 * barPulse}px ${accentColor}60, ${4 * barPulse}px 0 ${20 * barPulse}px ${accentColor}20`,
            }} />
            <div style={{
              fontSize: 56, fontWeight: 800, color: accentColor,
              fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif', textShadow: '0 2px 10px rgba(0,0,0,0.5)',
            }}>
              {heading}
            </div>
          </div>
        )}

        {/* Bullets */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: wrapperStyle.alignItems }}>
          {bullets.map((bullet, i) => {
            const startF = (bulletStartFrames && bulletStartFrames.length > i) ? bulletStartFrames[i] : (headingStartFrame + 15 + i * 15);
            const bulletSpring = spring({ frame: Math.max(0, frame - startF), fps, config: {damping: 16, stiffness: 120, mass: 0.5} });
            const bulletOpacity = interpolate(bulletSpring, [0, 0.4], [0, 1], { extrapolateRight: 'clamp' });
            
            // direction from which the bullet enters depend on layout
            const rawTrans = interpolate(bulletSpring, [0, 1], layoutStyle === 'split-right' ? [80, 0] : [-80, 0]);
            const bulletX = layoutStyle === 'center' ? 0 : rawTrans;
            const bulletY = layoutStyle === 'center' ? interpolate(bulletSpring, [0, 1], [40, 0]) : 0;

            const numberStr = String(i + 1).padStart(2, '0');

            return (
              <div key={i} style={{
                  transform: `translate(${bulletX}px, ${bulletY}px)`, opacity: bulletOpacity, marginBottom: 20,
                  background: 'rgba(255, 255, 255, 0.08)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
                  borderRadius: 16, padding: '20px 28px', border: '1px solid rgba(255, 255, 255, 0.1)',
                  display: 'flex', alignItems: 'center', gap: 20, maxWidth: layoutStyle === 'center' ? '900px' : '750px',
                  justifyContent: 'flex-start'
                }}
              >
                <div style={{
                  width: 44, height: 44, borderRadius: '50%', background: `linear-gradient(135deg, ${accentColor}, ${accentColor}80)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  boxShadow: `0 2px 10px ${accentColor}40`,
                }}>
                  <span style={{ fontSize: 18, fontWeight: 800, color: '#ffffff', fontFamily: '"Microsoft YaHei", sans-serif' }}>
                    {numberStr}
                  </span>
                </div>
                <span style={{
                  fontSize: 38, fontWeight: 500, color: textColor, fontFamily: '"Microsoft YaHei", sans-serif',
                  textShadow: '0 2px 8px rgba(0,0,0,0.4)', lineHeight: 1.4, textAlign: 'left'
                }}>
                  {bullet}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* TTS Caption (Universal Overlay) */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 100, pointerEvents: 'none' }}>
        <CaptionOverlay sentences={sentences} style={captionStyle} accentColor={accentColor} />
      </div>
    </div>
  );
};
