"""
KERNEL Multi-Task Neural Network Model

A neural network that predicts multiple mental health scores with uncertainty.

Key Features:
1. EXPECTED_INPUT_DIM = 100 (fixed)
2. Shared trunk with task-specific heads
3. Outputs mean + variance for each score
4. Monte Carlo dropout for uncertainty estimation
5. Runtime dimension validation

Architecture:
    Input (100 features) → Shared Trunk → [Stress, Depression, Anxiety, Sleep, Wellbeing] Heads
    Each head outputs: mean, log_variance
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("walls.kernel.model")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# CRITICAL: This MUST match preprocessor.TARGET_INPUT_DIM
EXPECTED_INPUT_DIM = 100

# Default architecture
DEFAULT_HIDDEN_DIMS = [64, 32, 16]
DEFAULT_DROPOUT = 0.2


# ---------------------------------------------------------------------------
# Check for PyTorch
# ---------------------------------------------------------------------------

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using fallback model")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PredictionResult:
    """Container for model predictions with uncertainty."""
    
    # Per-target predictions (each has mean, std, ci_lower, ci_upper)
    stress: Dict[str, float]
    depression: Dict[str, float]
    anxiety: Dict[str, float]
    sleep_quality: Dict[str, float]
    wellbeing: Dict[str, float]
    
    # Clinical classifications
    classifications: Dict[str, str]
    
    # Risk flags
    flags: List[str]
    
    # Model metadata
    model_version: str
    inference_mode: str  # "single", "mc_dropout", "fallback"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scores": {
                "stress": self.stress,
                "depression": self.depression,
                "anxiety": self.anxiety,
                "sleep_quality": self.sleep_quality,
                "wellbeing": self.wellbeing
            },
            "classifications": self.classifications,
            "flags": self.flags,
            "model_version": self.model_version,
            "inference_mode": self.inference_mode
        }


# ---------------------------------------------------------------------------
# PyTorch Model Components
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:
    
    class SharedTrunk(nn.Module):
        """Shared representation learning trunk."""
        
        def __init__(self, input_dim: int, hidden_dims: List[int], dropout: float = 0.2):
            super().__init__()
            
            layers = []
            prev_dim = input_dim
            
            for hidden_dim in hidden_dims:
                layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.LayerNorm(hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(dropout)
                ])
                prev_dim = hidden_dim
            
            self.network = nn.Sequential(*layers)
            self.output_dim = hidden_dims[-1]
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.network(x)
    
    
    class DistributionalHead(nn.Module):
        """
        Task-specific head that outputs a distribution (mean + variance).
        """
        
        def __init__(
            self,
            input_dim: int,
            output_range: Tuple[float, float],
            name: str = "head"
        ):
            super().__init__()
            
            self.name = name
            self.output_min, self.output_max = output_range
            self.output_range = self.output_max - self.output_min
            
            # Two outputs: mean and log_variance
            self.fc_mean = nn.Linear(input_dim, 1)
            self.fc_logvar = nn.Linear(input_dim, 1)
            
            # Initialize log_variance to small value
            nn.init.constant_(self.fc_logvar.bias, -2.0)
        
        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Returns:
                mean: Predicted mean value (scaled to output range)
                variance: Predicted variance
            """
            mean_raw = self.fc_mean(x)
            mean = torch.sigmoid(mean_raw) * self.output_range + self.output_min
            
            log_var = self.fc_logvar(x)
            variance = F.softplus(log_var) * (self.output_range / 10)
            
            return mean.squeeze(-1), variance.squeeze(-1)
    
    
    class KernelModel(nn.Module):
        """
        Multi-task neural network for mental health assessment.
        
        CRITICAL: Input dimension MUST be EXPECTED_INPUT_DIM (100).
        """
        
        def __init__(
            self,
            input_dim: int = EXPECTED_INPUT_DIM,
            hidden_dims: List[int] = None,
            dropout: float = DEFAULT_DROPOUT
        ):
            super().__init__()
            
            # Validate input dimension
            if input_dim != EXPECTED_INPUT_DIM:
                logger.warning(
                    f"Creating model with input_dim={input_dim}, "
                    f"but expected {EXPECTED_INPUT_DIM}. This may cause issues."
                )
            
            if hidden_dims is None:
                hidden_dims = DEFAULT_HIDDEN_DIMS.copy()
            
            self.input_dim = input_dim
            self.hidden_dims = hidden_dims
            self.dropout_rate = dropout
            
            # Shared trunk
            self.trunk = SharedTrunk(input_dim, hidden_dims, dropout)
            trunk_output_dim = self.trunk.output_dim
            
            # Task-specific heads
            self.heads = nn.ModuleDict({
                "stress": DistributionalHead(trunk_output_dim, (0, 100), "stress"),
                "depression": DistributionalHead(trunk_output_dim, (0, 27), "depression"),
                "anxiety": DistributionalHead(trunk_output_dim, (0, 21), "anxiety"),
                "sleep_quality": DistributionalHead(trunk_output_dim, (0, 10), "sleep_quality"),
                "wellbeing": DistributionalHead(trunk_output_dim, (0, 100), "wellbeing"),
            })
            
            self.version = "kernel-v1.0"
            
            logger.info(f"KernelModel initialized: input_dim={input_dim}, hidden={hidden_dims}")
        
        def _validate_input(self, x: torch.Tensor):
            """Validate input tensor dimensions."""
            if x.dim() == 1:
                x = x.unsqueeze(0)
            
            if x.shape[1] != self.input_dim:
                raise ValueError(
                    f"Input dimension mismatch: got {x.shape[1]}, "
                    f"expected {self.input_dim}. "
                    f"Ensure preprocessor output matches model input."
                )
            
            return x
        
        def forward(
            self,
            x: torch.Tensor
        ) -> Dict[str, Tuple[torch.Tensor, torch.Tensor]]:
            """
            Forward pass.
            
            Args:
                x: Input tensor of shape (batch_size, input_dim)
                
            Returns:
                Dict mapping target name to (mean, variance) tuple
            """
            x = self._validate_input(x)
            
            # Shared representation
            shared = self.trunk(x)
            
            # Task-specific predictions
            outputs = {}
            for name, head in self.heads.items():
                mean, var = head(shared)
                outputs[name] = (mean, var)
            
            return outputs
        
        def predict(
            self,
            x: torch.Tensor,
            n_samples: int = 10,
            use_mc_dropout: bool = True
        ) -> PredictionResult:
            """
            Make predictions with uncertainty estimation.
            
            Args:
                x: Input tensor of shape (input_dim,) or (1, input_dim)
                n_samples: Number of Monte Carlo samples
                use_mc_dropout: Whether to use MC dropout
                
            Returns:
                PredictionResult with means, CIs, and classifications
            """
            # Ensure tensor
            if isinstance(x, np.ndarray):
                x = torch.tensor(x, dtype=torch.float32)
            
            x = self._validate_input(x)
            
            if use_mc_dropout and n_samples > 1:
                logger.debug(f"Running MC dropout with {n_samples} samples")
                return self._predict_mc_dropout(x, n_samples)
            else:
                return self._predict_single(x)
        
        def _predict_single(self, x: torch.Tensor) -> PredictionResult:
            """Single forward pass prediction."""
            self.eval()
            with torch.inference_mode():
                outputs = self.forward(x)
            
            predictions = {}
            for name, (mean, var) in outputs.items():
                mean_val = float(mean.item())
                std_val = float(var.sqrt().item())
                
                predictions[name] = {
                    "mean": round(mean_val, 2),
                    "std": round(std_val, 2),
                    "ci_lower": round(max(0, mean_val - 1.96 * std_val), 2),
                    "ci_upper": round(mean_val + 1.96 * std_val, 2),
                }
            
            return self._build_result(predictions, "single")
        
        def _predict_mc_dropout(self, x: torch.Tensor, n_samples: int) -> PredictionResult:
            """Monte Carlo dropout prediction."""
            self.train()  # Enable dropout
            
            samples = {name: [] for name in self.heads.keys()}
            
            with torch.inference_mode():
                for i in range(n_samples):
                    outputs = self.forward(x)
                    for name, (mean, _) in outputs.items():
                        samples[name].append(float(mean.item()))
                    
                    if (i + 1) % 5 == 0:
                        logger.debug(f"MC dropout sample {i + 1}/{n_samples}")
            
            predictions = {}
            for name, values in samples.items():
                mean_val = float(np.mean(values))
                std_val = float(np.std(values))
                
                predictions[name] = {
                    "mean": round(mean_val, 2),
                    "std": round(std_val, 2),
                    "ci_lower": round(max(0, mean_val - 1.96 * std_val), 2),
                    "ci_upper": round(mean_val + 1.96 * std_val, 2),
                }
            
            self.eval()
            return self._build_result(predictions, "mc_dropout")
        
        def _build_result(
            self,
            predictions: Dict[str, Dict[str, float]],
            inference_mode: str
        ) -> PredictionResult:
            """Build a PredictionResult from raw predictions."""
            
            # Classify each score
            classifications = {
                "stress": self._classify_stress(predictions["stress"]["mean"]),
                "depression": self._classify_phq9(predictions["depression"]["mean"]),
                "anxiety": self._classify_gad7(predictions["anxiety"]["mean"]),
                "sleep_quality": self._classify_sleep(predictions["sleep_quality"]["mean"]),
                "wellbeing": self._classify_wellbeing(predictions["wellbeing"]["mean"]),
            }
            
            # Generate flags
            flags = []
            if predictions["depression"]["mean"] >= 20:
                flags.append("SEVERE_DEPRESSION")
            if predictions["anxiety"]["mean"] >= 15:
                flags.append("SEVERE_ANXIETY")
            if predictions["stress"]["mean"] >= 80:
                flags.append("EXTREME_STRESS")
            if predictions["sleep_quality"]["mean"] <= 3:
                flags.append("POOR_SLEEP")
            
            return PredictionResult(
                stress=predictions["stress"],
                depression=predictions["depression"],
                anxiety=predictions["anxiety"],
                sleep_quality=predictions["sleep_quality"],
                wellbeing=predictions["wellbeing"],
                classifications=classifications,
                flags=flags,
                model_version=self.version,
                inference_mode=inference_mode
            )
        
        @staticmethod
        def _classify_stress(score: float) -> str:
            if score < 20: return "low"
            if score < 40: return "mild"
            if score < 60: return "moderate"
            if score < 80: return "high"
            return "severe"
        
        @staticmethod
        def _classify_phq9(score: float) -> str:
            if score < 5: return "minimal"
            if score < 10: return "mild"
            if score < 15: return "moderate"
            if score < 20: return "moderately_severe"
            return "severe"
        
        @staticmethod
        def _classify_gad7(score: float) -> str:
            if score < 5: return "minimal"
            if score < 10: return "mild"
            if score < 15: return "moderate"
            return "severe"
        
        @staticmethod
        def _classify_sleep(score: float) -> str:
            if score >= 8: return "excellent"
            if score >= 6: return "good"
            if score >= 4: return "fair"
            if score >= 2: return "poor"
            return "very_poor"
        
        @staticmethod
        def _classify_wellbeing(score: float) -> str:
            if score >= 80: return "thriving"
            if score >= 60: return "flourishing"
            if score >= 40: return "moderate"
            if score >= 20: return "struggling"
            return "languishing"
        
        def save(self, path: Path):
            """Save model and config."""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            torch.save({
                "state_dict": self.state_dict(),
                "config": {
                    "input_dim": self.input_dim,
                    "hidden_dims": self.hidden_dims,
                    "dropout": self.dropout_rate,
                    "version": self.version
                }
            }, path)
            logger.info(f"Saved model to {path}")
        
        @classmethod
        def load(cls, path: Path) -> "KernelModel":
            """Load model from file."""
            path = Path(path)
            checkpoint = torch.load(path, map_location="cpu")
            
            config = checkpoint["config"]
            model = cls(
                input_dim=config["input_dim"],
                hidden_dims=config["hidden_dims"],
                dropout=config["dropout"]
            )
            model.load_state_dict(checkpoint["state_dict"])
            model.version = config.get("version", "kernel-v1.0")
            
            logger.info(f"Loaded model from {path}")
            return model


