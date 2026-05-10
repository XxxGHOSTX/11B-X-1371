from __future__ import annotations

from hashlib import sha1

from ..models import DecodeNode
from .registry import DecoderRegistry, default_registry
from .scoring import score_output, unexplained_residue


def run_layered_decode(
    artifact_id: str,
    text: str,
    *,
    registry: DecoderRegistry | None = None,
    max_depth: int = 2,
    max_nodes: int = 250,
) -> list[DecodeNode]:
    registry = registry or default_registry()
    root = DecodeNode(
        node_id="root",
        artifact_id=artifact_id,
        parent_id=None,
        depth=0,
        transform_name="input",
        parameters={},
        output=text,
        structuredness={},
        validation_notes=[],
        residue=unexplained_residue(text),
        score=score_output(text, residue=unexplained_residue(text)),
    )
    nodes = [root]
    queue = [root]
    seen_outputs = {text}
    while queue and len(nodes) < max_nodes:
        node = queue.pop(0)
        if node.depth >= max_depth:
            continue
        for registered in registry.transforms():
            for result in registered.handler(node.output):
                if not result.output or result.output == node.output or result.output in seen_outputs:
                    continue
                residue = unexplained_residue(result.output)
                child = DecodeNode(
                    node_id=sha1(f"{node.node_id}:{registered.name}:{result.output}".encode()).hexdigest()[:16],
                    artifact_id=artifact_id,
                    parent_id=node.node_id,
                    depth=node.depth + 1,
                    transform_name=registered.name,
                    parameters=result.parameters,
                    output=result.output,
                    structuredness=result.structuredness,
                    validation_notes=result.validation_notes,
                    residue=residue,
                    score=score_output(result.output, residue=residue),
                )
                nodes.append(child)
                queue.append(child)
                seen_outputs.add(result.output)
                if len(nodes) >= max_nodes:
                    break
            if len(nodes) >= max_nodes:
                break
    return nodes
