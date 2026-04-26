from __future__ import annotations

from pathlib import Path

from cartograph.config import Config
from cartograph.reconciler import ReconcileResult

_CHANNEL_NAMES = {
    1: "Channel 1: Git → Roadmap",
    2: "Channel 2: Memory → Roadmap",
    3: "Channel 3: Manifest → Docs",
}


def render(result: ReconcileResult, repo_path: Path | None = None) -> str:
    date_str = result.timestamp.strftime("%Y-%m-%d")
    lines = [f"# Reconciliation Report — {date_str}", ""]

    open_flags = [f for f in result.flags if not f.resolved]
    resolved_flags = [f for f in result.flags if f.resolved]

    for ch in result.channels_run:
        lines.append(f"## {_CHANNEL_NAMES[ch]}")
        ch_flags = [f for f in open_flags if f.channel == ch]
        if ch_flags:
            for flag in ch_flags:
                src = _rel(flag.source, repo_path)
                lines.append(f"- **{flag.type}**: {flag.detail} (`{src}`)")
        else:
            lines.append("No issues found.")
        lines.append("")

    if resolved_flags:
        lines.append("## Resolved (suppressed)")
        for flag in resolved_flags:
            lines.append(f"- `{flag.id}` — {flag.detail}")
        lines.append("")

    return "\n".join(lines)


def write_report(result: ReconcileResult, config: Config) -> Path:
    date_str = result.timestamp.strftime("%Y-%m-%d")
    output_path = config.repo_path / config.reconcile.report_output.replace("{date}", date_str)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(result, config.repo_path))
    return output_path


def _rel(source: str, repo_path: Path | None) -> str:
    if not repo_path:
        return source
    try:
        return str(Path(source).relative_to(repo_path))
    except ValueError:
        return source
