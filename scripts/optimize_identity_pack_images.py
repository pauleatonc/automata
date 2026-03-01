#!/usr/bin/env python3
"""
Optimiza imagenes del identity pack para reducir payload en Replicate.

Uso recomendado (seguro, no pisa originales):
  python3 scripts/optimize_identity_pack_images.py

Luego, si quieres actualizar metadata para usar las optimizadas:
  python3 scripts/optimize_identity_pack_images.py --update-metadata

Modo agresivo (sobrescribe originales):
  python3 scripts/optimize_identity_pack_images.py --in-place --update-metadata
"""
import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from PIL import Image, ImageOps


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimiza imagenes del identity pack para bajar su peso."
    )
    parser.add_argument(
        "--identity-pack-dir",
        default="identity_pack",
        help="Directorio del identity pack (default: identity_pack)",
    )
    parser.add_argument(
        "--metadata-file",
        default="identity_metadata.json",
        help="Nombre del metadata dentro del identity pack (default: identity_metadata.json)",
    )
    parser.add_argument(
        "--output-subdir",
        default="optimized",
        help="Subcarpeta de salida para imagenes optimizadas (default: optimized)",
    )
    parser.add_argument(
        "--max-dim",
        type=int,
        default=1280,
        help="Dimension maxima (ancho/alto) para resize proporcional (default: 1280)",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=88,
        help="Calidad JPEG (1-95, default: 88)",
    )
    parser.add_argument(
        "--png-compress-level",
        type=int,
        default=9,
        help="Nivel de compresion PNG (0-9, default: 9)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescribe archivos originales en lugar de escribir en output-subdir",
    )
    parser.add_argument(
        "--update-metadata",
        action="store_true",
        help="Actualiza identity_metadata.json con los nuevos archivos",
    )
    parser.add_argument(
        "--all-images",
        action="store_true",
        help="Procesa todas las imagenes en identity_pack (si no, solo las referenciadas en metadata)",
    )
    parser.add_argument(
        "--estimate-max-total-input-mb",
        type=float,
        default=None,
        help="Presupuesto MB para recomendar max_reference_images (si no, usa metadata o 18MB)",
    )
    return parser.parse_args()


def load_metadata(metadata_path: Path) -> Dict[str, Any]:
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(metadata_path: Path, metadata: Dict[str, Any]) -> None:
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def collect_source_images(identity_dir: Path, metadata: Dict[str, Any], all_images: bool) -> List[str]:
    if all_images:
        files = []
        for path in identity_dir.iterdir():
            if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
                files.append(path.name)
        return sorted(files)

    assets = metadata.get("assets", {}) or {}
    refs = assets.get("reference_images", None)
    if refs is None:
        refs = metadata.get("reference_images", [])
    refs = refs or []
    return [str(name) for name in refs]


def _target_output_path(
    source_name: str,
    identity_dir: Path,
    output_dir: Path,
    in_place: bool,
) -> Path:
    source_path = identity_dir / source_name
    if in_place:
        return source_path

    stem = source_path.stem
    # Convertir a JPG cuando no hay alpha reduce mucho el peso.
    # El formato final se decide al guardar; aca dejamos extension temporal.
    return output_dir / f"{stem}.jpg"


