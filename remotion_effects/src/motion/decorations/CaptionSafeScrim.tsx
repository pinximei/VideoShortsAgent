import React from 'react';
import {useVideoConfig} from 'remotion';
import {getLayoutZones} from '../layout/safeZones';

interface Props {
  captionPlatform?: string;
  captionBottomPx?: number;
  midSafeBottomRatio?: number;
}

/** 底栏渐变遮罩：保证口播字幕与下方中屏字分离可读 */
export const CaptionSafeScrim: React.FC<Props> = ({
  captionPlatform = '',
  captionBottomPx,
  midSafeBottomRatio,
}) => {
  const {height, width} = useVideoConfig();
  const zones = getLayoutZones(captionPlatform, height, {
    captionBottomPx,
    midSafeBottomRatio,
  });
  const zoneH = Math.round(height * zones.captionScrimHeightRatio);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        height: zoneH,
        width,
        background:
          'linear-gradient(to top, rgba(8,6,12,0.88) 0%, rgba(8,6,12,0.45) 42%, transparent 100%)',
        pointerEvents: 'none',
        zIndex: 18,
      }}
    />
  );
};
