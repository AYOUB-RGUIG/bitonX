"""Annotation parsers for supported floor-plan datasets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
import pickle
import re
import xml.etree.ElementTree as ET

from bitonx_ai.datasets.models import (
    AnnotationKind,
    GraphEdgeAnnotation,
    GraphNodeAnnotation,
    JsonPrimitive,
    JsonValue,
    ParsedAnnotations,
    PlanAnnotation,
    PlanGraph,
    Point2D,
)
from bitonx_ai.datasets.taxonomy import (
    cubicasa_category_from_group,
    normalize_label,
    resplan_category_from_key,
)

AffineMatrix = tuple[float, float, float, float, float, float]
GeometryPart = tuple[AnnotationKind, tuple[Point2D, ...]]


class DatasetParserError(ValueError):
    """Raised when a dataset annotation file cannot be parsed."""


@dataclass(frozen=True, slots=True)
class AnnotationParser:
    """Base annotation parser contract."""

    parser_name: str

    def parse(
        self,
        annotation_path: Path,
        *,
        sample_id: str | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ParsedAnnotations:
        """Parse an annotation file."""
        raise NotImplementedError


class CubiCasaSvgAnnotationParser(AnnotationParser):
    """Parse CubiCasa5K `model.svg` annotation files."""

    def __init__(self) -> None:
        super().__init__(parser_name="cubicasa_svg")

    def parse(
        self,
        annotation_path: Path,
        *,
        sample_id: str | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ParsedAnnotations:
        """Parse a CubiCasa5K SVG into unified annotations."""
        path = Path(annotation_path)
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise DatasetParserError(f"Invalid CubiCasa SVG: {path}") from exc

        root = tree.getroot()
        annotations: list[PlanAnnotation] = []
        sample_key = sample_id or path.parent.name
        parser_metadata: dict[str, JsonValue] = {
            "annotationFormat": "cubicasa_svg",
            "sourceFile": str(path),
        }
        parser_metadata.update(metadata or {})

        width, height = _svg_dimensions(root)
        if width is not None:
            parser_metadata["svgWidth"] = width
        if height is not None:
            parser_metadata["svgHeight"] = height

        def walk(element: ET.Element, parent_matrix: AffineMatrix) -> None:
            element_matrix = _matrix_multiply(
                parent_matrix,
                _parse_svg_transform(element.attrib.get("transform", "")),
            )
            if _strip_namespace(element.tag) == "g":
                group_id = element.attrib.get("id")
                class_name = element.attrib.get("class")
                if _is_cubicasa_annotation_group(group_id, class_name):
                    source_label = _cubicasa_source_label(group_id, class_name)
                    category = cubicasa_category_from_group(group_id, class_name)
                    parts = _collect_svg_geometry_parts(element, element_matrix)
                    for part_index, (kind, points) in enumerate(parts):
                        if kind == AnnotationKind.POLYGON and len(points) < 3:
                            continue
                        annotation_id = _stable_id(sample_key, source_label, part_index, points)
                        annotations.append(
                            PlanAnnotation(
                                annotation_id=annotation_id,
                                category=category,
                                source_label=source_label,
                                kind=kind,
                                points=points,
                                metadata={
                                    "parser": self.parser_name,
                                    "svgGroupId": group_id,
                                    "svgClass": class_name,
                                    "partIndex": part_index,
                                },
                            )
                        )
            for child in element:
                walk(child, element_matrix)

        walk(root, _identity_matrix())
        return ParsedAnnotations(
            annotations=tuple(annotations),
            metadata=parser_metadata,
            canvas_width=width,
            canvas_height=height,
        )


class ResPlanAnnotationParser(AnnotationParser):
    """Parse ResPlan vector-geometry records."""

    metadata_keys: frozenset[str] = frozenset(
        {
            "area",
            "bedroom_count",
            "bedrooms",
            "gfa",
            "planid",
            "plan_id",
            "planID",
            "source",
            "unit",
            "unitType",
            "unit_type",
            "wall_depth",
        }
    )

    non_geometry_keys: frozenset[str] = frozenset(
        {
            "graph",
            "image",
            "image_path",
            "metadata",
            "name",
            "planid",
            "plan_id",
            "planID",
            "split",
            "unitType",
            "unit_type",
        }
    )

    def __init__(self) -> None:
        super().__init__(parser_name="resplan_vector")

    def parse(
        self,
        annotation_path: Path,
        *,
        sample_id: str | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ParsedAnnotations:
        """Parse a file containing a single ResPlan record."""
        path = Path(annotation_path)
        record = _load_single_record(path)
        return self.parse_record(record, sample_id=sample_id, source_path=path, metadata=metadata)

    def parse_record(
        self,
        record: Mapping[str, object],
        *,
        sample_id: str | None = None,
        source_path: Path | None = None,
        record_key: str | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ParsedAnnotations:
        """Parse an in-memory ResPlan plan dictionary."""
        if not isinstance(record, Mapping):
            raise DatasetParserError("ResPlan records must be mapping-like objects.")

        sample_key = sample_id or _resplan_record_id(record, record_key) or "resplan_sample"
        annotations: list[PlanAnnotation] = []
        parser_metadata: dict[str, JsonValue] = {
            "annotationFormat": "resplan_vector",
            "metricCoordinates": True,
        }
        if source_path is not None:
            parser_metadata["sourceFile"] = str(source_path)
        if record_key is not None:
            parser_metadata["recordKey"] = record_key
        parser_metadata.update(_resplan_record_metadata(record))
        parser_metadata.update(metadata or {})

        for key, value in record.items():
            normalized_key = normalize_label(str(key))
            if normalized_key in self.non_geometry_keys:
                continue
            parts = _extract_geometry_parts(value)
            if not parts:
                continue
            category = resplan_category_from_key(str(key))
            for part_index, (kind, points) in enumerate(parts):
                if kind == AnnotationKind.POLYGON and len(points) < 3:
                    continue
                annotation_id = _stable_id(sample_key, key, part_index, points)
                annotations.append(
                    PlanAnnotation(
                        annotation_id=annotation_id,
                        category=category,
                        source_label=str(key),
                        kind=kind,
                        points=points,
                        metadata={
                            "parser": self.parser_name,
                            "recordKey": record_key,
                            "geometryKey": str(key),
                            "partIndex": part_index,
                        },
                    )
                )

        graph = _extract_resplan_graph(record.get("graph"))
        return ParsedAnnotations(
            annotations=tuple(annotations),
            graph=graph,
            metadata=parser_metadata,
        )


def _stable_id(*parts: object) -> str:
    import hashlib

    digest = hashlib.sha256()
    for part in parts:
        digest.update(repr(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:24]


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _identity_matrix() -> AffineMatrix:
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _matrix_multiply(parent: AffineMatrix, child: AffineMatrix) -> AffineMatrix:
    pa, pb, pc, pd, pe, pf = parent
    ca, cb, cc, cd, ce, cf = child
    return (
        pa * ca + pc * cb,
        pb * ca + pd * cb,
        pa * cc + pc * cd,
        pb * cc + pd * cd,
        pa * ce + pc * cf + pe,
        pb * ce + pd * cf + pf,
    )


def _apply_matrix(point: Point2D, matrix: AffineMatrix) -> Point2D:
    a, b, c, d, e, f = matrix
    return Point2D(a * point.x + c * point.y + e, b * point.x + d * point.y + f)


def _parse_svg_transform(transform: str) -> AffineMatrix:
    matrix = _identity_matrix()
    if not transform:
        return matrix

    for match in re.finditer(r"([a-zA-Z]+)\s*\(([^)]*)\)", transform):
        name = match.group(1).lower()
        values = _parse_floats(match.group(2))
        current = _identity_matrix()
        if name == "matrix" and len(values) >= 6:
            current = tuple(values[:6])  # type: ignore[assignment]
        elif name == "translate" and values:
            tx = values[0]
            ty = values[1] if len(values) > 1 else 0.0
            current = (1.0, 0.0, 0.0, 1.0, tx, ty)
        elif name == "scale" and values:
            sx = values[0]
            sy = values[1] if len(values) > 1 else sx
            current = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "rotate" and values:
            angle = math.radians(values[0])
            cos_value = math.cos(angle)
            sin_value = math.sin(angle)
            rotation: AffineMatrix = (cos_value, sin_value, -sin_value, cos_value, 0.0, 0.0)
            if len(values) >= 3:
                cx, cy = values[1], values[2]
                to_origin: AffineMatrix = (1.0, 0.0, 0.0, 1.0, -cx, -cy)
                back: AffineMatrix = (1.0, 0.0, 0.0, 1.0, cx, cy)
                current = _matrix_multiply(back, _matrix_multiply(rotation, to_origin))
            else:
                current = rotation
        matrix = _matrix_multiply(matrix, current)
    return matrix


def _parse_floats(text: str) -> list[float]:
    return [float(match.group(0)) for match in re.finditer(r"[-+]?(?:\d*\.\d+|\d+)(?:e[-+]?\d+)?", text, re.I)]


def _svg_dimensions(root: ET.Element) -> tuple[float | None, float | None]:
    width = _svg_length(root.attrib.get("width"))
    height = _svg_length(root.attrib.get("height"))
    if width is not None and height is not None:
        return width, height
    view_box = root.attrib.get("viewBox")
    if view_box:
        values = _parse_floats(view_box)
        if len(values) >= 4:
            return values[2], values[3]
    return width, height


def _svg_length(value: str | None) -> float | None:
    if value is None:
        return None
    values = _parse_floats(value)
    return values[0] if values else None


def _is_cubicasa_annotation_group(group_id: str | None, class_name: str | None) -> bool:
    if group_id in {"Wall", "Railing", "Door", "Window"}:
        return True
    if not class_name:
        return False
    tokens = class_name.split()
    return "Space" in tokens or "FixedFurniture" in tokens


def _cubicasa_source_label(group_id: str | None, class_name: str | None) -> str:
    if group_id in {"Wall", "Railing", "Door", "Window"}:
        return group_id
    if not class_name:
        return "Unknown"
    tokens = class_name.split()
    for marker in ("Space", "FixedFurniture"):
        if marker in tokens:
            index = tokens.index(marker)
            if len(tokens) > index + 1:
                return tokens[index + 1]
    return class_name


def _collect_svg_geometry_parts(
    element: ET.Element,
    parent_matrix: AffineMatrix,
) -> tuple[GeometryPart, ...]:
    parts: list[GeometryPart] = []
    for child in element:
        child_matrix = _matrix_multiply(
            parent_matrix,
            _parse_svg_transform(child.attrib.get("transform", "")),
        )
        tag = _strip_namespace(child.tag)
        if tag == "polygon":
            points = _parse_svg_points(child.attrib.get("points", ""))
            if points:
                parts.append((AnnotationKind.POLYGON, tuple(_apply_matrix(p, child_matrix) for p in points)))
        elif tag == "polyline":
            points = _parse_svg_points(child.attrib.get("points", ""))
            if points:
                parts.append((AnnotationKind.POLYLINE, tuple(_apply_matrix(p, child_matrix) for p in points)))
        elif tag == "rect":
            rect_points = _parse_svg_rect(child)
            if rect_points:
                parts.append(
                    (
                        AnnotationKind.POLYGON,
                        tuple(_apply_matrix(p, child_matrix) for p in rect_points),
                    )
                )
        elif tag == "path":
            path_points = _parse_simple_svg_path(child.attrib.get("d", ""))
            if len(path_points) >= 3:
                parts.append(
                    (
                        AnnotationKind.POLYGON,
                        tuple(_apply_matrix(p, child_matrix) for p in path_points),
                    )
                )
        else:
            parts.extend(_collect_svg_geometry_parts(child, child_matrix))
    return tuple(parts)


def _parse_svg_points(points: str) -> tuple[Point2D, ...]:
    values = _parse_floats(points)
    if len(values) < 4:
        return ()
    pair_count = len(values) // 2
    return tuple(Point2D(values[index * 2], values[index * 2 + 1]) for index in range(pair_count))


def _parse_svg_rect(element: ET.Element) -> tuple[Point2D, ...]:
    x = _svg_length(element.attrib.get("x")) or 0.0
    y = _svg_length(element.attrib.get("y")) or 0.0
    width = _svg_length(element.attrib.get("width"))
    height = _svg_length(element.attrib.get("height"))
    if width is None or height is None:
        return ()
    return (
        Point2D(x, y),
        Point2D(x + width, y),
        Point2D(x + width, y + height),
        Point2D(x, y + height),
    )


def _parse_simple_svg_path(path_data: str) -> tuple[Point2D, ...]:
    values = _parse_floats(path_data)
    if len(values) < 4:
        return ()
    pair_count = len(values) // 2
    return tuple(Point2D(values[index * 2], values[index * 2 + 1]) for index in range(pair_count))


def _load_single_record(path: Path) -> Mapping[str, object]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    elif suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            first_line = next((line for line in handle if line.strip()), "")
        data = json.loads(first_line) if first_line else {}
    elif suffix in {".pkl", ".pickle"}:
        with path.open("rb") as handle:
            data = pickle.load(handle)
    else:
        raise DatasetParserError(f"Unsupported annotation file format: {path}")

    if isinstance(data, Mapping):
        return data
    if isinstance(data, list) and data and isinstance(data[0], Mapping):
        return data[0]
    raise DatasetParserError(f"Expected a single mapping-like record in {path}")


def _resplan_record_id(record: Mapping[str, object], record_key: str | None) -> str | None:
    for key in ("planID", "plan_id", "id", "name"):
        value = record.get(key)
        if value is not None:
            return str(value)
    return record_key


def _resplan_record_metadata(record: Mapping[str, object]) -> dict[str, JsonValue]:
    metadata: dict[str, JsonValue] = {}
    for key, value in record.items():
        normalized_key = normalize_label(str(key))
        if key in ResPlanAnnotationParser.metadata_keys or normalized_key in {
            normalize_label(item) for item in ResPlanAnnotationParser.metadata_keys
        }:
            json_value = _to_json_value(value)
            if json_value is not None:
                metadata[str(key)] = json_value
    nested_metadata = record.get("metadata")
    if isinstance(nested_metadata, Mapping):
        for key, value in nested_metadata.items():
            json_value = _to_json_value(value)
            if json_value is not None:
                metadata[str(key)] = json_value
    return metadata


def _to_json_value(value: object) -> JsonValue | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        converted: dict[str, JsonValue] = {}
        for key, item in value.items():
            json_value = _to_json_value(item)
            if json_value is not None:
                converted[str(key)] = json_value
        return converted
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        converted_list: list[JsonValue] = []
        for item in value:
            json_value = _to_json_value(item)
            if json_value is not None:
                converted_list.append(json_value)
        return converted_list
    return None


def _extract_geometry_parts(value: object) -> tuple[GeometryPart, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return _extract_wkt_parts(value)
    if isinstance(value, Mapping):
        return _extract_geojson_parts(value)
    shapely_parts = _extract_shapely_like_parts(value)
    if shapely_parts:
        return shapely_parts
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return _extract_coordinate_sequence_parts(value)
    return ()


def _extract_shapely_like_parts(value: object) -> tuple[GeometryPart, ...]:
    if not hasattr(value, "geom_type"):
        return ()
    if bool(getattr(value, "is_empty", False)):
        return ()

    geom_type = str(getattr(value, "geom_type"))
    if geom_type == "Polygon" and hasattr(value, "exterior"):
        coords = getattr(getattr(value, "exterior"), "coords")
        points = _points_from_coordinate_pairs(coords)
        return ((AnnotationKind.POLYGON, points),) if points else ()
    if geom_type == "MultiPolygon" and hasattr(value, "geoms"):
        parts: list[GeometryPart] = []
        for geom in getattr(value, "geoms"):
            parts.extend(_extract_shapely_like_parts(geom))
        return tuple(parts)
    if geom_type in {"LineString", "LinearRing"} and hasattr(value, "coords"):
        points = _points_from_coordinate_pairs(getattr(value, "coords"))
        return ((AnnotationKind.POLYLINE, points),) if points else ()
    if geom_type == "MultiLineString" and hasattr(value, "geoms"):
        parts = []
        for geom in getattr(value, "geoms"):
            parts.extend(_extract_shapely_like_parts(geom))
        return tuple(parts)
    if geom_type == "Point" and hasattr(value, "x") and hasattr(value, "y"):
        return ((AnnotationKind.POINT, (Point2D(float(value.x), float(value.y)),)),)
    return ()


def _extract_wkt_parts(value: str) -> tuple[GeometryPart, ...]:
    text = value.strip()
    if not text or "EMPTY" in text.upper():
        return ()
    upper = text.upper()
    if upper.startswith("POLYGON"):
        match = re.search(r"\(\((.*)\)\)", text)
        if not match:
            return ()
        first_ring = re.split(r"\)\s*,\s*\(", match.group(1), maxsplit=1)[0]
        points = _parse_wkt_coordinate_text(first_ring)
        return ((AnnotationKind.POLYGON, points),) if points else ()
    if upper.startswith("MULTIPOLYGON"):
        parts: list[GeometryPart] = []
        for match in re.finditer(r"\(\(\s*([^()]+?)\s*\)\)", text):
            points = _parse_wkt_coordinate_text(match.group(1))
            if points:
                parts.append((AnnotationKind.POLYGON, points))
        return tuple(parts)
    if upper.startswith("LINESTRING"):
        match = re.search(r"\((.*)\)", text)
        points = _parse_wkt_coordinate_text(match.group(1)) if match else ()
        return ((AnnotationKind.POLYLINE, points),) if points else ()
    if upper.startswith("POINT"):
        values = _parse_floats(text)
        if len(values) >= 2:
            return ((AnnotationKind.POINT, (Point2D(values[0], values[1]),)),)
    return ()


def _parse_wkt_coordinate_text(text: str) -> tuple[Point2D, ...]:
    pairs: list[Point2D] = []
    for chunk in text.split(","):
        values = _parse_floats(chunk)
        if len(values) >= 2:
            pairs.append(Point2D(values[0], values[1]))
    return tuple(pairs)


def _extract_geojson_parts(value: Mapping[str, object]) -> tuple[GeometryPart, ...]:
    geom_type = value.get("type")
    coordinates = value.get("coordinates")
    if not isinstance(geom_type, str):
        return ()
    normalized = geom_type.lower()
    if normalized == "polygon":
        if isinstance(coordinates, Iterable):
            rings = list(coordinates)
            if rings:
                points = _points_from_coordinate_pairs(rings[0])
                return ((AnnotationKind.POLYGON, points),) if points else ()
    if normalized == "multipolygon":
        parts: list[GeometryPart] = []
        if isinstance(coordinates, Iterable):
            for polygon in coordinates:
                if isinstance(polygon, Iterable):
                    rings = list(polygon)
                    if rings:
                        points = _points_from_coordinate_pairs(rings[0])
                        if points:
                            parts.append((AnnotationKind.POLYGON, points))
        return tuple(parts)
    if normalized == "linestring":
        points = _points_from_coordinate_pairs(coordinates)
        return ((AnnotationKind.POLYLINE, points),) if points else ()
    if normalized == "point" and isinstance(coordinates, Iterable):
        values = list(coordinates)
        if len(values) >= 2 and _is_number(values[0]) and _is_number(values[1]):
            return ((AnnotationKind.POINT, (Point2D(float(values[0]), float(values[1])),)),)
    return ()


def _extract_coordinate_sequence_parts(value: object) -> tuple[GeometryPart, ...]:
    items = list(value) if isinstance(value, Iterable) else []
    if not items:
        return ()
    if _looks_like_point(items):
        return ((AnnotationKind.POINT, (Point2D(float(items[0]), float(items[1])),)),)
    if all(_looks_like_point(item) for item in items):
        points = _points_from_coordinate_pairs(items)
        return ((AnnotationKind.POLYGON, points),) if points else ()
    parts: list[GeometryPart] = []
    for item in items:
        parts.extend(_extract_coordinate_sequence_parts(item))
    return tuple(parts)


def _points_from_coordinate_pairs(value: object) -> tuple[Point2D, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, bytearray)):
        return ()
    points: list[Point2D] = []
    for item in value:
        if _looks_like_point(item):
            point = list(item)  # type: ignore[arg-type]
            points.append(Point2D(float(point[0]), float(point[1])))
    return tuple(points)


def _looks_like_point(value: object) -> bool:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, bytearray)):
        return False
    items = list(value)
    return len(items) >= 2 and _is_number(items[0]) and _is_number(items[1])


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_resplan_graph(value: object) -> PlanGraph | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _extract_mapping_graph(value)
    if hasattr(value, "nodes") and hasattr(value, "edges"):
        return _extract_networkx_like_graph(value)
    return None


def _extract_mapping_graph(value: Mapping[str, object]) -> PlanGraph:
    raw_nodes = value.get("nodes", [])
    raw_edges = value.get("edges", [])
    nodes = _extract_mapping_nodes(raw_nodes)
    edges = _extract_mapping_edges(raw_edges)
    return PlanGraph(nodes=nodes, edges=edges)


def _extract_mapping_nodes(raw_nodes: object) -> tuple[GraphNodeAnnotation, ...]:
    nodes: list[GraphNodeAnnotation] = []
    if isinstance(raw_nodes, Mapping):
        iterable = raw_nodes.items()
    elif isinstance(raw_nodes, Iterable) and not isinstance(raw_nodes, (str, bytes, bytearray)):
        iterable = enumerate(raw_nodes)
    else:
        return ()
    for fallback_id, raw_node in iterable:
        if isinstance(raw_node, Mapping):
            node_id = str(raw_node.get("id") or raw_node.get("node_id") or fallback_id)
            category = str(raw_node.get("type") or raw_node.get("category") or "room")
            centroid = _extract_centroid(raw_node)
            metadata = _primitive_mapping(raw_node, exclude={"id", "node_id", "type", "category"})
        else:
            node_id = str(fallback_id)
            category = "room"
            centroid = None
            metadata = {}
        nodes.append(
            GraphNodeAnnotation(
                node_id=node_id,
                category=category,
                centroid=centroid,
                metadata=metadata,
            )
        )
    return tuple(nodes)


def _extract_mapping_edges(raw_edges: object) -> tuple[GraphEdgeAnnotation, ...]:
    edges: list[GraphEdgeAnnotation] = []
    if not isinstance(raw_edges, Iterable) or isinstance(raw_edges, (str, bytes, bytearray)):
        return ()
    for index, raw_edge in enumerate(raw_edges):
        if isinstance(raw_edge, Mapping):
            source = raw_edge.get("source") or raw_edge.get("u") or raw_edge.get("source_node_id")
            target = raw_edge.get("target") or raw_edge.get("v") or raw_edge.get("target_node_id")
            if source is None or target is None:
                continue
            relationship = str(raw_edge.get("type") or raw_edge.get("relationship") or "adjacency")
            edge_id = str(raw_edge.get("id") or raw_edge.get("edge_id") or f"edge_{index}")
            metadata = _primitive_mapping(
                raw_edge,
                exclude={"id", "edge_id", "source", "target", "u", "v", "type", "relationship"},
            )
        elif isinstance(raw_edge, Iterable) and not isinstance(raw_edge, (str, bytes, bytearray)):
            values = list(raw_edge)
            if len(values) < 2:
                continue
            source = values[0]
            target = values[1]
            relationship = str(values[2]) if len(values) > 2 else "adjacency"
            edge_id = f"edge_{index}"
            metadata = {}
        else:
            continue
        edges.append(
            GraphEdgeAnnotation(
                edge_id=edge_id,
                source_node_id=str(source),
                target_node_id=str(target),
                relationship=relationship,
                metadata=metadata,
            )
        )
    return tuple(edges)


def _extract_networkx_like_graph(value: object) -> PlanGraph:
    nodes: list[GraphNodeAnnotation] = []
    edges: list[GraphEdgeAnnotation] = []
    try:
        node_iterable = value.nodes(data=True)  # type: ignore[union-attr]
        edge_iterable = value.edges(data=True)  # type: ignore[union-attr]
    except TypeError:
        return PlanGraph()

    for node_id, data in node_iterable:
        node_data = data if isinstance(data, Mapping) else {}
        category = str(node_data.get("type") or node_data.get("category") or "room")
        nodes.append(
            GraphNodeAnnotation(
                node_id=str(node_id),
                category=category,
                centroid=_extract_centroid(node_data),
                metadata=_primitive_mapping(node_data, exclude={"type", "category", "geometry"}),
            )
        )
    for index, (source, target, data) in enumerate(edge_iterable):
        edge_data = data if isinstance(data, Mapping) else {}
        edges.append(
            GraphEdgeAnnotation(
                edge_id=str(edge_data.get("id") or f"edge_{index}"),
                source_node_id=str(source),
                target_node_id=str(target),
                relationship=str(edge_data.get("type") or edge_data.get("relationship") or "adjacency"),
                metadata=_primitive_mapping(edge_data, exclude={"id", "type", "relationship"}),
            )
        )
    return PlanGraph(nodes=tuple(nodes), edges=tuple(edges))


def _extract_centroid(data: Mapping[str, object]) -> Point2D | None:
    centroid = data.get("centroid")
    if _looks_like_point(centroid):
        values = list(centroid)  # type: ignore[arg-type]
        return Point2D(float(values[0]), float(values[1]))
    geometry = data.get("geometry")
    if geometry is not None and hasattr(geometry, "centroid"):
        center = getattr(geometry, "centroid")
        if hasattr(center, "x") and hasattr(center, "y"):
            return Point2D(float(center.x), float(center.y))
    return None


def _primitive_mapping(
    data: Mapping[str, object],
    *,
    exclude: set[str] | None = None,
) -> dict[str, JsonPrimitive]:
    excluded = exclude or set()
    metadata: dict[str, JsonPrimitive] = {}
    for key, value in data.items():
        if str(key) in excluded:
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            metadata[str(key)] = value
    return metadata
