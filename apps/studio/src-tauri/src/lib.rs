use std::path::{Path, PathBuf};

use serde::Serialize;
use vsa_core::{clip_and_concat, parse_segments, probe_video, vertical_9_16};

#[derive(Serialize)]
pub struct ExportResult {
    pub output_path: String,
    pub message: String,
}

#[derive(Serialize)]
pub struct LicenseStatus {
    pub edition: String,
    pub message: String,
}

#[tauri::command]
fn probe_video_cmd(path: String) -> Result<serde_json::Value, String> {
    let p = probe_video(Path::new(&path)).map_err(|e| e.to_string())?;
    serde_json::to_value(p).map_err(|e| e.to_string())
}

#[tauri::command]
fn export_clip(
    video_path: String,
    segments_text: String,
    vertical: bool,
    mode: String,
) -> Result<ExportResult, String> {
    let input = PathBuf::from(&video_path);
    if !input.is_file() {
        return Err(format!("找不到视频文件: {video_path}"));
    }

    let segments = parse_segments(&segments_text).map_err(|e| e.to_string())?;

    if mode == "douyin" {
        let total: f64 = segments.iter().map(|s| s.end - s.start).sum();
        if total > 60.0 {
            return Err(format!(
                "抖音模式总时长 {total:.1}s 超过 60 秒上限，请缩短或分段导出"
            ));
        }
    }

    let stem = input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("output");
    let parent = output_parent_dir();
    let tag = match mode.as_str() {
        "douyin" => "douyin",
        "ecommerce" => "ecom",
        _ => "clip",
    };
    let raw = parent.join(format!("{stem}_{tag}_raw.mp4"));
    let final_out = parent.join(format!("{stem}_{tag}.mp4"));

    clip_and_concat(&input, &segments, &raw).map_err(|e| e.to_string())?;

    let out = if vertical || mode == "douyin" {
        vertical_9_16(&raw, &final_out).map_err(|e| e.to_string())?;
        let _ = std::fs::remove_file(&raw);
        final_out
    } else {
        let _ = std::fs::rename(&raw, &final_out);
        final_out
    };

    Ok(ExportResult {
        output_path: out.to_string_lossy().into_owned(),
        message: format!("导出完成: {}", out.display()),
    })
}

#[tauri::command]
fn license_status() -> LicenseStatus {
    LicenseStatus {
        edition: "free".into(),
        message: "未激活 · 免费版（手动裁剪不限，AI 每月 2 次 + 水印）".into(),
    }
}

#[tauri::command]
fn open_output_folder(app: tauri::AppHandle, path: String) -> Result<(), String> {
    use tauri_plugin_shell::ShellExt;

    let p = Path::new(&path);
    let dir = if p.is_file() {
        p.parent().map(Path::to_path_buf)
    } else {
        Some(p.to_path_buf())
    };
    let Some(dir) = dir.filter(|d| d.exists()) else {
        return Err("路径不存在".into());
    };
    app.shell()
        .open(dir.to_string_lossy().to_string(), None)
        .map_err(|e| e.to_string())
}

fn output_parent_dir() -> PathBuf {
    if let Ok(appdata) = std::env::var("APPDATA") {
        let dir = PathBuf::from(appdata).join("VideoShortsAgent").join("output");
        let _ = std::fs::create_dir_all(&dir);
        return dir;
    }
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            probe_video_cmd,
            export_clip,
            license_status,
            open_output_folder,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
