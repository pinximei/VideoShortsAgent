# VSA 全面审查报告（20 轮）

- 时间（UTC）: 2026-05-31T23:56:13.760750+00:00
- 目录: `D:\VideoShortsAgent\reports\vsa_audit_20260531T235611Z`
- 通过: **17/20**
- Git: f549061 Fix slow sparse male Douyin voice: Yunyang, faster TTS, richer script.

## 各轮结果

| # | 检查项 | 结果 | 证据文件 |
|---|--------|------|----------|
| 1 | pytest_test_vsa | ❌ | `round_01_pytest_test_vsa.json` |
| 2 | tts_params_unit | ✅ | `round_02_tts_params_unit.json` |
| 3 | py_compile_vsa | ✅ | `round_03_py_compile_vsa.json` |
| 4 | import_vsa_chain | ✅ | `round_04_import_vsa_chain.json` |
| 5 | vsa_render_tts_wiring | ✅ | `round_05_vsa_render_tts_wiring.json` |
| 6 | vsa_py_render_from_plan_args | ✅ | `round_06_vsa_py_render_from_plan_args.json` |
| 7 | slides_render_tts_parity | ✅ | `round_07_slides_render_tts_parity.json` |
| 8 | pipeline_render_tts | ✅ | `round_08_pipeline_render_tts.json` |
| 9 | legacy_dubbing_without_rate | ❌ | `round_09_legacy_dubbing_without_rate.json` |
| 10 | test_vsa_case_count | ✅ | `round_10_test_vsa_case_count.json` |
| 11 | vsa_adapter_present | ✅ | `round_11_vsa_adapter_present.json` |
| 12 | rust_vsa_core_tree | ✅ | `round_12_rust_vsa_core_tree.json` |
| 13 | pipeline_config_render_keys | ✅ | `round_13_pipeline_config_render_keys.json` |
| 14 | orchestrator_render_entry | ✅ | `round_14_orchestrator_render_entry.json` |
| 15 | pytest_capabilities_registry | ❌ | `round_15_pytest_capabilities_registry.json` |
| 16 | vsa_file_manifest_sha256 | ✅ | `round_16_vsa_file_manifest_sha256.json` |
| 17 | render_from_plan_callers | ✅ | `round_17_render_from_plan_callers.json` |
| 18 | pipeline_gates_tts_clips | ✅ | `round_18_pipeline_gates_tts_clips.json` |
| 19 | tts_resolve_runtime | ✅ | `round_19_tts_resolve_runtime.json` |
| 20 | git_commit_at_audit | ✅ | `round_20_git_commit_at_audit.json` |

## 复现

```powershell
cd D:\VideoShortsAgent
py -3 scripts/vsa_comprehensive_audit.py
```

每轮原始输出见同目录 `round_XX_*.json`。