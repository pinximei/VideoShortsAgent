from python_agent.summary_timing import (
    compute_panel_reveal_frame,
    compute_summary_reveal_frames,
)


def test_summary_reveal_matches_sentence():
    sents = [
        {"text": "第一句讲开源", "start": 0.0, "end": 2.0},
        {"text": "第二句讲部署", "start": 2.2, "end": 4.0},
    ]
    frames = compute_summary_reveal_frames(["开源神器", "一键部署"], sents, fps=30)
    assert frames[0] == 0
    assert frames[1] >= 60
