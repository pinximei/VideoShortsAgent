use std::path::Path;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::ffmpeg::run_ffprobe_capture;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoProbe {
    pub duration_sec: f64,
    pub width: u32,
    pub height: u32,
}

pub fn probe_video(path: &Path) -> Result<VideoProbe> {
    let path_str = path
        .to_str()
        .context("路径含非 UTF-8 字符")?;
    let out = run_ffprobe_capture(&[
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=width,height",
        "-of",
        "json",
        "-select_streams",
        "v:0",
        "-i",
        path_str,
    ])?;
    let v: serde_json::Value =
        serde_json::from_str(&out).context("解析 ffprobe 输出失败（请确认 ffmpeg 含 ffprobe）")?;
    let duration_sec = v
        .pointer("/format/duration")
        .and_then(|x| x.as_str())
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.0);
    let width = v
        .pointer("/streams/0/width")
        .and_then(|x| x.as_u64())
        .unwrap_or(0) as u32;
    let height = v
        .pointer("/streams/0/height")
        .and_then(|x| x.as_u64())
        .unwrap_or(0) as u32;
    Ok(VideoProbe {
        duration_sec,
        width,
        height,
    })
}
