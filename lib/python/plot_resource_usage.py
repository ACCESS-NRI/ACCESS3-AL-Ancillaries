#!/usr/bin/env python3
"""Plot the PBS walltime, memory and jobFS usage of each task in an installed Cylc workflow.

The PBS resource summary that Gadi appends to each job's stdout (log/job/<cycle>/<task>/<NN>/job.out)
is parsed, and one bar chart per resource is written to the output directory. Where a task has
been run more than once (retries, multiple cycles) the most recent attempt with a summary is used.

Usage: plot_resource_usage.py <installed_workflow_path> <output_path>
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BYTES_PER_UNIT = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}
BYTES_PER_GB = 1e9

MEMORY_PATTERN = re.compile(
    r"Memory Requested:\s*(?P<requested>\S+)\s+Memory Used:\s*(?P<used>\S+)"
)
WALLTIME_PATTERN = re.compile(
    r"Walltime requested:\s*(?P<requested>\S+)\s+Walltime Used:\s*(?P<used>\S+)",
    re.IGNORECASE,
)
JOBFS_PATTERN = re.compile(
    r"JobFS requested:\s*(?P<requested>\S+)\s+JobFS used:\s*(?P<used>\S+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RequestedAndUsed:
    requested: float
    used: float


@dataclass(frozen=True)
class TaskUsage:
    task_name: str
    walltime_hours: RequestedAndUsed
    memory_gb: RequestedAndUsed
    jobfs_gb: RequestedAndUsed


def parse_size_in_gb(size_text):
    """Convert a PBS size such as '1.2GB' or '0B' to GB."""
    match = re.fullmatch(r"([\d.]+)\s*([A-Za-z]*)", size_text)
    unit = (match.group(2).upper() or "B") if match else None
    if match is None or unit not in BYTES_PER_UNIT:
        raise ValueError(f"Unrecognised size: {size_text!r}")
    return float(match.group(1)) * BYTES_PER_UNIT[unit] / BYTES_PER_GB


def parse_duration_in_hours(duration_text):
    """Convert a PBS HH:MM:SS duration to hours."""
    hours, minutes, seconds = (float(part) for part in duration_text.split(":"))
    return hours + minutes / 60 + seconds / 3600


def parse_job_output(job_output_text, task_name):
    """Extract the resource summary from a job.out, or None if it has no summary."""
    memory_match = MEMORY_PATTERN.search(job_output_text)
    walltime_match = WALLTIME_PATTERN.search(job_output_text)
    jobfs_match = JOBFS_PATTERN.search(job_output_text)
    if not (memory_match and walltime_match and jobfs_match):
        return None

    def pair(match, parser):
        return RequestedAndUsed(
            requested=parser(match.group("requested")), used=parser(match.group("used"))
        )

    return TaskUsage(
        task_name=task_name,
        walltime_hours=pair(walltime_match, parse_duration_in_hours),
        memory_gb=pair(memory_match, parse_size_in_gb),
        jobfs_gb=pair(jobfs_match, parse_size_in_gb),
    )


def submit_number_directories(task_directory):
    """Attempt directories of a task, most recent first. Skips the 'NN' symlink."""
    attempt_directories = [
        path for path in task_directory.iterdir() if path.name.isdigit() and not path.is_symlink()
    ]
    return sorted(attempt_directories, key=lambda path: int(path.name), reverse=True)


def latest_usage_for_task(task_directory):
    """Usage from the most recent attempt of a task that has a resource summary."""
    for attempt_directory in submit_number_directories(task_directory):
        job_output_path = attempt_directory / "job.out"
        if not job_output_path.is_file():
            continue
        usage = parse_job_output(
            job_output_path.read_text(errors="replace"), task_directory.name
        )
        if usage is not None:
            return usage
    return None


def collect_task_usage(workflow_path):
    """Usage for every task in the workflow, using the latest cycle each task ran in."""
    job_log_directory = workflow_path / "log" / "job"
    if not job_log_directory.is_dir():
        raise FileNotFoundError(f"No job logs found at {job_log_directory}")

    usage_by_task = {}
    cycle_directories = sorted(
        (path for path in job_log_directory.iterdir() if path.is_dir()), key=lambda path: path.name
    )
    for cycle_directory in cycle_directories:
        for task_directory in cycle_directory.iterdir():
            if not task_directory.is_dir():
                continue
            usage = latest_usage_for_task(task_directory)
            if usage is not None:
                usage_by_task[task_directory.name] = usage
    return sorted(usage_by_task.values(), key=lambda usage: usage.task_name)


def plot_resource(task_usages, resource_attribute, title, unit_label, output_file):
    """One bar per task showing the used amount, with the requested amount as an outline."""
    resource_values = [getattr(usage, resource_attribute) for usage in task_usages]
    task_names = [usage.task_name for usage in task_usages]
    positions = range(len(task_usages))

    figure_width = max(8, 0.45 * len(task_usages))
    figure, axes = plt.subplots(figsize=(figure_width, 7))
    axes.bar(
        positions,
        [value.requested for value in resource_values],
        fill=False,
        edgecolor="grey",
        linestyle="--",
        label="Requested",
    )
    axes.bar(
        positions,
        [value.used for value in resource_values],
        color="tab:blue",
        width=0.6,
        label="Used",
    )
    axes.set_xticks(list(positions))
    axes.set_xticklabels(task_names, rotation=90)
    axes.set_xlim(-0.7, len(task_usages) - 0.3)
    axes.set_ylabel(unit_label)
    axes.set_title(title)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output_file, dpi=150)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workflow_path", type=Path, help="Installed workflow (cylc-run/<name>/<run>)")
    parser.add_argument("output_path", type=Path, help="Directory to write the plots to")
    arguments = parser.parse_args()

    task_usages = collect_task_usage(arguments.workflow_path)
    if not task_usages:
        raise SystemExit("No PBS resource summaries found in the workflow's job logs.")

    arguments.output_path.mkdir(parents=True, exist_ok=True)
    plots = [
        ("walltime_hours", "Walltime", "Walltime (hours)", "walltime.png"),
        ("memory_gb", "Memory", "Memory (GB)", "memory.png"),
        ("jobfs_gb", "JobFS", "JobFS (GB)", "jobfs.png"),
    ]
    for resource_attribute, title, unit_label, file_name in plots:
        plot_resource(
            task_usages,
            resource_attribute,
            f"{title} usage per task",
            unit_label,
            arguments.output_path / file_name,
        )
    print(f"Plotted {len(task_usages)} tasks to {arguments.output_path}")


if __name__ == "__main__":
    main()
