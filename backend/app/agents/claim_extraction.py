"""Claim Extraction Agent: extracts checkable factual claims and entities."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import ClaimExtractionOutput, ExtractedClaimItem, ExtractedEntity

logger = logging.getLogger(__name__)


def extract_claims(
    text: str,
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> ClaimExtractionOutput:
    """Extract factual claims from text using LLM and prompt template."""
    clean_text = text.strip()
    if not clean_text:
        return ClaimExtractionOutput(claims=[])

    # If the input text is a very short single sentence, we can process it directly
    output = run_agent_step(
        prompt_filename="claim_extraction.md",
        user_content=clean_text,
        schema_class=ClaimExtractionOutput,
        db=db,
        request_id=request_id,
        agent_name="claim_extraction",
        custom_llm=custom_llm,
    )

    # Optional: Enhance entity extraction with spaCy if available
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            nlp = None

        if nlp:
            for claim in output.claims:
                doc = nlp(claim.claim_text)
                existing_names = {e.name.lower() for e in claim.entities}
                for ent in doc.ents:
                    if ent.text.lower() not in existing_names:
                        category = "other"
                        if ent.label_ in ("PERSON",):
                            category = "person"
                        elif ent.label_ in ("ORG",):
                            category = "organization"
                        elif ent.label_ in ("GPE", "LOC", "FAC"):
                            category = "location"
                        elif ent.label_ in ("DATE", "TIME"):
                            category = "date"
                        elif ent.label_ in ("CARDINAL", "QUANTITY", "PERCENT", "MONEY"):
                            category = "number"

                        claim.entities.append(
                            ExtractedEntity(name=ent.text, category=category)
                        )
                        existing_names.add(ent.text.lower())
    except Exception as e:
        logger.debug(f"spaCy NER enhancement skipped: {e}")

    return output
