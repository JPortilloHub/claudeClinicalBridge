#!/usr/bin/env python3
"""
Claude Clinical Bridge - Process physician notes through multi-agent AI pipeline.

Usage:
    python main.py "physician note text here..."
    python main.py --file note.txt --payer "Medicare" --output json
    python main.py --file note.txt --patient-id P123 --procedure "99214" --output full
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

from src.python.orchestration.coordinator import ClinicalPipelineCoordinator
from src.python.utils.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Process clinical notes through the Claude Clinical Bridge pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "65yo male with chest pain, BP 160/95, history of HTN"
  python main.py --file note.txt --payer "Medicare" --procedure "99214"
  python main.py --file note.txt --output json
  python main.py --file note.txt --skip-prior-auth --output full
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("note", nargs="?", help="Clinical note text (inline)")
    input_group.add_argument("--file", "-f", help="Path to a text file containing the clinical note")

    parser.add_argument("--patient-id", help="FHIR patient identifier")
    parser.add_argument("--payer", help="Payer name (e.g., Medicare, Aetna)")
    parser.add_argument("--procedure", help="Procedure description or CPT code")
    parser.add_argument("--skip-prior-auth", action="store_true", help="Skip prior authorization phase")
    parser.add_argument(
        "--output", "-o",
        choices=["summary", "json", "full"],
        default="summary",
        help="Output format (default: summary)",
    )

    args = parser.parse_args()

    # Load note
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        note = file_path.read_text().strip()
    else:
        note = args.note

    if not note:
        print("Error: Empty clinical note provided", file=sys.stderr)
        sys.exit(1)

    print(f"Processing clinical note ({len(note)} chars)...")
    print(f"Model: {settings.claude_model}")
    if args.payer:
        print(f"Payer: {args.payer}")
    if args.patient_id:
        print(f"Patient ID: {args.patient_id}")
    print()

    # Create coordinator with shared client
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    coordinator = ClinicalPipelineCoordinator(client=client)

    # Run pipeline
    state = coordinator.process_note(
        note=note,
        patient_id=args.patient_id,
        payer=args.payer,
        procedure=args.procedure,
        skip_prior_auth=args.skip_prior_auth,
    )

    # Output results
    if args.output == "json":
        print(json.dumps(state.to_summary(), indent=2))

    elif args.output == "summary":
        print(f"Workflow ID: {state.workflow_id}")
        print(f"Status:      {state.status.value}")
        duration = state.total_duration_seconds
        if duration is not None:
            print(f"Duration:    {duration:.1f}s")
        tokens = state.total_tokens
        print(f"Tokens:      {tokens['input_tokens']} in / {tokens['output_tokens']} out")
        print()
        print("Phases:")
        for phase in state.all_phases:
            status_icon = {
                "completed": "+",
                "failed": "X",
                "skipped": "-",
                "running": "~",
                "pending": ".",
            }.get(phase.status.value, "?")
            dur = f"{phase.duration_seconds:.1f}s" if phase.duration_seconds else "--"
            print(f"  [{status_icon}] {phase.phase_name:<20} {phase.status.value:<12} {dur}")
            if phase.error:
                print(f"      Error: {phase.error}")

    elif args.output == "full":
        print(f"Workflow ID: {state.workflow_id}")
        print(f"Status:      {state.status.value}")
        duration = state.total_duration_seconds
        if duration is not None:
            print(f"Duration:    {duration:.1f}s")
        print()
        for phase in state.all_phases:
            print(f"{'=' * 60}")
            print(f"Phase: {phase.phase_name} ({phase.status.value})")
            if phase.duration_seconds:
                print(f"Duration: {phase.duration_seconds:.1f}s")
            if phase.usage:
                print(f"Tokens: {phase.usage}")
            if phase.error:
                print(f"Error: {phase.error}")
            if phase.content:
                print(f"\nOutput:\n{phase.content}")
            print()

    # Exit with appropriate code
    sys.exit(0 if state.status.value == "completed" else 1)


if __name__ == "__main__":
    main()
