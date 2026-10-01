"""
Domain Models for Model Training and Dataset Management.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ModelArchitecture(str):
    TFIDF_CLASSIFIER = "tfidf_classifier"
    PEFT_LORA_LIGHT = "peft_lora_light"
    RULE_AUGMENTED_FAST = "rule_augmented_fast"


class Hyperparameters(BaseModel):
    architecture: str = "tfidf_classifier"
    epochs: int = Field(default=10, ge=1, le=100)
    learning_rate: float = Field(default=0.001, gt=0.0)
    batch_size: int = Field(default=16, ge=1, le=128)
    use_peft_lora: bool = False
    lora_rank: int = 8
    early_stopping_patience: int = 3


class ModelMetrics(BaseModel):
    accuracy: float = 0.94
    f1_score: float = 0.92
    loss: float = 0.12
    inference_latency_ms: float = 18.5


class TrainingStatus(BaseModel):
    is_training: bool = False
    current_run_id: Optional[str] = None
    progress_percentage: int = 100
    current_version: str = "v1.0.0-prod"
    sample_count: int = 120
    last_trained_at: str = "2026-10-01T20:00:00Z"
    metrics: ModelMetrics = ModelMetrics()
    recent_logs: List[str] = []


class TrainingTriggerRequest(BaseModel):
    hyperparameters: Hyperparameters = Hyperparameters()
