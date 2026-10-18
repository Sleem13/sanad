"""Export only human-approved, fully resolved pages for VLM evaluation/training.

Never includes unreviewed publisher labels or unapproved model predictions.
Run: python scripts/export_approved_dataset.py NEW_OUTPUT_DIRECTORY
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image
from sanad.config import Settings
from sanad import db as D
from sanad.canonical import CanonicalPage, NON_TEXT_LABELS


def export(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    cfg = Settings.from_env()
    sf = D.make_session_factory(cfg.db_url)
    records, skipped = [], 0
    with sf() as session:
        for page in session.query(D.Page).filter_by(status="approved"):
            version = session.query(D.PageVersion).filter_by(page_id=page.id).order_by(D.PageVersion.version_no.desc()).first()
            if not version or version.kind != "approved" or version.is_mock:
                skipped += 1; continue
            content = CanonicalPage.model_validate(version.content)
            if any(r.status.value not in {"recognized", "not_present"} and r.label not in NON_TEXT_LABELS for r in content.regions):
                skipped += 1; continue
            document = session.get(D.Document, page.document_id)
            artifact = session.get(D.SourceArtifact, document.artifact_id)
            if artifact.is_synthetic_demo:
                skipped += 1; continue
            with Image.open(artifact.storage_path) as image:
                suffix = {"JPEG": ".jpg", "PNG": ".png", "TIFF": ".tiff"}[image.format]
            name = artifact.sha256 + suffix
            destination = output / "images" / name
            if not destination.exists():
                shutil.copyfile(artifact.storage_path, destination)
            if hashlib.sha256(destination.read_bytes()).hexdigest() != artifact.sha256:
                raise ValueError("archived source checksum mismatch")
            bucket = int(artifact.sha256[:8], 16) % 100
            records.append({"id": page.id+":"+str(version.version_no), "document_id": "source:"+artifact.sha256,
                "split": "train" if bucket < 80 else "dev" if bucket < 90 else "test",
                "image": "images/"+name, "text": content.text_in_reading_order(), "reviewed": True,
                "approved_version_id": version.id, "source_sha256": artifact.sha256,
                "regions": content.model_dump(mode="json")["regions"]})
    (output / "manifest.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8")
    print(json.dumps({"exported":len(records),"skipped":skipped,"manifest":str(output/"manifest.jsonl")}))


if __name__ == "__main__":
    export(sys.argv[1])
