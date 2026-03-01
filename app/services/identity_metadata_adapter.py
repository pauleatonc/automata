"""
Adaptador de metadata de identidad.

Permite usar un JSON organizado por proceso (caption/image/assets/meta)
sin romper compatibilidad con la estructura legacy (claves en raíz).
"""
from typing import Any, Dict, Iterable, Optional


def _deep_get(data: Dict[str, Any], path: Iterable[str], default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def normalize_identity_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normaliza metadata para que el resto del sistema lea claves legacy.

    Soporta dos formatos:
    - Legacy: claves principales en raíz (actual)
    - Reorganizado: caption/image/assets/meta
    """
    if not isinstance(metadata, dict):
        return {}

    normalized = dict(metadata)

    assets = normalized.get("assets", {}) or {}
    caption = normalized.get("caption", {}) or {}
    image = normalized.get("image", {}) or {}

    # -------------------------
    # Assets
    # -------------------------
    normalized["reference_images"] = _coalesce(
        normalized.get("reference_images"),
        assets.get("reference_images")
    ) or []
    normalized["base_images"] = _coalesce(
        normalized.get("base_images"),
        assets.get("base_images")
    ) or []
    normalized["generated_images"] = _coalesce(
        normalized.get("generated_images"),
        assets.get("generated_images")
    ) or []

    # -------------------------
    # Caption/Text
    # -------------------------
    normalized["influencer_name"] = _coalesce(
        normalized.get("influencer_name"),
        caption.get("influencer_name")
    ) or "Narradora"
    normalized["description"] = _coalesce(
        normalized.get("description"),
        caption.get("description")
    ) or "Un viaje de autodescubrimiento"
    normalized["voice_tone"] = _coalesce(
        normalized.get("voice_tone"),
        caption.get("voice_tone")
    ) or "poético e íntimo"
    normalized["style_notes"] = _coalesce(
        normalized.get("style_notes"),
        caption.get("style_notes")
    ) or "fotografía natural y contemplativa"
    normalized["palette"] = _coalesce(
        normalized.get("palette"),
        caption.get("palette")
    ) or {}
    normalized["themes"] = _coalesce(
        normalized.get("themes"),
        caption.get("themes")
    ) or []

    # Prompt sanitizer: puede vivir en raíz, caption o image
    normalized["prompt_sanitizer"] = _coalesce(
        normalized.get("prompt_sanitizer"),
        caption.get("prompt_sanitizer"),
        image.get("prompt_sanitizer")
    ) or {}

    # narrative_rules.caption_guidelines <-> caption.guidelines
    existing_caption_guidelines = _deep_get(
        normalized, ("narrative_rules", "caption_guidelines"), default=None
    )
    caption_guidelines = _coalesce(existing_caption_guidelines, caption.get("guidelines"))
    if caption_guidelines is not None:
        narrative_rules = normalized.get("narrative_rules", {}) or {}
        narrative_rules["caption_guidelines"] = caption_guidelines
        normalized["narrative_rules"] = narrative_rules

    # persona puede venir de caption.persona
    normalized["persona"] = _coalesce(
        normalized.get("persona"),
        caption.get("persona")
    ) or {}
    normalized["narrative"] = _coalesce(
        normalized.get("narrative"),
        caption.get("narrative")
    ) or {}

    # -------------------------
    # Image
    # -------------------------
    normalized["identity_strength"] = _coalesce(
        normalized.get("identity_strength"),
        image.get("identity_strength")
    )
    normalized["style_strength"] = _coalesce(
        normalized.get("style_strength"),
        image.get("style_strength")
    )

    normalized["appearance_variation"] = _coalesce(
        normalized.get("appearance_variation"),
        image.get("appearance_variation")
    ) or {}
    normalized["look_rotation"] = _coalesce(
        normalized.get("look_rotation"),
        image.get("look_rotation")
    ) or {}
    normalized["image_prompt_guidelines"] = _coalesce(
        normalized.get("image_prompt_guidelines"),
        image.get("prompt_guidelines")
    ) or {}
    normalized["generation_defaults"] = _coalesce(
        normalized.get("generation_defaults"),
        image.get("generation_defaults")
    ) or {}
    normalized["photorealism"] = _coalesce(
        normalized.get("photorealism"),
        image.get("photorealism")
    ) or {}
    normalized["nsfw_filters"] = _coalesce(
        normalized.get("nsfw_filters"),
        image.get("nsfw_filters")
    ) or {}
    normalized["replicate_overrides"] = _coalesce(
        normalized.get("replicate_overrides"),
        image.get("replicate_overrides")
    ) or {}
    normalized["mood_controls"] = _coalesce(
        normalized.get("mood_controls"),
        image.get("mood_controls")
    ) or {}
    normalized["composition_policy"] = _coalesce(
        normalized.get("composition_policy"),
        image.get("composition_policy")
    ) or {}

    # Defaults numéricos usados por image_gen
    if normalized["identity_strength"] is None:
        normalized["identity_strength"] = 0.8
    if normalized["style_strength"] is None:
        normalized["style_strength"] = 0.7

    return normalized
