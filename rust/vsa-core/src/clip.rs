use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

use crate::ffmpeg::run_ffmpeg;
use crate::segments::Segment;

pub fn clip_and_concat(input: &Path, segments: &[Segment], output: &Path) -> Result<()> {
    let parent = output
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)?;
    let work = parent.join(format!(
        ".vsa_work_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis()
    ));
    fs::create_dir_all(&work)?;
    let mut parts: Vec<PathBuf> = Vec::new();
    for (i, seg) in segments.iter().enumerate() {
        let part = work.join(format!("part_{i:03}.mp4"));
        run_ffmpeg(&[
            "-y",
            "-ss",
            &format!("{:.3}", seg.start),
            "-to",
            &format!("{:.3}", seg.end),
            "-i",
            input.to_str().unwrap(),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            part.to_str().unwrap(),
        ])?;
        parts.push(part);
    }
    if parts.len() == 1 {
        fs::copy(&parts[0], output).context("复制输出失败")?;
    } else {
        concat_parts(&parts, output)?;
    }
    let _ = fs::remove_dir_all(&work);
    Ok(())
}

fn concat_parts(parts: &[PathBuf], output: &Path) -> Result<()> {
    let list_path = output.with_extension("concat.txt");
    let mut list = String::new();
    for p in parts {
        let esc = p.to_string_lossy().replace('\'', "'\\''");
        list.push_str(&format!("file '{esc}'\n"));
    }
    fs::write(&list_path, list)?;
    run_ffmpeg(&[
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path.to_str().unwrap(),
        "-c",
        "copy",
        output.to_str().unwrap(),
    ])?;
    let _ = fs::remove_file(&list_path);
    Ok(())
}

pub fn vertical_9_16(input: &Path, output: &Path) -> Result<()> {
    run_ffmpeg(&[
        "-y",
        "-i",
        input.to_str().unwrap(),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:a",
        "copy",
        output.to_str().unwrap(),
    ])
}
