"""training/synthetic_data_generator.py — Synthetic cognitive data generation for model training."""
from __future__ import annotations

import random
from typing import List, Dict, Any
from graph.graph import GraphEngine
from core.semantic_ir import SemanticIR, Relation


class SyntheticDataGenerator:
    """
    Generates training data by performing 'reverse cognition'.
    It takes existing graph structures and converts them into SemanticIR 
    and natural-ish language templates.
    """

    def __init__(self, graph: GraphEngine):
        self.graph = graph
        self.templates = {
            "CAUSES": [
                "Does {src} cause {tgt}?",
                "What is the relationship between {src} and {tgt}?",
                "How does {src} affect {tgt}?",
            ],
            "DEPENDS_ON": [
                "What do I need for {src}?",
                "How do I achieve {src}?",
                "Requirements for {src}.",
            ],
            "IS_A": [
                "What is {src}?",
                "Define {src}.",
                "Is {src} a type of {tgt}?",
            ]
        }

    def generate_batch(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate a batch of (text, semantic_ir) pairs."""
        dataset = []
        edges = self.graph.store.list_all_edges()
        if not edges:
            return []

        selected_edges = random.sample(edges, min(count, len(edges)))

        for edge in selected_edges:
            src_label = self.graph.get_node_label(edge.source)
            tgt_label = self.graph.get_node_label(edge.target)
            
            # 1. Create IR
            ir = SemanticIR(
                intent="relation",
                reasoning_mode="general",
                entities=[src_label, tgt_label],
                relations=[Relation(source=src_label, relation=edge.type.value, target=tgt_label)],
                raw_text="",
                confidence=1.0
            )

            # 2. Select a template and generate text
            templates = self.templates.get(edge.type.value, ["Tell me about {src} and {tgt}."])
            text = random.choice(templates).format(src=src_label, tgt=tgt_label)
            ir.raw_text = text
            ir.normalized_text = text.lower().strip("?")

            dataset.append({
                "text": text,
                "semantic_ir": ir.to_dict()
            })

        return dataset


def generate_reasoning_data(graph: GraphEngine, count: int = 50):
    generator = SyntheticDataGenerator(graph)
    return generator.generate_batch(count)
