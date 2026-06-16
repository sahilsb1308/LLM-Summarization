"""MoveUp Content Ops Bot - Streamlit Management Platform."""

import os
import json
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="MoveUp Content Ops Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.shields.io/badge/MoveUp-Media-blue?style=for-the-badge", use_container_width=False)
    st.title("Content Ops Bot")
    st.caption("AI-powered YouTube analytics")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Dashboard", "Performance Report", "Conversational Agent", "Settings"],
        label_visibility="collapsed",
    )

    st.divider()

    # Scheduler status
    from src.scheduler import get_next_run_time, start_scheduler, stop_scheduler
    if "scheduler_started" not in st.session_state:
        st.session_state.scheduler_started = False

    sched_enabled = st.toggle("Weekly Auto-Refresh", value=st.session_state.scheduler_started)
    if sched_enabled and not st.session_state.scheduler_started:
        start_scheduler(include_competitive=True)
        st.session_state.scheduler_started = True
    elif not sched_enabled and st.session_state.scheduler_started:
        stop_scheduler()
        st.session_state.scheduler_started = False

    next_run = get_next_run_time()
    if next_run:
        st.caption(f"Next refresh: {next_run}")

    st.divider()
    st.caption("Channels: Netflu - ThePlayoffsTV")
    st.caption("Competitors: BeFootball - Oh My Goal")


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_data():
    from src.youtube import load_data as _load
    return _load()

def load_report():
    from src.analyzer import load_report as _load
    return _load()

