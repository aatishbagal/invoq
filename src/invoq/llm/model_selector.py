from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from invoq.system.detector import get_system_specs, SystemSpecs, GPUType


@dataclass
class ModelRecommendation:
    model_name: str
    model_size_mb: int
    description: str
    is_recommended: bool
    reason: str
    estimated_speed: str  # 'fast', 'medium', 'slow', 'very_slow'
    warning: Optional[str] = None


@dataclass
class ModelRecommendations:
    specs: SystemSpecs
    recommendations: List[ModelRecommendation]
    primary_recommendation: ModelRecommendation
    can_run_any_model: bool
    limiting_factor: str  # 'ram', 'vram', 'disk', 'none'


AVAILABLE_MODELS = [
    {
        "name": "qwen2.5-coder:1.5b",
        "size_mb": 1200,
        "min_ram_mb": 4000,
        "min_vram_mb": 2000,
        "description": "Lightweight, fast responses, good for simple tasks",
    },
    {
        "name": "qwen2.5-coder:7b",
        "size_mb": 4500,
        "min_ram_mb": 8000,
        "min_vram_mb": 6000,
        "description": "Best balance of speed and capability",
    },
    {
        "name": "qwen2.5-coder:7b-q4_0",
        "size_mb": 4000,
        "min_ram_mb": 6000,
        "min_vram_mb": 4000,
        "description": "Quantized 7B, reduced memory with minimal quality loss",
    },
    {
        "name": "codellama:7b",
        "size_mb": 3800,
        "min_ram_mb": 8000,
        "min_vram_mb": 6000,
        "description": "Meta's code model, good alternative",
    },
    {
        "name": "deepseek-coder:6.7b",
        "size_mb": 3800,
        "min_ram_mb": 8000,
        "min_vram_mb": 6000,
        "description": "Strong coding model from DeepSeek",
    },
    {
        "name": "phi3:mini",
        "size_mb": 2200,
        "min_ram_mb": 4000,
        "min_vram_mb": 3000,
        "description": "Microsoft's efficient small model",
    },
]


def _uses_gpu(specs: SystemSpecs) -> tuple[bool, Optional[int]]:
    """Determine if GPU will be used and effective VRAM."""
    gpu = specs.primary_gpu
    if gpu is None:
        return False, None

    if gpu.gpu_type == GPUType.NVIDIA and gpu.cuda_available:
        return True, gpu.vram_mb
    if gpu.gpu_type == GPUType.AMD and gpu.rocm_available:
        return True, gpu.vram_mb
    if gpu.gpu_type == GPUType.INTEL_ARC:
        return True, gpu.vram_mb

    # Integrated GPU — CPU is usually faster for LLMs
    return False, None


def _estimate_speed(
    model: dict,
    use_gpu: bool,
    memory_mb: int,
) -> tuple[str, Optional[str]]:
    """Return (estimated_speed, warning_or_none)."""
    min_key = "min_vram_mb" if use_gpu else "min_ram_mb"
    min_mem = model[min_key]
    size_mb = model["size_mb"]

    if memory_mb < min_mem:
        return "very_slow", "May be slow on your system"

    headroom = memory_mb - min_mem

    if use_gpu:
        if size_mb <= 2000:
            return "fast", None
        return "medium", None
    else:
        if size_mb <= 2000:
            return "medium", None
        if headroom > 2000:
            return "slow", None
        return "slow", "CPU inference will be slower than GPU"


def get_model_recommendations(specs: Optional[SystemSpecs] = None) -> ModelRecommendations:
    if specs is None:
        specs = get_system_specs()

    use_gpu, vram_mb = _uses_gpu(specs)
    effective_mem = vram_mb if (use_gpu and vram_mb) else specs.total_ram_mb

    limiting_factor = "none"
    if specs.total_ram_mb < 4000 and not use_gpu:
        limiting_factor = "ram"
    elif use_gpu and vram_mb is not None and vram_mb < 2000:
        limiting_factor = "vram"

    max_model_size = max(m["size_mb"] for m in AVAILABLE_MODELS)
    if specs.ollama_dir_free_mb < max_model_size:
        if limiting_factor == "none":
            limiting_factor = "disk"

    can_run_any = True

    recommendations: List[ModelRecommendation] = []
    for model in AVAILABLE_MODELS:
        speed, warning = _estimate_speed(model, use_gpu, effective_mem)

        recommendations.append(ModelRecommendation(
            model_name=model["name"],
            model_size_mb=model["size_mb"],
            description=model["description"],
            is_recommended=False,
            reason="Can run on this system",
            estimated_speed=speed,
            warning=warning,
        ))

    primary = _select_primary(use_gpu, vram_mb, specs.total_ram_mb, recommendations)

    return ModelRecommendations(
        specs=specs,
        recommendations=recommendations,
        primary_recommendation=primary,
        can_run_any_model=can_run_any,
        limiting_factor=limiting_factor,
    )


def _select_primary(
    use_gpu: bool,
    vram_mb: Optional[int],
    total_ram_mb: int,
    recommendations: List[ModelRecommendation],
) -> ModelRecommendation:
    """Pick the best model for the user's hardware."""
    target_name: Optional[str] = None

    if use_gpu and vram_mb is not None:
        if vram_mb >= 6000:
            target_name = "qwen2.5-coder:7b"
        elif vram_mb >= 4000:
            target_name = "qwen2.5-coder:7b-q4_0"
        elif vram_mb >= 2000:
            target_name = "qwen2.5-coder:1.5b"
    else:
        if total_ram_mb >= 8000:
            target_name = "qwen2.5-coder:7b-q4_0"
        elif total_ram_mb >= 6000:
            target_name = "qwen2.5-coder:1.5b"
        else:
            target_name = "phi3:mini"

    for rec in recommendations:
        if rec.model_name == target_name:
            rec.is_recommended = True
            rec.reason = "Best fit for your hardware"
            return rec

    for rec in recommendations:
        if rec.estimated_speed != "very_slow":
            rec.is_recommended = True
            rec.reason = "Smallest model that fits"
            return rec

    fallback = recommendations[0]
    fallback.is_recommended = True
    fallback.reason = "Smallest available model"
    fallback.warning = "May be slow on your system"
    return fallback


def get_recommended_model(specs: Optional[SystemSpecs] = None) -> str:
    """Return the recommended model name string."""
    recs = get_model_recommendations(specs)
    return recs.primary_recommendation.model_name


def check_model_fits(
    model_name: str,
    specs: Optional[SystemSpecs] = None,
) -> tuple[bool, str]:
    """Check if a specific model fits the system."""
    if specs is None:
        specs = get_system_specs()

    use_gpu, vram_mb = _uses_gpu(specs)
    effective_mem = vram_mb if (use_gpu and vram_mb) else specs.total_ram_mb

    for model in AVAILABLE_MODELS:
        if model["name"] == model_name:
            min_key = "min_vram_mb" if use_gpu else "min_ram_mb"
            if effective_mem >= model[min_key]:
                return True, "Model fits available memory"
            return True, f"May be slow: model wants {model[min_key]}MB, system has {effective_mem}MB"

    return True, "Custom model (cannot verify fit)"
