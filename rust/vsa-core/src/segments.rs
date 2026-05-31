use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Segment {
    pub start: f64,
    pub end: f64,
}

pub fn parse_segments(text: &str) -> Result<Vec<Segment>> {
    let mut out = Vec::new();
    for (i, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (a, b) = split_range(line).map_err(|e| anyhow::anyhow!("第 {} 行: {}", i + 1, e))?;
        let start = parse_time_token(a)?;
        let end = parse_time_token(b)?;
        if end <= start {
            bail!("第 {} 行: 结束时间必须大于开始 ({start} >= {end})", i + 1);
        }
        out.push(Segment { start, end });
    }
    if out.is_empty() {
        bail!("请至少填写一行时间段，例如 0:30-1:05");
    }
    Ok(out)
}

fn split_range(line: &str) -> Result<(&str, &str), String> {
    for sep in ['-', '~', '–', '—'] {
        if let Some((a, b)) = line.split_once(sep) {
            return Ok((a.trim(), b.trim()));
        }
    }
    Err(format!("无法解析: {line}"))
}

fn parse_time_token(token: &str) -> Result<f64> {
    let token = token.trim();
    if !token.contains(':') {
        return token
            .parse::<f64>()
            .map_err(|_| anyhow::anyhow!("无效秒数: {token}"));
    }
    let parts: Vec<f64> = token
        .split(':')
        .map(|p| p.parse::<f64>())
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| anyhow::anyhow!("无效时间: {token}"))?;
    Ok(match parts.len() {
        2 => parts[0] * 60.0 + parts[1],
        3 => parts[0] * 3600.0 + parts[1] * 60.0 + parts[2],
        _ => bail!("无效时间: {token}"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_two_lines() {
        let segs = parse_segments("0:30-1:00\n90-120").unwrap();
        assert_eq!(segs.len(), 2);
        assert!((segs[0].start - 30.0).abs() < 0.01);
    }
}
