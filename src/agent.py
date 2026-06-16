import os
import json
from openai import OpenAI
from src.youtube import (
    get_youtube_client,
    resolve_channel_id,
    fetch_last_n_videos,
    fetch_channel_stats,
    ALL_CHANNELS,
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

AGENT_SYSTEM = """You are the MoveUp Media Content Intelligence Assistant — an autonomous analytics agent for a digital media agency.

You have access to tools to fetch live YouTube data for MoveUp Media's channels (Netflu, ThePlayoffsTV) and competitor channels.

Your job:
- Understand what the user wants to know about YouTube performance.
- Decide autonomously which tools to call and with what parameters.
- Synthesize the fetched data into a clear, professional answer.
- Be specific with numbers. Surface actionable insights, not just data.

Available channels:
- MoveUp: Netflu (@Netflu), ThePlayoffsTV (@ThePlayoffsTV)
- Competitors: BeFootball (@BeFootball), Oh My Goal (@OhMyGoal)

When asked to compare channels or time ranges, fetch data for all relevant channels before answering.
Always ground your analysis in the actual numbers you retrieve."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_channel_stats",
            "description": "Get overall statistics for one or more YouTube channels (subscribers, total views, total videos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of channel names. Valid: Netflu, ThePlayoffsTV, BeFootball, Oh My Goal",
                    }
                },
                "required": ["channel_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_videos",
            "description": "Fetch the most recent videos from one or more channels with metrics: views, likes, comments, engagement rate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of channel names. Valid: Netflu, ThePlayoffsTV, BeFootball, Oh My Goal",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of recent videos per channel (1-20). Default: 10.",
                    },
                },
                "required": ["channel_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cached_report",
            "description": "Retrieve the most recently generated performance report without making new API calls.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    try:
        youtube = get_youtube_client()

        if tool_name == "get_cached_report":
            from src.analyzer import load_report
            report = load_report()
            if report:
                return json.dumps({"report": report[:3000] + "..." if len(report) > 3000 else report})
            return json.dumps({"error": "No cached report found. Generate a report first."})

        channel_names = tool_input.get("channel_names", [])
        n = tool_input.get("n", 10)
        results = {}

        for name in channel_names:
            handle = ALL_CHANNELS.get(name)
            if not handle:
                results[name] = {"error": f"Unknown channel: {name}. Valid: {list(ALL_CHANNELS.keys())}"}
                continue
            try:
                channel_id = resolve_channel_id(youtube, handle)
                if tool_name == "get_channel_stats":
                    results[name] = fetch_channel_stats(youtube, channel_id)
                elif tool_name == "get_recent_videos":
                    videos = fetch_last_n_videos(youtube, channel_id, n)
                    avg_views = sum(v["views"] for v in videos) / len(videos) if videos else 0
                    avg_eng = sum(v["engagement_rate"] for v in videos) / len(videos) if videos else 0
                    results[name] = {
                        "channel_id": channel_id,
                        "video_count": len(videos),
                        "avg_views": round(avg_views),
                        "avg_engagement_rate": round(avg_eng, 4),
                        "videos": videos,
                    }
            except Exception as e:
                results[name] = {"error": str(e)}

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_agent(user_message: str, conversation_history: list, cached_data: dict | None = None) -> tuple[str, list]:
    history = conversation_history + [{"role": "user", "content": user_message}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            messages=[{"role": "system", "content": AGENT_SYSTEM}] + history,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            history.append({"role": "assistant", "content": msg.content, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]})

            for tc in msg.tool_calls:
                tool_input = json.loads(tc.function.arguments)
                result = execute_tool(tc.function.name, tool_input)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            final_text = msg.content or ""
            history.append({"role": "assistant", "content": final_text})
            return final_text, history
