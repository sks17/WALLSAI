#!/usr/bin/env python3
"""
Debug Inference Test Harness

This script tests the end-to-end inference pipeline with synthetic scenarios
to verify that the model produces sensible outputs for different inputs.

Test scenarios:
1. Neutral baseline - all "no" answers
2. Anxiety-heavy - yes to anxiety-related symptoms
3. Depression-heavy - yes to depression-related symptoms
4. Stress-heavy - yes to stress-related symptoms
5. Mixed symptoms - combination of various symptoms
6. All "yes" - worst case scenario

Run this script to verify model behavior:
    .venv\\Scripts\\activate   (on Windows)
    python src/debug_inference.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Load Model Components
# ---------------------------------------------------------------------------

def load_schema() -> Dict[str, Any]:
    """Load the model schema from metadata.json."""
    metadata_path = ROOT / "ml" / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_pytorch_model():
    """Load the PyTorch model and preprocessor."""
    from api.predict import _load_model, _load_metadata, run_inference
    
    metadata = _load_metadata()
    model = _load_model()
    
    return model, metadata, run_inference


# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

def create_test_scenarios(features: List[str]) -> Dict[str, List[str]]:
    """
    Create test scenarios with different symptom patterns.
    
    Args:
        features: List of feature names from schema
        
    Returns:
        Dict mapping scenario name to list of yes/no values
    """
    # Feature groupings based on typical symptom clusters
    anxiety_features = {
        "feeling.nervous", "panic", "breathing.rapidly", "sweating",
        "over.react", "trouble.in.concentration"
    }
    
    depression_features = {
        "hopelessness", "feeling.negative", "blamming.yourself",
        "suicidal.thought", "feeling.tired", "change.in.eating"
    }
    
    stress_features = {
        "trouble.in.concentration", "trouble.concentrating",
        "having.trouble.with.work", "popping.up.stressful.memory",
        "having.nightmares", "anger"
    }
    
    loneliness_features = {
        "introvert", "avoids.people.or.activities", "social.media.addiction"
    }
    
    sleep_features = {
        "having.trouble.in.sleeping", "having.nightmares", "feeling.tired"
    }
    
    scenarios = {}
    
    # Scenario 1: Neutral baseline (all no)
    scenarios["neutral_baseline"] = ["no"] * len(features)
    
    # Scenario 2: Anxiety-heavy
    scenarios["anxiety_heavy"] = [
        "yes" if f in anxiety_features else "no" for f in features
    ]
    
    # Scenario 3: Depression-heavy
    scenarios["depression_heavy"] = [
        "yes" if f in depression_features else "no" for f in features
    ]
    
    # Scenario 4: Stress-heavy
    scenarios["stress_heavy"] = [
        "yes" if f in stress_features else "no" for f in features
    ]
    
    # Scenario 5: Loneliness indicators
    scenarios["loneliness_indicators"] = [
        "yes" if f in loneliness_features else "no" for f in features
    ]
    
    # Scenario 6: Sleep issues
    scenarios["sleep_issues"] = [
        "yes" if f in sleep_features else "no" for f in features
    ]
    
    # Scenario 7: Mixed mild symptoms
    mild_symptoms = {"feeling.nervous", "feeling.tired", "trouble.in.concentration"}
    scenarios["mixed_mild"] = [
        "yes" if f in mild_symptoms else "no" for f in features
    ]
    
    # Scenario 8: All yes (worst case)
    scenarios["all_yes_worst_case"] = ["yes"] * len(features)
    
    # Scenario 9: Alternating pattern
    scenarios["alternating"] = ["yes" if i % 2 == 0 else "no" for i in range(len(features))]
    
    # Scenario 10: Single symptom tests
    for single_feature in ["feeling.nervous", "hopelessness", "anger"]:
        if single_feature in features:
            idx = features.index(single_feature)
            answers = ["no"] * len(features)
            answers[idx] = "yes"
            scenarios[f"single_{single_feature}"] = answers
    
    return scenarios


# ---------------------------------------------------------------------------
# Verification Functions
# ---------------------------------------------------------------------------

def verify_feature_alignment(model, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify that the model's expected features match the schema.
    
    Args:
        model: Loaded PyTorch model
        metadata: Model metadata from metadata.json
        
    Returns:
        Dict with alignment status for each component
    """
    results = {
        "status": "ok",
        "issues": [],
        "details": {}
    }
    
    # Check schema features
    features = metadata.get("features", [])
    labels = metadata.get("labels", [])
    config = metadata.get("config", {})
    
    results["details"]["feature_count"] = len(features)
    results["details"]["label_count"] = len(labels)
    results["details"]["features"] = features
    results["details"]["labels"] = labels
    
    # Check model configuration
    expected_input_dim = config.get("input_dim", 24)
    expected_output_dim = config.get("num_classes", 5)
    
    if len(features) != expected_input_dim:
        results["issues"].append(
            f"Feature count mismatch: schema has {len(features)}, model expects {expected_input_dim}"
        )
        results["status"] = "error"
    
    if len(labels) != expected_output_dim:
        results["issues"].append(
            f"Label count mismatch: schema has {len(labels)}, model expects {expected_output_dim}"
        )
        results["status"] = "error"
    
    # Test a dummy forward pass
    try:
        import torch
        dummy_input = torch.zeros(1, expected_input_dim)
        with torch.inference_mode():
            output = model(dummy_input)
        
        results["details"]["model_output_shape"] = list(output.shape)
        
        if output.shape[1] != expected_output_dim:
            results["issues"].append(
                f"Model output mismatch: got {output.shape[1]}, expected {expected_output_dim}"
            )
            results["status"] = "error"
    except Exception as e:
        results["issues"].append(f"Forward pass failed: {str(e)}")
        results["status"] = "error"
    
    return results


