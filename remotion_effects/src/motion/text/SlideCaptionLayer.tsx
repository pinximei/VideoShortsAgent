import React from 'react';
import {CaptionOverlay} from '../../compositions/CaptionOverlay';
import {TikTokActiveCaption} from './TikTokActiveCaption';
import {XhsEditorialCaption} from './XhsEditorialCaption';
import type {MotionParams} from '../types';

interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface CaptionPageProp {
  text: string;
  startMs: number;
  durationMs: number;
  tokens: Array<{text: string; fromMs: number; toMs: number}>;
}

interface Props {
  sentences: Sentence[];
  captionPages?: CaptionPageProp[];
  captionMode?: string;
  captionPlatform?: string;
  motionProfile?: string;
  motionParams?: MotionParams;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  accentColor?: string;
  colorMood?: string;
  midScreenKinetic?: boolean;
  textColor?: string;
}

/** 抖音：中屏动效字 + 底栏 TikTok；小红书：居中 fade 字幕 */
export const SlideCaptionLayer: React.FC<Props> = ({
  sentences,
  captionPages,
  captionMode = '',
  captionPlatform = '',
  motionProfile = '',
  motionParams = {},
  captionStyle = 'spring',
  accentColor = '#FF9F43',
  colorMood = '',
  midScreenKinetic = false,
  textColor = '#FFFFFF',
}) => {
  if (!sentences.length) {
    return null;
  }
  const plat = (captionPlatform || '').toLowerCase();
  const isDouyin =
    plat === 'douyin' ||
    captionMode === 'tiktok' ||
    String(motionProfile).includes('tiktok');
  const isXhs = plat === 'xhs';
  const useEditorialCaption = isXhs && captionMode === 'editorial';

  const wordList = sentences.map((s) => ({
    text: isDouyin || useEditorialCaption ? s.text.trim() : `${s.text.trim()} `,
    start: s.start,
    end: s.end,
  }));

  return (
    <>
      {useEditorialCaption ? (
        <XhsEditorialCaption
          words={wordList}
          captionPages={captionPages}
          accentColor={accentColor}
          textColor={textColor}
          fontScale={motionParams.captionFontScale ?? 0.72}
          bottomPx={motionParams.captionBottomPx ?? 200}
          letterSpacing={motionParams.captionLetterSpacing ?? 2}
          lineHeight={motionParams.captionLineHeight ?? 1.42}
        />
      ) : isDouyin || captionMode === 'tiktok' || captionMode === 'semantic' ? (
        <TikTokActiveCaption
          words={wordList}
          captionPages={captionPages}
          profile={motionProfile}
          wordsPerPageMs={motionParams.wordsPerPageMs ?? 2400}
          maxCharsPerPage={motionParams.maxCharsPerPage ?? 24}
          accentColor={accentColor}
          letterSpacing={motionParams.captionLetterSpacing ?? 0}
          lineHeight={motionParams.captionLineHeight ?? 1.06}
          bottomPx={motionParams.captionBottomPx ?? 300}
          midSafeBottomRatio={motionParams.midSafeBottomRatio ?? 0.36}
          captionPlatform={captionPlatform}
        />
      ) : (
        <div style={{position: 'absolute', inset: 0, zIndex: 100, pointerEvents: 'none'}}>
          <CaptionOverlay
            sentences={sentences}
            style={captionStyle}
            accentColor={accentColor}
            textColor={textColor}
          />
        </div>
      )}
    </>
  );
};
