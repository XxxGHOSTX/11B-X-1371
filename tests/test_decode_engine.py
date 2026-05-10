from x1371.decode.engine import run_layered_decode


def test_layered_decode_traverses_reverse_transform() -> None:
    nodes = run_layered_decode("artifact", "cba", max_depth=1, max_nodes=25)
    outputs = {node.output for node in nodes}
    assert "abc" in outputs
    assert any(node.parent_id == "root" for node in nodes if node.output == "abc")
