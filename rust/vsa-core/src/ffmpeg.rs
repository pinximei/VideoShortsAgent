use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use anyhow::{bail, Context, Result};

/// 查找 ffmpeg：环境变量 VSA_FFMPEG > PATH > 常见安装路径
pub fn resolve_ffprobe() -> Result<PathBuf> {
    if let Ok(p) = std::env::var("VSA_FFPROBE") {
        let path = PathBuf::from(p);
        if path.is_file() {
            return Ok(path);
        }
    }
    let ffmpeg = resolve_ffmpeg()?;
    let probe = ffmpeg.with_file_name(if cfg!(windows) {
        "ffprobe.exe"
    } else {
        "ffprobe"
    });
    if probe.is_file() {
        return Ok(probe);
    }
    if let Some(name) = which_ffprobe_name() {
        if Command::new(name).arg("-version").output().ok().is_some() {
            return Ok(PathBuf::from(name));
        }
    }
    bail!("未找到 ffprobe（通常与 ffmpeg 同目录）");
}

fn which_ffprobe_name() -> Option<&'static str> {
    if cfg!(windows) {
        Some("ffprobe.exe")
    } else {
        Some("ffprobe")
    }
}

pub fn run_ffprobe_capture(args: &[&str]) -> Result<String> {
    let ffprobe = resolve_ffprobe()?;
    let output = Command::new(&ffprobe)
        .args(args)
        .output()
        .with_context(|| format!("执行 ffprobe 失败: {:?}", ffprobe))?;
    ensure_ok(&output)?;
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

pub fn resolve_ffmpeg() -> Result<PathBuf> {
    if let Ok(p) = std::env::var("VSA_FFMPEG") {
        let path = PathBuf::from(p);
        if path.is_file() {
            return Ok(path);
        }
    }
    if let Some(name) = which_ffmpeg_name() {
        if let Ok(out) = Command::new(&name).arg("-version").output() {
            if out.status.success() {
                return Ok(PathBuf::from(name));
            }
        }
    }
    bail!(
        "未找到 FFmpeg。请安装并加入 PATH，或设置环境变量 VSA_FFMPEG 指向 ffmpeg.exe"
    );
}

fn which_ffmpeg_name() -> Option<&'static str> {
    if cfg!(windows) {
        Some("ffmpeg.exe")
    } else {
        Some("ffmpeg")
    }
}

pub fn run_ffmpeg(args: &[&str]) -> Result<()> {
    let ffmpeg = resolve_ffmpeg()?;
    let output = Command::new(&ffmpeg)
        .args(args)
        .output()
        .with_context(|| format!("执行 ffmpeg 失败: {:?}", ffmpeg))?;
    ensure_ok(&output)
}

pub fn run_ffmpeg_capture(args: &[&str]) -> Result<String> {
    let ffmpeg = resolve_ffmpeg()?;
    let output = Command::new(&ffmpeg)
        .args(args)
        .output()
        .with_context(|| format!("执行 ffmpeg 失败: {:?}", ffmpeg))?;
    ensure_ok(&output)?;
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

fn ensure_ok(output: &Output) -> Result<()> {
    if output.status.success() {
        return Ok(());
    }
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stdout = String::from_utf8_lossy(&output.stdout);
    bail!("ffmpeg 退出码 {:?}\n{}\n{}", output.status.code(), stderr, stdout);
}

pub fn escape_subtitle_path(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/").replace(':', "\\:")
}
