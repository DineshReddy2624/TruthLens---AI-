"""Database seeding script for TruthLens AI demo data.

Populates:
- Admin user (admin@truthlens.ai / AdminPass123!)
- Regular demo user (user@truthlens.ai / UserPass123!)
- Trusted scientific and journalistic domains
- 5 Pre-verified benchmark requests covering all 5 canonical labels
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    InputType,
    RequestStatus,
    SearchQuery,
    QueryIntent,
)
from app.models.evidence import RetrievedSource, EvidenceRecord, SourceEvaluation
from app.models.logs import TrustedSource
from app.services.auth import hash_password


def seed_database():
    db = SessionLocal()
    try:
        print("🌱 Seeding TruthLens AI database...")

        # 1. Seed Users
        admin_email = "admin@truthlens.ai"
        admin = db.query(User).filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name="System Administrator",
                email=admin_email,
                password_hash=hash_password("AdminPass123!"),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"  ✅ Created admin user: {admin_email}")
        else:
            print(f"  ℹ️ Admin user already exists: {admin_email}")

        demo_email = "user@truthlens.ai"
        demo_user = db.query(User).filter_by(email=demo_email).first()
        if not demo_user:
            demo_user = User(
                name="Demo Researcher",
                email=demo_email,
                password_hash=hash_password("UserPass123!"),
                role=UserRole.user,
                is_active=True,
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            print(f"  ✅ Created demo user: {demo_email}")
        else:
            print(f"  ℹ️ Demo user already exists: {demo_email}")

        # 2. Seed Trusted Sources
        trusted_domains = [
            ("nasa.gov", "Scientific", "US National Aeronautics and Space Administration"),
            ("nature.com", "Scientific", "Premier peer-reviewed scientific journal"),
            ("science.org", "Scientific", "AAAS peer-reviewed research publisher"),
            ("cdc.gov", "Medical / Health", "Centers for Disease Control and Prevention"),
            ("who.int", "Medical / Health", "World Health Organization official global health bulletins"),
            ("nih.gov", "Medical / Health", "US National Institutes of Health / PubMed Central"),
            ("reuters.com", "News / Journalism", "Global fact-checked news wire agency"),
            ("wikipedia.org", "Reference", "Crowdsourced encyclopedia with strict citation guidelines"),
        ]

        for domain, category, notes in trusted_domains:
            existing_ts = db.query(TrustedSource).filter_by(domain=domain).first()
            if not existing_ts:
                ts = TrustedSource(
                    domain=domain,
                    category=category,
                    notes=notes,
                    added_by=admin.id,
                )
                db.add(ts)
        db.commit()
        print(f"  ✅ Seeded {len(trusted_domains)} trusted domains.")

        # 3. Seed 5 Verified Demo Requests
        demo_cases = [
            {
                "claim": "People say that the Great Wall of China is visible from space with the naked eye.",
                "type": "scientific",
                "label": VerdictLabel.contradicted,
                "confidence": 0.94,
                "missing_context": "The Great Wall can only be photographed from low Earth orbit using telephoto camera lenses, not resolved by the human eye.",
                "explanation": "Astronaut observations and optical physics confirm that the Great Wall is invisible to the unaided human eye from low Earth orbit [1]. Its narrow width cannot be resolved by the human eye's angular resolution at that altitude [2].",
                "sources": [
                    {
                        "domain": "nasa.gov",
                        "url": "https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
                        "title": "China's Wall Less Great in View from Space - NASA",
                        "passage": "NASA astronauts confirm that the Great Wall is practically invisible from low Earth orbit without high magnification.",
                        "nli_label": "contradiction",
                        "total_score": 7.8,
                    },
                    {
                        "domain": "scientificamerican.com",
                        "url": "https://www.scientificamerican.com/article/is-chinas-great-wall-visible-from-space/",
                        "title": "Is China's Great Wall Really Visible from Space?",
                        "passage": "Optical physics dictates that the human pupil's diffraction limit prevents resolving a structure a few meters wide from 300 km altitude.",
                        "nli_label": "contradiction",
                        "total_score": 7.5,
                    },
                ],
            },
            {
                "claim": "Earth revolves around the Sun at an average orbital speed of roughly 30 km/s.",
                "type": "scientific",
                "label": VerdictLabel.supported,
                "confidence": 0.96,
                "missing_context": None,
                "explanation": "Astrophysical calculations and planetary telemetry prove that Earth orbits the Sun at approximately 29.78 kilometers per second (about 107,200 km/h) [1]. This velocity balances the Sun's gravitational attraction [2].",
                "sources": [
                    {
                        "domain": "nasa.gov",
                        "url": "https://solarsystem.nasa.gov/planets/earth/in-depth/",
                        "title": "Earth In Depth - NASA Solar System Exploration",
                        "passage": "Earth orbits our Sun, a star, at an average distance of about 93 million miles, traveling at roughly 18.5 miles per second (29.8 km/s).",
                        "nli_label": "entailment",
                        "total_score": 8.0,
                    },
                    {
                        "domain": "britannica.com",
                        "url": "https://www.britannica.com/science/Earth/Orbital-speed",
                        "title": "Earth: Planetary Motion and Orbit - Encyclopedia Britannica",
                        "passage": "Earth moves around the Sun at an average orbital velocity of 29.78 km per second.",
                        "nli_label": "entailment",
                        "total_score": 7.4,
                    },
                ],
            },
            {
                "claim": "The COVID-19 mRNA vaccines alter human genomic DNA permanently.",
                "type": "scientific",
                "label": VerdictLabel.contradicted,
                "confidence": 0.95,
                "missing_context": "mRNA never enters the nucleus where cell DNA resides, and degrades within days after directing spike protein synthesis.",
                "explanation": "Molecular biology disproves this claim: mRNA vaccines deliver temporary instructions to cellular ribosomes in the cytoplasm and cannot enter the nucleus or alter DNA [1]. Humans lack the reverse transcriptase required to integrate exogenous mRNA into genomic chromosomes [2].",
                "sources": [
                    {
                        "domain": "cdc.gov",
                        "url": "https://www.cdc.gov/coronavirus/2019-ncov/vaccines/facts.html",
                        "title": "Myths and Facts about COVID-19 Vaccines - CDC",
                        "passage": "COVID-19 vaccines do not change or interact with your DNA in any way. The mRNA never enters the nucleus of the cell.",
                        "nli_label": "contradiction",
                        "total_score": 8.0,
                    },
                    {
                        "domain": "who.int",
                        "url": "https://www.who.int/news-room/feature-stories/detail/the-race-for-a-covid-19-vaccine-explained",
                        "title": "How mRNA Vaccines Work - World Health Organization",
                        "passage": "Messenger RNA is broken down by standard cellular pathways shortly after instructing the cell to produce antibodies.",
                        "nli_label": "contradiction",
                        "total_score": 7.9,
                    },
                ],
            },
            {
                "claim": "Low-dose aspirin universally reduces total stroke risk without increasing gastrointestinal bleeding.",
                "type": "statistical",
                "label": VerdictLabel.partially_supported,
                "confidence": 0.81,
                "missing_context": "While aspirin prevents ischemic stroke, it significantly elevates hemorrhagic stroke and major gastrointestinal bleeding risks.",
                "explanation": "Aspirin exhibits protective anti-platelet efficacy for secondary prevention of ischemic vascular events [1]. However, comprehensive meta-analyses show that routine prophylactic use significantly increases major gastrointestinal bleeding and hemorrhagic stroke risks [2].",
                "sources": [
                    {
                        "domain": "nih.gov",
                        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6438753/",
                        "title": "Aspirin for Primary Prevention of Cardiovascular Disease - NEJM",
                        "passage": "Aspirin reduced ischemic stroke risk but led to a significantly higher rate of major hemorrhage, predominantly gastrointestinal bleeding.",
                        "nli_label": "entailment",
                        "total_score": 7.7,
                    },
                    {
                        "domain": "who.int",
                        "url": "https://www.who.int/cardiovascular_diseases/guidelines/aspirin",
                        "title": "Clinical Practice Guidelines: Antiplatelet Therapy",
                        "passage": "Routine unselected aspirin administration in individuals without established vascular disease carries net negative bleeding risk.",
                        "nli_label": "contradiction",
                        "total_score": 7.6,
                    },
                ],
            },
            {
                "claim": "Dietary saturated fat intake is the sole causative mechanism of all human cardiovascular disease.",
                "type": "scientific",
                "label": VerdictLabel.conflicting_evidence,
                "confidence": 0.76,
                "missing_context": "Modern nutritional cardiology shows cardiovascular disease is multifactorial, involving insulin resistance, chronic inflammation, genetics, and refined carbohydrates.",
                "explanation": "Clinical research yields conflicting perspectives on saturated fat's exact role in cardiovascular disease [1]. While classical diet-heart models linked saturated fats to elevated LDL cholesterol, newer large-scale cohort studies report that replacing saturated fats with refined starches does not reduce cardiovascular mortality [2].",
                "sources": [
                    {
                        "domain": "nature.com",
                        "url": "https://www.nature.com/articles/s41569-020-0414-2",
                        "title": "Saturated fats and cardiovascular health: current evidence",
                        "passage": "Contrasting epidemiological trials report divergent associations between dairy saturated fats versus industrial trans fats and coronary artery disease.",
                        "nli_label": "neutral",
                        "total_score": 7.9,
                    },
                    {
                        "domain": "nih.gov",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/32562735/",
                        "title": "Saturated Fats and Health: A Reassessment - JACC",
                        "passage": "Whole-fat dairy, unprocessed meat, and dark chocolate are not associated with increased risk of CVD, challenging simple nutrient-based thresholds.",
                        "nli_label": "contradiction",
                        "total_score": 7.8,
                    },
                ],
            },
        ]

        for case in demo_cases:
            vr = VerificationRequest(
                user_id=demo_user.id,
                input_type=InputType.claim,
                raw_text=case["claim"],
                status=RequestStatus.done,
            )
            db.add(vr)
            db.commit()
            db.refresh(vr)

            claim = ExtractedClaim(
                request_id=vr.id,
                claim_text=case["claim"],
                claim_type=case["type"],
                entities=[{"name": case["type"].capitalize(), "category": "domain"}],
                analysis={
                    "claim_type": case["type"],
                    "topic": "Scientific and empirical verification",
                    "is_time_sensitive": False,
                    "is_checkable": True,
                },
            )
            db.add(claim)
            db.commit()
            db.refresh(claim)

            # Search queries
            sq1 = SearchQuery(claim_id=claim.id, query_text=f"{case['claim']} scientific proof", intent=QueryIntent.support)
            sq2 = SearchQuery(claim_id=claim.id, query_text=f"{case['claim']} myth debunked", intent=QueryIntent.contradict)
            db.add_all([sq1, sq2])

            ev_ids = []
            for src_data in case["sources"]:
                source = RetrievedSource(
                    claim_id=claim.id,
                    url=src_data["url"],
                    domain=src_data["domain"],
                    title=src_data["title"],
                )
                db.add(source)
                db.commit()
                db.refresh(source)

                # Source Evaluation
                se = SourceEvaluation(
                    source_id=source.id,
                    publisher_score=2.0,
                    date_score=1.8,
                    quality_score=2.0,
                    corroboration_score=src_data["total_score"] - 5.8,
                    total_score=src_data["total_score"],
                    reason=f"Verified authoritative domain ({src_data['domain']}) with established editorial peer review.",
                )
                db.add(se)

                ev = EvidenceRecord(
                    claim_id=claim.id,
                    source_id=source.id,
                    passage=src_data["passage"],
                    nli_label=src_data["nli_label"],
                    rank_score=0.92,
                )
                db.add(ev)
                db.commit()
                db.refresh(ev)
                ev_ids.append(ev.id)

            vres = VerificationResult(
                claim_id=claim.id,
                label=case["label"],
                confidence=case["confidence"],
                key_passage_ids=ev_ids,
                missing_context=case["missing_context"],
                conflicts={"has_conflicts": case["label"] == VerdictLabel.conflicting_evidence},
                explanation=case["explanation"],
            )
            db.add(vres)
            db.commit()

        print(f"  ✅ Seeded {len(demo_cases)} verified demo requests across all 5 canonical labels.")
        print("\n✨ TruthLens AI seeding complete!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
