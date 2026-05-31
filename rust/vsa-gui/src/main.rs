#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::sync::mpsc;
use std::thread;

use eframe::egui;
use vsa_core::{clip_and_concat, parse_segments, vertical_9_16};

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([960.0, 720.0])
            .with_title("VideoShorts Studio"),
        ..Default::default()
    };
    eframe::run_native(
        "VideoShorts Studio",
        options,
        Box::new(|_cc| Ok(Box::new(StudioApp::default()))),
    )
}

#[derive(Default)]
struct StudioApp {
    video_path: String,
    segments_text: String,
    vertical_9_16: bool,
    douyin_max_sec: f64,
    status: String,
    busy: bool,
    last_output: Option<PathBuf>,
    rx: Option<mpsc::Receiver<Result<String, String>>>,
}

impl StudioApp {
    fn start_job(&mut self) {
        if self.busy {
            return;
        }
        let input = PathBuf::from(self.video_path.trim());
        if !input.is_file() {
            self.status = "请先选择视频文件".into();
            return;
        }
        let segs = match parse_segments(&self.segments_text) {
            Ok(s) => s,
            Err(e) => {
                self.status = format!("时间段错误: {e}");
                return;
            }
        };
        if self.vertical_9_16 {
            let total: f64 = segs.iter().map(|s| s.end - s.start).sum();
            if total > self.douyin_max_sec + 0.5 {
                self.status = format!(
                    "抖音建议总时长 ≤ {:.0} 秒，当前 {total:.1} 秒",
                    self.douyin_max_sec
                );
                return;
            }
        }
        let out_dir = std::env::var("USERPROFILE")
            .ok()
            .map(|h| PathBuf::from(h).join("Videos"))
            .filter(|p| p.is_dir())
            .unwrap_or_else(|| std::env::temp_dir());
        let stem = input
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("output");
        let output = out_dir.join(format!("{stem}_vsa_export.mp4"));

        self.busy = true;
        self.status = "处理中…".into();
        let vertical = self.vertical_9_16;
        let (tx, rx) = mpsc::channel();
        self.rx = Some(rx);
        thread::spawn(move || {
            let result = (|| {
                if vertical {
                    let tmp = output.with_extension("vsa_tmp.mp4");
                    clip_and_concat(&input, &segs, &tmp)?;
                    vertical_9_16(&tmp, &output)?;
                    let _ = std::fs::remove_file(&tmp);
                } else {
                    clip_and_concat(&input, &segs, &output)?;
                }
                Ok(output.display().to_string())
            })()
            .map_err(|e| e.to_string());
            let _ = tx.send(result);
        });
    }
}

impl eframe::App for StudioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        if let Some(rx) = &self.rx {
            if let Ok(res) = rx.try_recv() {
                self.busy = false;
                self.rx = None;
                match res {
                    Ok(path) => {
                        self.last_output = Some(PathBuf::from(&path));
                        self.status = format!("完成: {path}");
                    }
                    Err(e) => self.status = format!("失败: {e}"),
                }
            }
        }
        if self.busy {
            ctx.request_repaint_after(std::time::Duration::from_millis(200));
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("VideoShorts Studio");
            ui.label("方案 A · 本地裁剪 · 无需 API Key · Rust 轻量版");
            ui.separator();

            ui.horizontal(|ui| {
                ui.label("视频文件:");
                ui.text_edit_singleline(&mut self.video_path);
                if ui.button("浏览…").clicked() {
                    if let Some(p) = rfd::FileDialog::new()
                        .add_filter("视频", &["mp4", "mkv", "mov", "webm"])
                        .pick_file()
                    {
                        self.video_path = p.display().to_string();
                    }
                }
            });

            ui.label("时间段（每行一段，如 0:30-1:05 或 90-120）:");
            ui.add(
                egui::TextEdit::multiline(&mut self.segments_text)
                    .desired_rows(6)
                    .hint_text("0:00-0:45\n1:20-2:00"),
            );

            ui.checkbox(&mut self.vertical_9_16, "导出 9:16 竖屏（抖音/快手）");
            if self.vertical_9_16 {
                ui.add(
                    egui::Slider::new(&mut self.douyin_max_sec, 15.0..=180.0)
                        .text("时长上限(秒)"),
                );
            }

            ui.add_enabled_ui(!self.busy, |ui| {
                if ui.button("开始导出").clicked() {
                    self.start_job();
                }
            });

            ui.separator();
            ui.label(&self.status);
            if let Some(p) = &self.last_output {
                ui.label(format!("输出: {}", p.display()));
            }

            ui.separator();
            ui.collapsing("后续版本（Python 能力迁移）", |ui| {
                ui.label("· AI 智能切片 / 翻译配音（用户自带通义 Key）");
                ui.label("· 电商自动切分 / 批量队列 / 短剧 lite");
            });
        });
    }
}
