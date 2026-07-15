from rc7_shared_config import SharedSettings


class Settings(SharedSettings):
    worker_poll_interval_seconds: int = 5
    # Sized for a full semantic review: every chunk costs one Gemini call, so a
    # large manual needs hours, not minutes.
    worker_manual_timeout_seconds: int = 7200
    worker_manual_timeout_base_coverage_mb: int = 8
    worker_manual_timeout_extra_per_mb_seconds: int = 30
    worker_manual_timeout_max_seconds: int = 21600
    semantic_review_enabled: bool = True
    semantic_review_sample_rate: float = 1.0
    semantic_review_min_chars: int = 250
    semantic_review_max_chars: int = 2200
    semantic_review_autofix_enabled: bool = True
    semantic_review_merge_boundary_max: float = 0.6
    semantic_review_split_max_coherence: float = 0.65
    semantic_review_split_min_chars: int = 1800
    # Only regenerate (rewrite) a chunk when its coherence is at or below this.
    semantic_review_regenerate_max_coherence: float = 0.5
    semantic_review_enabled_languages: str = "es,en"
    semantic_review_title_include_terms: str = ""
    # 0 = no cap: review every selected chunk.
    semantic_review_max_reviews_per_manual: int = 0
    semantic_review_cost_input_per_1k_tokens: float = 0.00025
    semantic_review_cost_output_per_1k_tokens: float = 0.00075
    semantic_review_estimated_output_tokens: int = 120


settings = Settings()
