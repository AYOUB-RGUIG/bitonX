"""Dataset visualization helpers for parsed annotations."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
from pathlib import Path

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import AnnotationKind, DatasetSample, PlanAnnotation

CATEGORY_COLORS: dict[str, str] = {
    "wall": "#2f2f2f",
    "railing": "#5b6770",
    "door": "#c2410c",
    "front_door": "#9a3412",
    "window": "#0369a1",
    "opening": "#0e7490",
    "living": "#65a30d",
    "bedroom": "#16a34a",
    "bathroom": "#0284c7",
    "kitchen": "#ca8a04",
    "dining": "#a16207",
    "hallway": "#7c3aed",
    "entry": "#9333ea",
    "storage": "#64748b",
    "garage": "#475569",
    "balcony": "#0f766e",
    "outdoor": "#15803d",
    "stair": "#db2777",
    "plumbing": "#0891b2",
    "electrical": "#f59e0b",
    "fixture": "#78716c",
    "furniture": "#854d0e",
    "unknown": "#6b7280",
}


class DatasetVisualizer:
    """Render parsed annotations as SVG or a compact HTML preview."""

    def render_sample_svg(
        self,
        sample: DatasetSample,
        *,
        include_image: bool = True,
        show_labels: bool = False,
    ) -> str:
        """Render one sample as an SVG overlay."""
        min_x, min_y, width, height = _sample_viewbox(sample)
        svg_parts = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="{min_x:g} {min_y:g} {width:g} {height:g}" '
                f'role="img" aria-label="{escape(sample.sample_id)} annotations">'
            )
        ]
        if include_image and sample.image_path is not None and sample.image_path.exists():
            href = escape(sample.image_path.resolve().as_uri())
            svg_parts.append(
                f'<image href="{href}" x="0" y="0" width="{width:g}" height="{height:g}" '
                'preserveAspectRatio="none" opacity="0.55" />'
            )
        svg_parts.extend(_render_annotation(annotation, show_labels=show_labels) for annotation in sample.annotations)
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def write_sample_svg(
        self,
        sample: DatasetSample,
        path: str | Path,
        *,
        include_image: bool = True,
        show_labels: bool = False,
    ) -> Path:
        """Write one sample SVG overlay."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.render_sample_svg(sample, include_image=include_image, show_labels=show_labels),
            encoding="utf-8",
        )
        return output_path

    def write_dataset_preview_html(
        self,
        dataset: FloorplanDataset,
        path: str | Path,
        *,
        limit: int = 24,
        include_images: bool = False,
    ) -> Path:
        """Write a static HTML preview grid for a dataset."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        samples = list(dataset[:limit])
        body = "\n".join(
            (
                '<section class="sample">'
                f"<h2>{escape(sample.sample_id)}</h2>"
                f"{self.render_sample_svg(sample, include_image=include_images, show_labels=False)}"
                "</section>"
            )
            for sample in samples
        )
        output_path.write_text(
            _preview_html(dataset.name, body),
            encoding="utf-8",
        )
        return output_path


def _render_annotation(annotation: PlanAnnotation, *, show_labels: bool) -> str:
    color = CATEGORY_COLORS.get(annotation.category, CATEGORY_COLORS["unknown"])
    if annotation.kind == AnnotationKind.POINT and annotation.points:
        point = annotation.points[0]
        return (
            f'<circle cx="{point.x:g}" cy="{point.y:g}" r="3" '
            f'fill="{color}" stroke="#111827" stroke-width="1" />'
        )
    if annotation.kind == AnnotationKind.POLYLINE:
        points = _svg_points(annotation)
        return (
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
        )
    if annotation.kind == AnnotationKind.POLYGON:
        points = _svg_points(annotation)
        label = _label_element(annotation) if show_labels else ""
        return (
            f'<polygon points="{points}" fill="{color}" fill-opacity="0.24" '
            f'stroke="{color}" stroke-width="1.5" />{label}'
        )
    bbox = annotation.resolved_bbox
    return (
        f'<rect x="{bbox.x:g}" y="{bbox.y:g}" width="{bbox.width:g}" height="{bbox.height:g}" '
        f'fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="1.5" />'
    )


def _svg_points(annotation: PlanAnnotation) -> str:
    return " ".join(f"{point.x:g},{point.y:g}" for point in annotation.points)


def _label_element(annotation: PlanAnnotation) -> str:
    bbox = annotation.resolved_bbox
    label = escape(annotation.category)
    return (
        f'<text x="{bbox.x:g}" y="{bbox.y:g}" font-size="10" '
        'font-family="Arial, sans-serif" fill="#111827">'
        f"{label}</text>"
    )


def _sample_viewbox(sample: DatasetSample) -> tuple[float, float, float, float]:
    if sample.image_metadata is not None:
        return 0.0, 0.0, float(sample.image_metadata.width), float(sample.image_metadata.height)
    boxes = [annotation.resolved_bbox for annotation in sample.annotations]
    if not boxes:
        return 0.0, 0.0, 512.0, 512.0
    min_x = min(box.x for box in boxes)
    min_y = min(box.y for box in boxes)
    max_x = max(box.x + box.width for box in boxes)
    max_y = max(box.y + box.height for box in boxes)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    return min_x, min_y, width, height


def _preview_html(dataset_name: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(dataset_name)} Preview</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #111827;
      background: #f8fafc;
    }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      padding: 16px;
    }}
    .sample {{
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 12px;
    }}
    h1, h2 {{
      font-size: 14px;
      margin: 0 0 10px;
      font-weight: 700;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
      background: #ffffff;
      border: 1px solid #e5e7eb;
    }}
  </style>
</head>
<body>
  <main aria-label="{escape(dataset_name)} dataset previews">
{body}
  </main>
</body>
</html>
"""
