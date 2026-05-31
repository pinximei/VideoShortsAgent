export type MotionProfileId =
  | 'github_daily_hook'
  | 'github_daily_bullets'
  | 'tiktok_word_pop'
  | 'kinetic_slam_tight'
  | 'kinetic_slam_loose'
  | 'typewriter_terminal'
  | 'episode_counter'
  | 'glitch_hook_clean'
  | 'bullet_rail_right'
  | 'bullet_stagger_up'
  | 'minimal_headline'
  | 'cta_pulse_arrow'
  | 'mono_code_rain'
  | 'flash_hook_smash'
  | 'split_mask_reveal'
  | 'glass_card_stack'
  | 'marquee_ticker'
  | 'shake_emphasis'
  | 'product_split_frame'
  | 'tiktok_phrase_pages';

export interface MotionParams {
  staggerFrames?: number;
  springDamping?: number;
  springStiffness?: number;
  wordsPerPageMs?: number;
  glitchFrames?: number;
}

export interface MotionTheme {
  bg: string;
  fg: string;
  accent: string;
  accent2?: string;
}

export const THEMES: Record<string, MotionTheme> = {
  github: {bg: '#0d1117', fg: '#f0f6fc', accent: '#58a6ff', accent2: '#3fb950'},
  tiktok: {bg: '#000000', fg: '#ffffff', accent: '#39E508', accent2: '#39E508'},
  kinetic: {bg: '#0c0c0e', fg: '#fafafa', accent: '#ff3366', accent2: '#ffcc00'},
  terminal: {bg: '#0a0f0a', fg: '#33ff99', accent: '#33ff99', accent2: '#1a1a1a'},
  minimal: {bg: '#111111', fg: '#ffffff', accent: '#ffffff', accent2: '#666666'},
};
