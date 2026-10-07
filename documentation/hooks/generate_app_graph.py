"""Insert a Mermaid dependency graph of the suite's apps into the Apps landing page.

The `<!-- app-graph -->` placeholder in `pages/apps/index.md` is replaced at build time with a
graph generated from the `[[graph]]` section of the repository's `flow.cylc`. The file is parsed
directly (the Jinja2 is not rendered), so apps which are only included under an `{% if %}` are
drawn inside a dashed box labelled with the condition. Every app with an `app/<name>/README.md`
is hyperlinked to its docs page. No Cylc or Rose installation is required.
"""
import re
from pathlib import Path

LANDING_PAGE_SOURCE = "pages/apps/index.md"
PLACEHOLDER = "<!-- app-graph -->"

JINJA_BLOCK = re.compile(r"\{%-?\s*(if|elif|else|endif)\b\s*(.*?)\s*-?%\}")
TASK_NAME = re.compile(r"[A-Za-z_]\w*")

def extract_graph_lines(flow_text):
    """Return the lines between the triple quotes of the first `[[graph]]` section."""
    after_graph_header = flow_text.split("[[graph]]", 1)[1]
    return after_graph_header.split('"""')[1].splitlines()


def format_condition(keyword, expression):
    """Human readable label for one branch of an if/elif/else."""
    if keyword == "else":
        return "otherwise"
    comparison = re.fullmatch(r'(\w+)\s*==\s*"([^"]*)"', expression)
    if comparison:
        return f"{comparison.group(1)} = {comparison.group(2)}"
    return f"{expression} = true"


def parse_conditional_edges(graph_lines):
    """Parse graph lines into (upstream, downstream, condition_path) edges and the condition path of each mention of a task.

    A condition path is the tuple of branch labels which must hold for the line to be included.
    """
    edges = []
    mentions = []
    # Label of the active branch of each open `if`
    open_blocks = []
    for line in graph_lines:
        block = JINJA_BLOCK.search(line)
        if block:
            keyword, expression = block.groups()
            if keyword == "if":
                open_blocks.append(format_condition(keyword, expression))
            elif keyword in ("elif", "else"):
                open_blocks[-1] = format_condition(keyword, expression)
            else:
                open_blocks.pop()
            continue
        if "{{" in line:
            continue
        condition_path = tuple(open_blocks)
        stages = [
            TASK_NAME.findall(stage.replace("&", " ")) for stage in line.split("=>")
        ]
        if len(stages) < 2 or any(not stage for stage in stages):
            continue
        for upstream_stage, downstream_stage in zip(stages, stages[1:]):
            edges.extend(
                (upstream, downstream, condition_path)
                for upstream in upstream_stage
                for downstream in downstream_stage
            )
        mentions.extend((task, condition_path) for stage in stages for task in stage)
    return edges, mentions


def common_prefix(paths):
    """Longest tuple prefix shared by every path (empty if there are none)."""
    shared = []
    for labels in zip(*paths):
        if len(set(labels)) != 1:
            break
        shared.append(labels[0])
    return tuple(shared)


def assign_task_conditions(mentions):
    """A task only belongs to a condition if every edge which mentions it is under that condition."""
    paths_by_task = {}
    for task, condition_path in mentions:
        paths_by_task.setdefault(task, []).append(condition_path)
    return {task: common_prefix(paths) for task, paths in paths_by_task.items()}


def build_condition_tree(task_conditions):
    """Nest tasks by condition path: {"tasks": [...], "children": {label: subtree}}."""
    tree = {"tasks": [], "children": {}}
    for task, condition_path in sorted(task_conditions.items()):
        node = tree
        for label in condition_path:
            node = node["children"].setdefault(label, {"tasks": [], "children": {}})
        node["tasks"].append(task)
    return tree


def render_tree(tree, indent, subgraph_ids):
    """Mermaid lines for the tasks and nested conditional subgraphs of a tree node."""
    lines = [f"{indent}{task}" for task in tree["tasks"]]
    for label, child in tree["children"].items():
        subgraph_id = f"condition_{len(subgraph_ids)}"
        subgraph_ids.append(subgraph_id)
        lines.append(f'{indent}subgraph {subgraph_id} ["{label}"]')
        lines.extend(render_tree(child, indent + "    ", subgraph_ids))
        lines.append(f"{indent}end")
    return lines


def render_mermaid_graph(edges, task_conditions, documented_apps):
    subgraph_ids = []
    node_lines = render_tree(build_condition_tree(task_conditions), "    ", subgraph_ids)
    unique_edges = sorted(set((upstream, downstream) for upstream, downstream, _ in edges))
    edge_lines = [f"    {upstream} --> {downstream}" for upstream, downstream in unique_edges]
    click_lines = [
        f'    click {task} "{task}/" "Documentation for {task}"'
        for task in sorted(task_conditions)
        if task in documented_apps
    ]
    undocumented = [task for task in sorted(task_conditions) if task not in documented_apps]
    style_lines = ["    classDef undocumented stroke-dasharray:2 2,color:#777"]
    if undocumented:
        style_lines.append(f"    class {','.join(undocumented)} undocumented")
    style_lines.extend(f"    style {subgraph_id} stroke-dasharray:6 4,fill:none" for subgraph_id in subgraph_ids)
    return "\n".join(
        ["flowchart LR", *node_lines, "", *edge_lines, "", *click_lines, "", *style_lines]
    )


def find_documented_apps(app_directory):
    return {readme.parent.name for readme in app_directory.glob("*/README.md")}


def generate_graph_block(flow_file, app_directory):
    edges, mentions = parse_conditional_edges(extract_graph_lines(flow_file.read_text()))
    graph = render_mermaid_graph(edges, assign_task_conditions(mentions), find_documented_apps(app_directory))
    return f"```mermaid\n{graph}\n```"


def on_page_markdown(markdown, *, page, config, files):
    if page.file.src_uri != LANDING_PAGE_SOURCE:
        return markdown
    repository_root = Path(config.config_file_path).resolve().parents[1]
    graph_block = generate_graph_block(repository_root / "flow.cylc", repository_root / "app")
    return markdown.replace(PLACEHOLDER, graph_block)
