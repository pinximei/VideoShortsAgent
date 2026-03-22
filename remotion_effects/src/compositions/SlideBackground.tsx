import React, {useMemo} from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Video,
  staticFile,
} from 'remotion';

/**
 * SlideBackground - 通用幻灯片背景（终极版）
 */
interface SlideBackgroundProps {
  colors: string[];
  imagePath?: string;
  overlayOpacity?: number;
  accentColor?: string;
  cameraPan?: string;
  particleType?: string;
  decorationStyle?: string;
  colorMood?: string;
}

function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
  phase: number;
  type: 'dot' | 'ring' | 'glow' | 'matrix' | 'starfield' | 'bokeh';
}

function generateParticles(count: number, forceType: string): Particle[] {
  if (!forceType || forceType === 'none') return [];
  const particles: Particle[] = [];
  const validTypes = ['dot', 'ring', 'glow', 'matrix', 'starfield', 'bokeh'];
  
  for (let i = 0; i < count; i++) {
    const t = forceType && validTypes.includes(forceType) ? forceType as any : 'glow';
    particles.push({
      x: seededRandom(i * 7 + 1) * 100,
      y: seededRandom(i * 7 + 2) * 100,
      size: (t === 'glow' || t === 'bokeh') ? 20 + seededRandom(i * 7 + 3) * 60 : 
            (t === 'starfield') ? 1 + seededRandom(i * 7 + 3) * 3 :
            3 + seededRandom(i * 7 + 3) * 10,
      speedX: (t === 'matrix') ? 0 : (t === 'starfield') ? (seededRandom(i*7+4)-0.5)*2 : (seededRandom(i * 7 + 4) - 0.5) * 0.6,
      speedY: (t === 'matrix') ? 0.5 + seededRandom(i*7+5) * 2 : (t === 'starfield') ? 0.5 + seededRandom(i*7+5)*2 : (seededRandom(i * 7 + 5) - 0.5) * 0.4,
      opacity: (t === 'glow' || t === 'bokeh') ? 0.04 + seededRandom(i * 7 + 6) * 0.1 : 
               (t === 'starfield') ? 0.5 + seededRandom(i*7+6)*0.5 :
               0.08 + seededRandom(i * 7 + 6) * 0.15,
      phase: seededRandom(i * 7 + 7) * Math.PI * 2,
      type: t,
    });
  }
  return particles;
}

const MOOD_PALETTES: Record<string, string[]> = {
  'neon-cyber': ['#09090e', '#302b63', '#ff00ff'],
  'minimal-dark': ['#111111', '#222222'],
  'warm-sunrise': ['#3a1c22', '#6a2a22', '#b3472b'],
  'deep-ocean': ['#00091a', '#002540'],
  'cyberpunk': ['#1a0b2e', '#2c1b4d', '#00e5ff'],
};

