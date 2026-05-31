use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};
use vsa_core::{clip_and_concat, parse_segments, probe_video, vertical_9_16};

#[derive(Parser)]
#[command(name = "vsa-cli", about = "VideoShorts Studio — local clip engine")]
struct Cli {
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 显示视频时长与分辨率
    Probe { input: PathBuf },
    /// 按时间段裁剪并拼接
    Clip {
        input: PathBuf,
        #[arg(short, long)]
        segments: String,
        #[arg(short, long)]
        output: PathBuf,
        #[arg(long)]
        vertical: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Commands::Probe { input } => {
            let p = probe_video(&input)?;
            println!("{}", serde_json::to_string_pretty(&p)?);
        }
        Commands::Clip {
            input,
            segments,
            output,
            vertical,
        } => {
            let segs = parse_segments(&segments)?;
            let out = if vertical {
                let tmp = output.with_extension("tmp.mp4");
                clip_and_concat(&input, &segs, &tmp)?;
                vertical_9_16(&tmp, &output)?;
                let _ = std::fs::remove_file(&tmp);
                output
            } else {
                clip_and_concat(&input, &segs, &output)?;
                output
            };
            println!("OK: {}", out.display());
        }
    }
    Ok(())
}
