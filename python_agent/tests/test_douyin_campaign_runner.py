from python_agent.douyin_campaign_state import CampaignState, apply_state_to_slides, tune_state_from_issues
from python_agent.douyin_campaign_runner import run_agent_rounds
from python_agent.douyin_cycle_review import slides_digest
from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.platform_caption_presets import reconcile_platform_slides


def test_tune_state_stagger():
    s = CampaignState(stagger_frames=14)
    s2 = tune_state_from_issues(s, ["content_0:stagger_too_slow"])
    assert s2.stagger_frames == 13


def test_agent_rounds_on_mock():
    slides = reconcile_platform_slides(
        mock_compose_from_brief({"platform": "douyin", "feed_kind": "github_daily"})["slides"],
        "douyin",
    )
    out, logs, pre = run_agent_rounds(slides, cycle=1)
    assert len(logs) == 10
    assert len(out) == len(slides)
    assert slides_digest(slides) != slides_digest(out) or len(pre) == 0
