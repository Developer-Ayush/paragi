"""training/evaluation.py — Evaluation metrics for cognitive graph reasoning."""
from __future__ import annotations

import time
from typing import List, Dict, Any
from graph.graph import GraphEngine
from training.synthetic_data_generator import generate_reasoning_data
from encoder.compiler import SemanticCompiler
from cognition.consciousness import CognitionEngine


class CognitiveBenchmarker:
    """
    Measures the 'intelligence' and 'reliability' of the cognitive runtime.
    """

    def __init__(self, graph: GraphEngine):
        self.graph = graph
        self.compiler = SemanticCompiler()
        self.engine = CognitionEngine(graph)

    def run_full_evaluation(self, sample_size: int = 50) -> Dict[str, Any]:
        """Runs all benchmarks and returns a composite score."""
        t0 = time.perf_counter()
        
        # 1. Generate test data from current graph
        test_data = generate_reasoning_data(self.graph, count=sample_size)
        if not test_data:
            return {"error": "Graph is too small to evaluate."}

        # 2. Benchmarks
        extraction_results = self.evaluate_extraction(test_data)
        reasoning_results = self.evaluate_reasoning(test_data)
        
        latency = (time.perf_counter() - t0) / sample_size

        return {
            "sample_size": sample_size,
            "extraction_accuracy": extraction_results["accuracy"],
            "reasoning_recall": reasoning_results["recall"],
            "logic_coherence": reasoning_results["coherence"],
            "avg_latency_ms": latency * 1000,
            "timestamp": time.time()
        }

    def evaluate_extraction(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tests if the SemanticCompiler correctly parses natural language into IR."""
        matches = 0
        for item in test_data:
            text = item["text"]
            expected_ir = item["semantic_ir"]
            
            actual_ir = self.compiler.compile(text)
            
            # Compare primary relation
            if expected_ir["relations"] and actual_ir.relations:
                exp_rel = expected_ir["relations"][0]
                act_rel = actual_ir.relations[0]
                if exp_rel["relation"] == act_rel.relation:
                    matches += 1
                    
        return {"accuracy": matches / len(test_data)}

    def evaluate_reasoning(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tests if the CognitionEngine can retrieve the relations it was trained on."""
        recall_hits = 0
        coherence_sum = 0.0
        
        for item in test_data:
            text = item["text"]
            expected_ir = item["semantic_ir"]
            
            # Simulate a query
            ir = self.compiler.compile(text)
            result = self.engine.process(ir)
            
            # Recall: Did we find the expected target?
            if expected_ir["relations"]:
                tgt = expected_ir["relations"][0]["target"]
                if any(tgt.lower() in p.node_labels[1:].lower() for p in result.paths if len(p.node_labels) > 1):
                    recall_hits += 1
            
            coherence_sum += result.extra.get("coherence_score", 0.0)
            
        return {
            "recall": recall_hits / len(test_data),
            "coherence": coherence_sum / len(test_data)
        }


def evaluate_graph(graph: GraphEngine):
    benchmarker = CognitiveBenchmarker(graph)
    return benchmarker.run_full_evaluation()
