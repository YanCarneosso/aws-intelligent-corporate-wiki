from __future__ import annotations

from typing import Any

from services.query.rag import BedrockGenerator, BedrockGuardrail, Evidence, KnowledgeBaseRetriever


class FakeRetrieverClient:
    def retrieve(self, **request: Any) -> dict[str, Any]:
        assert (
            request["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"] == 4
        )
        return {
            "retrievalResults": [
                {
                    "content": {"text": "Approved Rota 120"},
                    "score": 0.88,
                    "metadata": {
                        "document_id": "doc_" + "a" * 32,
                        "chunk_id": "chk_" + "b" * 32,
                        "source_file": "minutes.pdf",
                        "page": 3,
                    },
                },
                {"content": {}, "metadata": {}},
            ]
        }


class FakeRuntimeClient:
    def __init__(self, action: str = "NONE") -> None:
        self.action = action

    def converse(self, **request: Any) -> dict[str, Any]:
        assert "retrieved-evidence" in request["messages"][0]["content"][0]["text"]
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "name": "return_grounded_answer",
                                "input": {
                                    "answer": "Rota 120 was approved.",
                                    "evidence_ids": ["E1"],
                                },
                            }
                        }
                    ]
                }
            }
        }

    def apply_guardrail(self, **request: Any) -> dict[str, str]:
        assert request["source"] in {"INPUT", "OUTPUT"}
        return {"action": self.action}


def test_knowledge_base_retriever_maps_metadata_to_evidence() -> None:
    results = KnowledgeBaseRetriever(FakeRetrieverClient(), "kb-id").retrieve(
        "question", top_k=4, metadata_filter={"equals": {"key": "x", "value": "y"}}
    )
    assert len(results) == 1
    assert results[0].page == 3
    assert results[0].score == 0.88


def test_bedrock_generator_requires_structured_evidence_ids() -> None:
    evidence = Evidence(
        evidence_id="E1",
        document_id="doc_" + "a" * 32,
        chunk_id="chk_" + "b" * 32,
        text="Approved Rota 120",
        score=0.88,
        source_file="minutes.pdf",
        page=3,
    )
    answer = BedrockGenerator(FakeRuntimeClient(), "model").generate("question", [evidence])
    assert answer.evidence_ids == ["E1"]


def test_optional_guardrail_can_allow_or_block() -> None:
    assert BedrockGuardrail(FakeRuntimeClient(), None, "DRAFT").allows("text", source="INPUT")
    assert not BedrockGuardrail(FakeRuntimeClient("GUARDRAIL_INTERVENED"), "gr", "DRAFT").allows(
        "hostile", source="INPUT"
    )