else:
    # Fallback model when PyTorch is not available
    
    class KernelModel:
        """Fallback model that uses simple heuristics."""
        
        def __init__(self, input_dim: int = EXPECTED_INPUT_DIM, **kwargs):
            self.input_dim = input_dim
            self.version = "kernel-fallback-v1.0"
            
            if input_dim != EXPECTED_INPUT_DIM:
                logger.warning(
                    f"Creating fallback model with input_dim={input_dim}, "
                    f"but expected {EXPECTED_INPUT_DIM}"
                )
        
        def predict(self, x, **kwargs) -> PredictionResult:
            """Simple heuristic-based prediction."""
            if isinstance(x, np.ndarray):
                x = x.flatten()
            
            # Validate dimension
            if len(x) != self.input_dim:
                raise ValueError(
                    f"Input dimension mismatch: got {len(x)}, expected {self.input_dim}"
                )
            
            # Use first 20 values (tabular) for heuristics
            tabular_mean = float(np.mean(x[:20]))
            
            # Higher tabular values = worse mental health
            predictions = {
                "stress": {
                    "mean": round(tabular_mean * 100, 2),
                    "std": 10.0,
                    "ci_lower": max(0, round(tabular_mean * 100 - 20, 2)),
                    "ci_upper": min(100, round(tabular_mean * 100 + 20, 2))
                },
                "depression": {
                    "mean": round(tabular_mean * 27, 2),
                    "std": 3.0,
                    "ci_lower": max(0, round(tabular_mean * 27 - 6, 2)),
                    "ci_upper": min(27, round(tabular_mean * 27 + 6, 2))
                },
                "anxiety": {
                    "mean": round(tabular_mean * 21, 2),
                    "std": 2.5,
                    "ci_lower": max(0, round(tabular_mean * 21 - 5, 2)),
                    "ci_upper": min(21, round(tabular_mean * 21 + 5, 2))
                },
                "sleep_quality": {
                    "mean": round((1 - tabular_mean) * 10, 2),
                    "std": 1.0,
                    "ci_lower": max(0, round((1 - tabular_mean) * 10 - 2, 2)),
                    "ci_upper": min(10, round((1 - tabular_mean) * 10 + 2, 2))
                },
                "wellbeing": {
                    "mean": round((1 - tabular_mean) * 100, 2),
                    "std": 10.0,
                    "ci_lower": max(0, round((1 - tabular_mean) * 100 - 20, 2)),
                    "ci_upper": min(100, round((1 - tabular_mean) * 100 + 20, 2))
                },
            }
            
            classifications = {
                "stress": "moderate",
                "depression": "mild",
                "anxiety": "mild",
                "sleep_quality": "fair",
                "wellbeing": "moderate"
            }
            
            return PredictionResult(
                stress=predictions["stress"],
                depression=predictions["depression"],
                anxiety=predictions["anxiety"],
                sleep_quality=predictions["sleep_quality"],
                wellbeing=predictions["wellbeing"],
                classifications=classifications,
                flags=[],
                model_version=self.version,
                inference_mode="fallback"
            )
        
        def save(self, path: Path):
            """Save config as JSON."""
            path = Path(path)
            with open(path, "w") as f:
                json.dump({"version": self.version, "input_dim": self.input_dim}, f)
        
        @classmethod
        def load(cls, path: Path) -> "KernelModel":
            """Load from JSON config."""
            with open(path) as f:
                config = json.load(f)
            return cls(**config)


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------

