"""HTML rendering utilities using Jinja2."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from ..core.plugin_base import DiffResult

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    """Get a configured Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )


def render_html_report(
    template_name: str,
    result: DiffResult,
    extra_context: Optional[dict] = None,
) -> str:
    """Render an HTML report using a Jinja2 template.

    Args:
        template_name: Name of the template file (e.g., "image_report.html.j2")
        result: The DiffResult to render
        extra_context: Additional template context variables

    Returns:
        Rendered HTML string
    """
    env = get_jinja_env()
    template = env.get_template(template_name)

    context = {
        "result": result,
        "similarity_percent": f"{result.similarity:.1%}",
        "changed": result.changed,
        "summary": result.summary,
    }

    if extra_context:
        context.update(extra_context)

    return template.render(**context)


def save_html_report(
    html_content: str,
    output_path: Path,
    title: str = "polydiff Report",
) -> None:
    """Save an HTML report to a file with a complete HTML wrapper."""
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .summary {{
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .identical {{ background: #d4edda; color: #155724; }}
        .minor-changes {{ background: #fff3cd; color: #856404; }}
        .major-changes {{ background: #f8d7da; color: #721c24; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }}
        th, td {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            text-align: left;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .changed {{ background: #fff3cd; }}
        .added {{ background: #d4edda; }}
        .removed {{ background: #f8d7da; text-decoration: line-through; }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        .side-by-side {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .side-by-side > div {{
            flex: 1;
            min-width: 300px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_html)