export const SlideBackground: React.FC<SlideBackgroundProps> = ({
  colors = ['#0a0a0f', '#1a1a2e'],
  imagePath,
  overlayOpacity = 0.25,
  accentColor = '#00e5c8',
  cameraPan = 'zoom-in',
  particleType = 'glow',
  decorationStyle = 'none',
  colorMood = '',
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  const activeColors = MOOD_PALETTES[colorMood.toLowerCase()] || colors;
  const pCount = (particleType === 'starfield') ? 80 : (particleType === 'matrix') ? 40 : 15;
  const particles = useMemo(() => generateParticles(pCount, particleType), [particleType, pCount]);

  const angle = interpolate(frame, [0, 1800], [135, 495]);
  const breathe = interpolate(frame % 150, [0, 75, 150], [0.85, 1, 0.85]);

  let scale = 1; let tx = 0; let ty = 0; let rotate = 0;
  
  // 核心修复: 如果背景是原生视频(.mp4)，禁用极小粒度的平移和缩放！
  // Chromium 的 `<video>` 硬件解码与 useCurrentFrame() 小数级 CSS transform 叠加会引发严重的丢帧与来回抖动(Jitter/Bouncing)。
  const isVideo = imagePath?.toLowerCase().endsWith('.mp4');
  if (!isVideo) {
    if (cameraPan === 'zoom-in') scale = 1 + frame * 0.0006;
    else if (cameraPan === 'zoom-out') scale = 1.1 - frame * 0.0006;
    else if (cameraPan === 'pan-left') { scale = 1.1; tx = interpolate(frame, [0, 600], [5, -5]); }
    else if (cameraPan === 'pan-right') { scale = 1.1; tx = interpolate(frame, [0, 600], [-5, 5]); }
    else if (cameraPan === 'pan-up') { scale = 1.1; ty = interpolate(frame, [0, 600], [5, -5]); }
    else if (cameraPan === 'pan-down') { scale = 1.1; ty = interpolate(frame, [0, 600], [-5, 5]); }
    else if (cameraPan === 'rotate-clock') { scale = 1.1; rotate = frame * 0.02; }
  }

  const gradientColors = activeColors.length >= 2 ? activeColors.join(', ') : `${activeColors[0]}, ${activeColors[0]}`;

  return (
    <div style={{ position: 'absolute', top: 0, left: 0, width, height, overflow: 'hidden', backgroundColor: '#000' }}>
      
      {/* Background Media */}
      {imagePath && imagePath.toLowerCase().endsWith('.mp4') ? (
        <Video src={staticFile(imagePath.replace(/^\//, ''))}
          muted loop
          style={{
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover',
            transform: `scale(${Math.max(1, scale)}) translate(${tx}%, ${ty}%) rotate(${rotate}deg)`,
          }}
        />
      ) : imagePath && (
        <Img src={staticFile(imagePath.replace(/^\//, ''))}
          style={{
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover',
            transform: `scale(${Math.max(1, scale)}) translate(${tx}%, ${ty}%) rotate(${rotate}deg)`,
          }}
        />
      )}

      {/* Primary Gradients */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
        background: `linear-gradient(${angle}deg, ${gradientColors})`, opacity: imagePath ? overlayOpacity : breathe,
      }} />

      {/* Decorations Layer */}
      {decorationStyle === 'cyber-grid' && (
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
          backgroundImage: `linear-gradient(${accentColor}1A 1px, transparent 1px), linear-gradient(90deg, ${accentColor}1A 1px, transparent 1px)`,
          backgroundSize: '40px 40px', backgroundPosition: 'center center', transform: `perspective(500px) rotateX(60deg) translateY(${frame % 40}px) scale(3)`, pointerEvents: 'none'
        }} />
      )}

      {decorationStyle === 'film-grain' && (
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', mixBlendMode: 'overlay', opacity: 0.1, pointerEvents: 'none',
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='1.2' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`
        }} />
      )}

      {/* Particles Layer */}
      {particles.map((p, i) => {
        let px = p.x; let py = p.y;
        if (p.type === 'matrix') {
          // Fall down matrix style
          py = (p.y + frame * p.speedY) % 110 - 10;
        } else if (p.type === 'starfield') {
          // Zoom out from center
          const dx = p.x - 50; const dy = p.y - 50;
          px = 50 + dx * (1 + (frame * 0.05 * p.speedY));
          py = 50 + dy * (1 + (frame * 0.05 * p.speedY));
          if (px < -10 || px > 110 || py < -10 || py > 110) {
             // Let it off screen for now, simplifying math
          }
        } else {
          px = p.x + Math.sin(frame * 0.008 * p.speedX + p.phase) * 10;
          py = p.y + Math.cos(frame * 0.006 * p.speedY + p.phase) * 8;
        }

        const pOpac = p.opacity * (0.6 + 0.4 * Math.sin(frame * 0.015 + p.phase));

        if (p.type === 'ring') return <div key={i} style={{ position: 'absolute', left: `${px}%`, top: `${py}%`, width: p.size * 2, height: p.size * 2, borderRadius: '50%', border: `1px solid ${accentColor}`, opacity: pOpac * 0.6, filter: `blur(1px)` }} />
        if (p.type === 'glow' || p.type === 'bokeh') return <div key={i} style={{ position: 'absolute', left: `${px}%`, top: `${py}%`, width: p.size, height: p.size, borderRadius: '50%', background: `radial-gradient(circle, ${p.type==='bokeh'? '#ffffff': accentColor}30, transparent 70%)`, opacity: pOpac, filter: `blur(${p.size * (p.type==='bokeh'? 0.1:0.3)}px)` }} />
        if (p.type === 'matrix') return <div key={i} style={{ position: 'absolute', left: `${px}%`, top: `${py}%`, fontSize: p.size, color: accentColor, opacity: pOpac, fontFamily: 'monospace', textShadow: `0 0 5px ${accentColor}` }}>{Math.random()>0.5?'0':'1'}</div>
        
        // dot or starfield
        return <div key={i} style={{ position: 'absolute', left: `${px}%`, top: `${py}%`, width: p.size, height: p.size, borderRadius: '50%', background: p.type === 'starfield' ? '#fff' : accentColor, opacity: pOpac, filter: `blur(${p.size * 0.2}px)`, boxShadow: p.type === 'starfield' ? `0 0 5px #fff` : `0 0 ${p.size * 1.2}px ${accentColor}40` }} />
      })}

      {/* Cinematic Bars Layer */}
      {decorationStyle === 'cinematic-bars' && (
        <>
          <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '10%', backgroundColor: '#000', zIndex: 9999 }} />
          <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '10%', backgroundColor: '#000', zIndex: 9999 }} />
        </>
      )}

      {/* Corner Glow Layer */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '40%', background: `linear-gradient(to top, ${(colors[colors.length-1]||colors[0])}40, transparent)`, pointerEvents: 'none' }} />
    </div>
  );
};
