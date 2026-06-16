"""LLM-powered report generator using OpenAI GPT-4o."""

import os
from openai import OpenAI
from pathlib import Path

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = """You are a senior media analyst at MoveUp Media, a digital agency managing YouTube content campaigns for multiple clients.

Your role is to produce professional, actionable performance reports for internal use by content strategists and account managers.

When analyzing YouTube channel data:
- Focus on the metrics that drive business decisions: views, engagement rate (likes+comments/views), publication frequency, and content trends.
- Rate each video as **Strong**, **Average**, or **Underperforming** relative to the channel's own average — not absolute benchmarks.
- Write in a professional, direct tone. Be specific. Avoid vague statements like "performance was mixed."
- Every recommendation must be concrete and implementable within the next week.
- Format output as structured Markdown with clear sections."""

REPORT_PROMPT_TEMPLATE = """Analyze the following YouTube performance data for MoveUp Media's channels.

## Channel Data
{channel_data}

## Your Analysis Must Include

### For each channel ({channel_names}):
1. **Overall Performance Summary** — How did this channel perform across its last 10 videos? Include average views, average engagement rate, and publication cadence.
2. **Per-Video Ratings Table** — Rate each video as Strong / Average / Underperforming with a one-line explanation. Include views and engagement rate.
3. **Top 2-3 Videos** — Why did they succeed? What patterns do you notice?
4. **Bottom 2-3 Videos** — What went wrong? What factors likely caused underperformance?
5. **Actionable Recommendations** — At least 2 specific, implementable recommendations for the next publishing cycle.

### Cross-Channel Comparison
- Which channel is performing better overall and why?
- What content strategies from one channel could be applied to the other?

{competitive_section}

Format the output in clean Markdown. Be specific with numbers. Avoid generic advice."""

COMPETITIVE_SECTION = """### Competitive Benchmark
Compare MoveUp Media's channels against the competitor channels included in the data.
- How do Netflu and ThePlayoffsTV compare on key metrics (views, engagement, posting frequency)?
- Identify 1-2 strategies competitors use that MoveUp Media could adopt."""


def format_channel_data_for_prompt(data: dict) -> str:
    sections = []
    for channel_name, channel_info in data.items():
        stats = channel_info.get("stats", {})
        videos = channel_info.get("videos", [])

        lines = [
            f"### Channel: {channel_name} ({channel_info.get('handle', '')})",
            f"- Subscribers: {stats.get('subscribers', 'N/A'):,}",
            f"- Total channel views: {stats.get('total_views', 'N/A'):,}",
            f"- Total videos published: {stats.get('total_videos', 'N/A')}",
            f"- Data fetched at: {channel_info.get('fetched_at', 'N/A')}",
            "",
            "**Last 10 Videos:**",
        ]

        avg_views = sum(v["views"] for v in videos) / len(videos) if videos else 0
        avg_eng = sum(v["engagement_rate"] for v in videos) / len(videos) if videos else 0
        lines.append(f"- Channel average views (last 10): {avg_views:,.0f}")
        lines.append(f"- Channel average engagement rate (last 10): {avg_eng:.3f}%")
        lines.append("")

        for i, v in enumerate(videos, 1):
            lines.append(
                f"{i}. **{v['title']}** | "
                f"Published: {v['published_at'][:10]} | "
                f"Views: {v['views']:,} | "
                f"Likes: {v['likes']:,} | "
                f"Comments: {v['comments']:,} | "
                f"Engagement: {v['engagement_rate']:.3f}% | "
                f"[Link]({v['url']})"
            )
        sections.append("\n".join(lines))

    return "\n\n---\n\n".join(sections)


def generate_report(data: dict, include_competitive: bool = False) -> str:
    moveup_channels = {k: v for k, v in data.items() if k in ("Netflu", "ThePlayoffsTV")}
    competitor_channels = {k: v for k, v in data.items() if k not in ("Netflu", "ThePlayoffsTV")}

    analysis_data = dict(moveup_channels)
    if include_competitive and competitor_channels:
        analysis_data.update(competitor_channels)

    channel_data_str = format_channel_data_for_prompt(analysis_data)
    channel_names = " and ".join(moveup_channels.keys())
    competitive_section = COMPETITIVE_SECTION if (include_competitive and competitor_channels) else ""

    prompt = REPORT_PROMPT_TEMPLATE.format(
        channel_data=channel_data_str,
        channel_names=channel_names,
        competitive_section=competitive_section,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content


def save_report(report: str, path: str = "data/reports/latest_report.md"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)


def load_report(path: str = "data/reports/latest_report.md") -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")
