"""Extract the pinned public sample into pending-review SANAD examples (no model needed)."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

EXPECTED_SHA256 = "3a7f36efd43e00ce0bbd9fd3e57914d990c4fc0552bd35bd1eb041fd3d7bb0cf"


def prepare(source: Path, output: Path):
    import pyarrow.parquet as parquet

    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError("source checksum differs from the inspected dataset revision")
    rows = parquet.read_table(source).to_pylist()
    # A fresh directory prevents accidentally replacing reviewed corrections.
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    manifest = []
    for index, row in enumerate(rows):
        if not isinstance(row["content"], str) or not row["doc_id"]:
            raise ValueError("missing transcription or document identity")
        image_name = f"images/{index:04d}.png"
        with Image.open(io.BytesIO(row["image"]["bytes"])) as image:
            image.convert("RGB").save(output / image_name)
        manifest.append({
            "id": f"egyptian-official-{index:04d}",
            "document_id": f"egyptian-official:{row['doc_id']}",
            "split": "test", "image": image_name, "text": row["content"], "reviewed": False,
            "source": "mohamedwasef/egyptian-official-documents-ocr",
            "source_revision": "ad2c38f5809d58d4ab475df26fd2bf750ab063a3",
            "annotation_license": "CC-BY-4.0", "source_page": row["page_index"],
            "source_image_name": row["image_name"], "source_status": row["status"],
            "review_notes": row["review_notes"], "elements": row["elements"],
            "target_convention": "publisher structured text; requires SANAD transcription-policy review",
        })
    (output / "pending_review.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    print(json.dumps({"pages": len(manifest), "documents": len({r['document_id'] for r in manifest}),
                      "reviewed": False, "output": str(output.resolve())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