def fmt_number(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ── Dashboard ────────────────────────────────────────────────────────────────

if page == "Dashboard":
    st.title("YouTube Performance Dashboard")
    data = load_data()

    if not data:
        st.info("No data loaded yet. Go to **Settings** to collect data.")
    else:
        moveup = {k: v for k, v in data.items() if k in ("Netflu", "ThePlayoffsTV")}
        competitors = {k: v for k, v in data.items() if k not in ("Netflu", "ThePlayoffsTV")}
        fetched = list(data.values())[0].get("fetched_at", "")[:10]
        st.caption(f"Data collected on: {fetched}")

        # KPI cards
        st.subheader("MoveUp Media Channels")
        cols = st.columns(len(moveup))
        for i, (name, info) in enumerate(moveup.items()):
            stats = info.get("stats", {})
            videos = info.get("videos", [])
            avg_views = sum(v["views"] for v in videos) / len(videos) if videos else 0
            avg_eng = sum(v["engagement_rate"] for v in videos) / len(videos) if videos else 0
            with cols[i]:
                st.metric("Channel", name)
                st.metric("Subscribers", fmt_number(stats.get("subscribers", 0)))
                st.metric("Avg Views (last 10)", fmt_number(int(avg_views)))
                st.metric("Avg Engagement Rate", f"{avg_eng:.3f}%")

        st.divider()

        # Video tables per channel
        for name, info in moveup.items():
            videos = info.get("videos", [])
            if not videos:
                continue
            st.subheader(f"{name} - Last 10 Videos")
            avg_views = sum(v["views"] for v in videos) / len(videos)
            rows = []
            for v in videos:
                rel = v["views"] / avg_views if avg_views > 0 else 1
                if rel >= 1.3:
                    rating = "Strong"
                elif rel >= 0.7:
                    rating = "Average"
                else:
                    rating = "Underperforming"
                rows.append({
                    "Title": v["title"][:55] + ("…" if len(v["title"]) > 55 else ""),
                    "Published": v["published_at"][:10],
                    "Views": fmt_number(v["views"]),
                    "Likes": fmt_number(v["likes"]),
                    "Comments": fmt_number(v["comments"]),
                    "Engagement": f"{v['engagement_rate']:.3f}%",
                    "Rating": rating,
                    "Link": v["url"],
                })
            import pandas as pd
            df = pd.DataFrame(rows)

            def color_rating(val):
                colors = {"Strong": "background-color: #d4edda", "Average": "background-color: #fff3cd", "Underperforming": "background-color: #f8d7da"}
                return colors.get(val, "")

            styled = df.style.applymap(color_rating, subset=["Rating"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        # Competitor section
        if competitors:
            st.divider()
            st.subheader("Competitive Benchmark")
            comp_cols = st.columns(len(competitors))
            for i, (name, info) in enumerate(competitors.items()):
                stats = info.get("stats", {})
                videos = info.get("videos", [])
                avg_views = sum(v["views"] for v in videos) / len(videos) if videos else 0
                avg_eng = sum(v["engagement_rate"] for v in videos) / len(videos) if videos else 0
                with comp_cols[i]:
                    st.metric("Channel", name)
                    st.metric("Subscribers", fmt_number(stats.get("subscribers", 0)))
                    st.metric("Avg Views (last 10)", fmt_number(int(avg_views)))
                    st.metric("Avg Engagement", f"{avg_eng:.3f}%")


# ── Performance Report ────────────────────────────────────────────────────────

elif page == "Performance Report":
    st.title("AI-Generated Performance Report")
    report = load_report()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Regenerate Report", type="primary", use_container_width=True):
            data = load_data()
            if not data:
                st.error("No data available. Collect data first in Settings.")
            else:
                with st.spinner("Generating report with Claude..."):
                    from src.analyzer import generate_report, save_report
                    include_comp = any(k not in ("Netflu", "ThePlayoffsTV") for k in data)
                    report = generate_report(data, include_competitive=include_comp)
                    save_report(report)
                    st.success("Report generated!")
                    st.rerun()

    if report:
        st.markdown(report)
    else:
        st.info("No report yet. Click **Regenerate Report** to create one (requires data to be collected first).")


# ── Conversational Agent ──────────────────────────────────────────────────────

elif page == "Conversational Agent":
    st.title("Content Intelligence Agent")
    st.caption("Ask anything about channel performance. The agent fetches live data autonomously.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []

    # Suggested questions
    suggestions = [
        "Which channel had better engagement last week?",
        "Compare Netflu vs ThePlayoffsTV views over the last 10 videos",
        "What type of content works best for us?",
        "How do we compare against BeFootball?",
        "Which video dropped the most and why?",
    ]

    if not st.session_state.messages:
        st.markdown("**Try asking:**")
        cols = st.columns(len(suggestions))
        for i, s in enumerate(suggestions):
            with cols[i]:
                if st.button(s, use_container_width=True, key=f"sug_{i}"):
                    st.session_state._pending_message = s
                    st.rerun()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle pending suggestion click
    pending = st.session_state.pop("_pending_message", None)

    prompt = st.chat_input("Ask about your YouTube channels...") or pending
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                from src.agent import run_agent
                cached_data = load_data()
                response, updated_history = run_agent(
                    prompt,
                    st.session_state.agent_history,
                    cached_data=cached_data,
                )
                st.session_state.agent_history = updated_history
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    if st.session_state.messages:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.messages = []
            st.session_state.agent_history = []
            st.rerun()


# ── Settings ──────────────────────────────────────────────────────────────────

elif page == "Settings":
    st.title("Settings & Data Collection")

    # API key status
    yt_key = os.environ.get("YOUTUBE_API_KEY", "")
    oai_key = os.environ.get("OPENAI_API_KEY", "")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("YouTube API Key", "Configured" if yt_key else "Missing", delta=None)
    with col2:
        st.metric("OpenAI API Key", "Configured" if oai_key else "Missing", delta=None)

    if not yt_key or not oai_key:
        st.warning("Set both API keys in your `.env` file before collecting data.")

    st.divider()
    st.subheader("Data Collection")

    include_comp = st.checkbox("Include competitor channels (BeFootball, Oh My Goal)", value=True)

    if st.button("Collect Fresh Data", type="primary", disabled=not yt_key):
        from src.youtube import collect_all_data, save_data, MOVEUP_CHANNELS, COMPETITOR_CHANNELS
        channels = dict(MOVEUP_CHANNELS)
        if include_comp:
            channels.update(COMPETITOR_CHANNELS)

        with st.spinner(f"Fetching data for {len(channels)} channels..."):
            try:
                data = collect_all_data(channels=channels)
                save_data(data)
                st.success(f"Data collected for: {', '.join(data.keys())}")

                # Summary
                for name, info in data.items():
                    videos = info.get("videos", [])
                    st.write(f"- **{name}**: {len(videos)} videos fetched")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("Generate Report")

    if st.button("Generate AI Report", type="secondary", disabled=not oai_key):
        data = load_data()
        if not data:
            st.error("Collect data first.")
        else:
            with st.spinner("Generating report..."):
                from src.analyzer import generate_report, save_report
                comp_present = any(k not in ("Netflu", "ThePlayoffsTV") for k in data)
                report = generate_report(data, include_competitive=comp_present)
                save_report(report)
                st.success("Report saved. Go to **Performance Report** to view it.")

    st.divider()
    st.subheader("Cached Data Status")
    data = load_data()
    if data:
        fetched = list(data.values())[0].get("fetched_at", "unknown")
        st.success(f"Data available. Last fetched: {fetched[:19]} UTC")
        channels_list = list(data.keys())
        st.write(f"Channels: {', '.join(channels_list)}")
        if st.button("View raw JSON"):
            st.json(data)
    else:
        st.info("No cached data. Run **Collect Fresh Data** above.")
