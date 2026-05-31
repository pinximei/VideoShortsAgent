import { isTauri, tauriInvoke } from "./useTauri";

export type ExportPayload = {
  videoPath: string;
  segments: string;
  vertical: boolean;
  mode: "clip" | "douyin" | "ecommerce";
};

export type ExportResult = {
  output_path: string;
  message: string;
};

export async function runExport(payload: ExportPayload): Promise<ExportResult> {
  if (!isTauri()) {
    return {
      output_path: "",
      message: "浏览器预览模式：请在 Tauri 桌面环境中运行以调用 FFmpeg。",
    };
  }
  return tauriInvoke<ExportResult>("export_clip", {
    videoPath: payload.videoPath,
    segmentsText: payload.segments,
    vertical: payload.vertical || payload.mode === "douyin",
    mode: payload.mode,
  });
}
