from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cartograph import reconciler, reporter
from cartograph import state as state_mod
from cartograph.config import load


def main(argv=None, repo_path=None):
    parser = argparse.ArgumentParser(
        prog="cartograph",
        description="Documentation drift detection for AI-augmented projects.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    sub.add_parser("reconcile", help="Run all channels, write report, update state.")

    p_resolve = sub.add_parser("resolve", help="Mark a flag resolved.")
    p_resolve.add_argument("flag_id", metavar="flag-id")

    sub.add_parser("status", help="Show last run timestamp and resolved flag count.")

    p_context = sub.add_parser("context", help="Print session context: current work, reconcile status, orientation.")
    p_context.add_argument("--query", default=None, metavar="QUERY",
                           help="Rank orientation sections by relevance to this query (requires cartograph[embeddings]).")

    p_init = sub.add_parser("init", help="Scaffold a new project.")
    p_init.add_argument("--template", default=None, metavar="TEMPLATE")

    p_section = sub.add_parser("add-section", help="Add a section to the scaffold.")
    p_section.add_argument("name")
    p_section.add_argument("--question", default="", metavar="QUESTION")
    p_section.add_argument("--lifecycle", default="Stable", metavar="LIFECYCLE")

    p_track = sub.add_parser("track", help="Manage the work checklist.")
    ts = p_track.add_subparsers(dest="track_command", metavar="track-command")
    p_done = ts.add_parser("done", help="Mark one or more open items as complete.")
    p_done.add_argument("terms", nargs="+", metavar="TERM",
                        help="Substring(s) to match against open items — one per completed task.")

    p_related = sub.add_parser("related", help="Show docs historically related to a code file.")
    p_related.add_argument("file", metavar="FILE")

    p_manifest = sub.add_parser("manifest", help="Manage the manifest dependency graph.")
    ms = p_manifest.add_subparsers(dest="manifest_command", metavar="manifest-command")

    p_edge = ms.add_parser("add-edge", help="Append an edge to manifest.toml.")
    p_edge.add_argument("--from", dest="from_doc", required=True, metavar="FROM")
    p_edge.add_argument("--to", dest="to_doc", required=True, metavar="TO")
    p_edge.add_argument("--type", dest="edge_type", required=True, metavar="TYPE")
    p_edge.add_argument("--term", default="", metavar="TERM")
    p_edge.add_argument("--heading", default="", metavar="HEADING")

    p_fact = ms.add_parser("add-fact", help="Append a fact to manifest.toml.")
    p_fact.add_argument("--key", required=True, metavar="KEY")
    p_fact.add_argument("--canonical", required=True, metavar="CANONICAL")
    p_fact.add_argument("--duplicate", dest="duplicates", action="append", default=[], metavar="PATH")

    args = parser.parse_args(argv)

    if repo_path is None:
        repo_path = Path.cwd()
    config = load(repo_path)

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "context":
        return _context(config, getattr(args, "query", None))
    if args.command == "reconcile":
        return _reconcile(config)
    if args.command == "resolve":
        return _resolve(config, args.flag_id)
    if args.command == "status":
        return _status(config)
    if args.command == "init":
        return _init(config, args.template)
    if args.command == "add-section":
        return _add_section(config, args.name, args.question, args.lifecycle)
    if args.command == "track":
        if args.track_command == "done":
            return _track_done(config, args.terms)
        p_track.print_help()
        return 0
    if args.command == "related":
        return _related(config, args.file)
    if args.command == "manifest":
        if args.manifest_command == "add-edge":
            return _manifest_add_edge(config, args)
        if args.manifest_command == "add-fact":
            return _manifest_add_fact(config, args)
        p_manifest.print_help()
        return 0
    return 0


def _context(config, query=None):
    from cartograph import context as context_mod
    print(context_mod.generate(config, query=query))
    return 0


def _reconcile(config):
    result = reconciler.run(config)
    path = reporter.write_report(result, config)
    open_count = sum(1 for f in result.flags if not f.resolved)
    resolved_count = sum(1 for f in result.flags if f.resolved)
    print(f"Report: {path}")
    print(f"Flags:  {open_count} open, {resolved_count} resolved")
    for f in result.flags:
        if not f.resolved:
            print(f"  [{f.channel}] {f.type}: {f.detail}")
    return 0


def _resolve(config, flag_id):
    state = state_mod.load(config.repo_path)
    if state_mod.is_resolved(state, flag_id):
        print(f"Already resolved: {flag_id}")
        return 0
    state_mod.mark_resolved(state, flag_id)
    state_mod.save(state, config.repo_path)
    print(f"Resolved: {flag_id}")
    return 0


def _status(config):
    state = state_mod.load(config.repo_path)
    if state.last_run:
        print(f"Last run:       {state.last_run.isoformat()}")
    else:
        print("Last run:       never")
    print(f"Resolved flags: {len(state.resolved_ids)}")
    return 0


def _init(config, template):
    from cartograph import scaffold
    scaffold.init(config.repo_path, template=template)
    print("Project initialised.")
    return 0


def _add_section(config, name, question, lifecycle):
    from cartograph import scaffold
    scaffold.add_section(config.repo_path, name, question, lifecycle)
    print(f"Section '{name}' added.")
    return 0


def _related(config, file_path):
    from cartograph import observations as obs_mod
    results = obs_mod.query_file(config, file_path)
    if not results:
        print(f"No observations for {file_path}")
        return 0
    for md_file, section, count in results:
        print(f"{md_file}:{section}  ({count}×)")
    return 0


def _track_done(config, terms):
    from cartograph import track as track_mod
    try:
        results = track_mod.done(config.repo_path, config, terms)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    for term, matched in results.items():
        if matched:
            print(f"  done: {matched}")
        else:
            print(f"  no match: {term!r}")
    return 0


def _manifest_add_edge(config, args):
    path = config.repo_path / config.docs.manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    block = (
        f'\n[[edge]]\n'
        f'from = "{args.from_doc}"\n'
        f'to = "{args.to_doc}"\n'
        f'type = "{args.edge_type}"\n'
    )
    if args.term:
        block += f'term = "{args.term}"\n'
    if args.heading:
        block += f'heading = "{args.heading}"\n'
    with path.open("a") as f:
        f.write(block)
    print(f"Edge added → {config.docs.manifest}")
    return 0


def _manifest_add_fact(config, args):
    path = config.repo_path / config.docs.manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    dups = "".join(f'\n  "{d}",' for d in args.duplicates)
    block = (
        f'\n[[fact]]\n'
        f'key = "{args.key}"\n'
        f'canonical = "{args.canonical}"\n'
        f'duplicates = [{dups}\n]\n'
    )
    with path.open("a") as f:
        f.write(block)
    print(f"Fact added → {config.docs.manifest}")
    return 0