def run_scenario_tests(run_inference, features: List[str], scenarios: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Run inference on all test scenarios and collect results.
    
    Args:
        run_inference: Inference function from api/predict.py
        features: List of feature names
        scenarios: Dict of scenario name -> answers list
        
    Returns:
        List of test results
    """
    results = []
    
    for name, answers in scenarios.items():
        # Count yes/no
        yes_count = sum(1 for a in answers if a == "yes")
        no_count = len(answers) - yes_count
        
        try:
            # Run inference
            output = run_inference(answers)
            
            result = {
                "scenario": name,
                "input_summary": f"{yes_count} yes / {no_count} no",
                "prediction": output.get("prediction"),
                "confidence": output.get("confidence"),
                "probabilities": output.get("probabilities", {}),
                "status": "success"
            }
        except Exception as e:
            result = {
                "scenario": name,
                "input_summary": f"{yes_count} yes / {no_count} no",
                "error": str(e),
                "status": "error"
            }
        
        results.append(result)
    
    return results


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze test results for consistency and expected behavior.
    
    Args:
        results: List of test result dicts
        
    Returns:
        Analysis summary
    """
    analysis = {
        "total_tests": len(results),
        "successful": 0,
        "failed": 0,
        "warnings": [],
        "observations": []
    }
    
    predictions = {}
    confidences = []
    
    for r in results:
        if r["status"] == "success":
            analysis["successful"] += 1
            pred = r["prediction"]
            predictions[pred] = predictions.get(pred, 0) + 1
            confidences.append(r["confidence"])
        else:
            analysis["failed"] += 1
    
    # Check for expected behaviors
    baseline_result = next((r for r in results if r["scenario"] == "neutral_baseline"), None)
    worst_result = next((r for r in results if r["scenario"] == "all_yes_worst_case"), None)
    
    if baseline_result and worst_result:
        if baseline_result.get("status") == "success" and worst_result.get("status") == "success":
            # Baseline should ideally predict "Normal" or at least not severe
            if baseline_result["prediction"] == "Normal":
                analysis["observations"].append("✓ Baseline correctly predicts 'Normal'")
            else:
                analysis["warnings"].append(
                    f"⚠ Baseline predicts '{baseline_result['prediction']}' instead of 'Normal'"
                )
            
            # Worst case should not predict "Normal"
            if worst_result["prediction"] != "Normal":
                analysis["observations"].append(
                    f"✓ Worst case correctly predicts '{worst_result['prediction']}'"
                )
            else:
                analysis["warnings"].append("⚠ Worst case predicts 'Normal' (unexpected)")
    
    # Check prediction diversity
    unique_predictions = len(predictions)
    if unique_predictions == 1:
        analysis["warnings"].append(
            f"⚠ All scenarios predict the same class: '{list(predictions.keys())[0]}'"
        )
    else:
        analysis["observations"].append(
            f"✓ Model produces {unique_predictions} different predictions across scenarios"
        )
    
    # Check confidence variation
    if confidences:
        conf_range = max(confidences) - min(confidences)
        analysis["observations"].append(
            f"✓ Confidence range: {min(confidences):.3f} - {max(confidences):.3f}"
        )
        
        if conf_range < 0.1:
            analysis["warnings"].append(
                "⚠ Low confidence variation suggests model may not be differentiating inputs well"
            )
    
    analysis["prediction_distribution"] = predictions
    
    return analysis


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Run the debug inference test suite."""
    print("=" * 70)
    print("WALLS Mental Health Model - Debug Inference Test Suite")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project root: {ROOT}")
    print()
    
    # 1. Load schema
    print("1. Loading model schema...")
    try:
        schema = load_schema()
        features = schema["features"]
        labels = schema["labels"]
        print(f"   ✓ Loaded {len(features)} features, {len(labels)} labels")
        print(f"   Features: {features[:5]}... (showing first 5)")
        print(f"   Labels: {labels}")
    except Exception as e:
        print(f"   ✗ Failed to load schema: {e}")
        return
    
    print()
    
    # 2. Load model
    print("2. Loading PyTorch model...")
    try:
        model, metadata, run_inference = load_pytorch_model()
        print(f"   ✓ Model loaded successfully")
        print(f"   Model version: {metadata.get('version', 'unknown')}")
    except Exception as e:
        print(f"   ✗ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # 3. Verify feature alignment
    print("3. Verifying feature alignment...")
    alignment = verify_feature_alignment(model, metadata)
    print(f"   Status: {alignment['status']}")
    
    if alignment["issues"]:
        for issue in alignment["issues"]:
            print(f"   ✗ {issue}")
    else:
        print(f"   ✓ Features aligned: {alignment['details']['feature_count']} inputs")
        print(f"   ✓ Labels aligned: {alignment['details']['label_count']} outputs")
    
    print()
    
    # 4. Create and run test scenarios
    print("4. Running test scenarios...")
    scenarios = create_test_scenarios(features)
    print(f"   Created {len(scenarios)} test scenarios")
    print()
    
    results = run_scenario_tests(run_inference, features, scenarios)
    
    # Print results table
    print("   " + "-" * 66)
    print(f"   {'Scenario':<25} {'Input':<15} {'Prediction':<12} {'Confidence':>10}")
    print("   " + "-" * 66)
    
    for r in results:
        if r["status"] == "success":
            print(f"   {r['scenario']:<25} {r['input_summary']:<15} {r['prediction']:<12} {r['confidence']:>10.4f}")
        else:
            print(f"   {r['scenario']:<25} {r['input_summary']:<15} {'ERROR':<12} {'N/A':>10}")
    
    print("   " + "-" * 66)
    print()
    
    # 5. Analyze results
    print("5. Analysis...")
    analysis = analyze_results(results)
    print(f"   Tests run: {analysis['total_tests']}")
    print(f"   Successful: {analysis['successful']}")
    print(f"   Failed: {analysis['failed']}")
    print()
    
    if analysis["observations"]:
        print("   Observations:")
        for obs in analysis["observations"]:
            print(f"     {obs}")
        print()
    
    if analysis["warnings"]:
        print("   Warnings:")
        for warn in analysis["warnings"]:
            print(f"     {warn}")
        print()
    
    print("   Prediction distribution:")
    for pred, count in sorted(analysis["prediction_distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"     {pred:<12} {bar} ({count})")
    
    print()
    print("=" * 70)
    print("Test suite complete!")
    print()
    print("If all tests pass but the web UI shows wrong results, check:")
    print("  1. Browser console for JavaScript errors")
    print("  2. Flask logs for request parsing issues")
    print("  3. Survey.js SURVEY_SECTIONS feature IDs match schema.json")
    print()
    print("Run the web app with debug logging:")
    print("  set WALLS_DEBUG=1")
    print("  python app.py")
    print("=" * 70)


if __name__ == "__main__":
    main()


# To run:
#   .venv\Scripts\activate   (on Windows)
#   python src/debug_inference.py