def optimize_one_image(
    source_path: Path,
    output_path_hint: Path,
    max_dim: int,
    jpeg_quality: int,
    png_compress_level: int,
    in_place: bool,
) -> Tuple[Path, int, int]:
    original_size = source_path.stat().st_size
    with Image.open(source_path) as img:
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        scale = min(1.0, float(max_dim) / max(width, height))
        if scale < 1.0:
            new_size = (int(width * scale), int(height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )

        # Si no hay alpha, usar JPG para bajar peso.
        if not has_alpha:
            out_path = output_path_hint.with_suffix(".jpg")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            img = img.convert("RGB")
            img.save(
                out_path,
                format="JPEG",
                quality=jpeg_quality,
                optimize=True,
                progressive=True,
            )
        else:
            # Mantener PNG cuando hay transparencia.
            out_path = output_path_hint.with_suffix(".png")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if img.mode not in ("RGBA", "LA"):
                img = img.convert("RGBA")
            img.save(
                out_path,
                format="PNG",
                optimize=True,
                compress_level=png_compress_level,
            )

    optimized_size = out_path.stat().st_size
    if in_place and out_path != source_path and source_path.exists():
        source_path.unlink()
    return out_path, original_size, optimized_size


def deep_replace_paths(obj: Any, mapping: Dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {k: deep_replace_paths(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_replace_paths(v, mapping) for v in obj]
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def get_payload_budget_mb(metadata: Dict[str, Any], cli_value: float) -> float:
    if cli_value is not None:
        return float(cli_value)
    image = metadata.get("image", {}) or {}
    generation = image.get("generation_defaults", {}) or {}
    nano = generation.get("nano_banana", {}) or {}
    return float(nano.get("max_total_input_mb", 18))


def main() -> None:
    args = parse_args()
    identity_dir = Path(args.identity_pack_dir).resolve()
    metadata_path = identity_dir / args.metadata_file
    output_dir = identity_dir if args.in_place else (identity_dir / args.output_subdir)

    if not identity_dir.exists():
        raise FileNotFoundError(f"No existe directorio: {identity_dir}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"No existe metadata: {metadata_path}")

    metadata = load_metadata(metadata_path)
    source_names = collect_source_images(identity_dir, metadata, args.all_images)
    if not source_names:
        print("No se encontraron imagenes para procesar.")
        return

    print(f"Procesando {len(source_names)} imagen(es)...")
    mapping: Dict[str, str] = {}
    total_original = 0
    total_optimized = 0
    processed = 0

    for name in source_names:
        src = identity_dir / name
        if not src.exists():
            print(f"- Omitida (no existe): {name}")
            continue
        if src.suffix.lower() not in VALID_EXTENSIONS:
            print(f"- Omitida (extension no soportada): {name}")
            continue

        out_hint = _target_output_path(name, identity_dir, output_dir, args.in_place)
        out_path, original_size, optimized_size = optimize_one_image(
            source_path=src,
            output_path_hint=out_hint,
            max_dim=args.max_dim,
            jpeg_quality=args.jpeg_quality,
            png_compress_level=args.png_compress_level,
            in_place=args.in_place,
        )

        if args.in_place:
            mapped_name = out_path.name
        else:
            mapped_name = str(Path(args.output_subdir) / out_path.name)

        mapping[name] = mapped_name
        total_original += original_size
        total_optimized += optimized_size
        processed += 1

        ratio = (1 - (optimized_size / original_size)) * 100 if original_size else 0
        print(
            f"- {name} -> {mapped_name} | "
            f"{original_size / (1024 * 1024):.2f}MB -> {optimized_size / (1024 * 1024):.2f}MB "
            f"({ratio:.1f}% ahorro)"
        )

    if processed == 0:
        print("No se procesaron imagenes.")
        return

    avg_optimized = total_optimized / processed
    estimated_wire_per_image = avg_optimized * 1.37  # overhead aproximado base64/data-url
    budget_mb = get_payload_budget_mb(metadata, args.estimate_max_total_input_mb)
    budget_bytes = budget_mb * 1024 * 1024
    suggested_max_refs = max(1, int(math.floor(budget_bytes / estimated_wire_per_image)))

    print("\nResumen:")
    print(f"- Imagenes procesadas: {processed}")
    print(f"- Tamano total original: {total_original / (1024 * 1024):.2f} MB")
    print(f"- Tamano total optimizado: {total_optimized / (1024 * 1024):.2f} MB")
    print(f"- Promedio optimizado por imagen: {avg_optimized / (1024 * 1024):.2f} MB")
    print(f"- Recomendacion max_reference_images para ~{budget_mb:.1f}MB: {suggested_max_refs}")

    if args.update_metadata:
        backup = metadata_path.with_suffix(
            f".json.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        backup.write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")
        updated_metadata = deep_replace_paths(metadata, mapping)
        save_metadata(metadata_path, updated_metadata)
        print(f"\nMetadata actualizado: {metadata_path.name}")
        print(f"Backup creado: {backup.name}")
    else:
        print("\nMetadata NO modificado (usa --update-metadata para aplicarlo).")


if __name__ == "__main__":
    main()