def selftest():
    """Run self-test to verify module works correctly."""
    print("=" * 60)
    print("KERNEL Model Self-Test")
    print("=" * 60)
    print(f"Expected input dimension: {EXPECTED_INPUT_DIM}")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    print()
    
    # Create model
    model = KernelModel(input_dim=EXPECTED_INPUT_DIM)
    print(f"Model version: {model.version}")
    
    # Test with correct dimension
    print("\nTest 1: Correct input dimension")
    try:
        if TORCH_AVAILABLE:
            test_input = torch.randn(1, EXPECTED_INPUT_DIM)
        else:
            test_input = np.random.randn(EXPECTED_INPUT_DIM)
        
        result = model.predict(test_input, n_samples=5, use_mc_dropout=TORCH_AVAILABLE)
        
        print(f"  ✓ Input shape: ({EXPECTED_INPUT_DIM},)")
        print(f"  ✓ Inference mode: {result.inference_mode}")
        print(f"\n  Results:")
        print(f"    Stress: {result.stress['mean']:.1f} ± {result.stress['std']:.1f} [{result.classifications['stress']}]")
        print(f"    Depression: {result.depression['mean']:.1f} ± {result.depression['std']:.1f} [{result.classifications['depression']}]")
        print(f"    Anxiety: {result.anxiety['mean']:.1f} ± {result.anxiety['std']:.1f} [{result.classifications['anxiety']}]")
        print(f"    Sleep: {result.sleep_quality['mean']:.1f} ± {result.sleep_quality['std']:.1f} [{result.classifications['sleep_quality']}]")
        print(f"    Wellbeing: {result.wellbeing['mean']:.1f} ± {result.wellbeing['std']:.1f} [{result.classifications['wellbeing']}]")
        print(f"  ✓ Flags: {result.flags}")
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test with wrong dimension (should raise error)
    print("\nTest 2: Wrong input dimension (should fail)")
    try:
        if TORCH_AVAILABLE:
            wrong_input = torch.randn(1, 50)  # Wrong size
        else:
            wrong_input = np.random.randn(50)
        
        result = model.predict(wrong_input)
        print(f"  ✗ Should have raised ValueError!")
        return False
        
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")
        
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False
    
    # Test JSON serialization
    print("\nTest 3: JSON serialization")
    try:
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)
        print(f"  ✓ JSON serializable: {len(json_str)} bytes")
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    selftest()
