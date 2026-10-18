"""Verify Git LFS weights and restore local runtimes. No network requests."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import re

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only",action="store_true")
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--paddlex-dir",type=Path,default=Path.home()/".paddlex/official_models")
    parser.add_argument("--ollama-dir",type=Path,default=Path.home()/".ollama/models")
    args=parser.parse_args();weights=ROOT/"weights"
    index=json.loads((weights/"index.json").read_text(encoding="utf-8"))
    def checked(relative):
        path=(weights/relative).resolve()
        if not path.is_relative_to(weights.resolve()):raise ValueError("unsafe weight path")
        return path
    for row in index["files"]:
        source=checked(row["path"])
        if digest(source)!=row["sha256"]:raise ValueError("weight missing or corrupt; run git lfs pull: "+row["path"])
        if not args.verify_only:
            prefix,relative=row["restore"].split("/",1)
            if prefix not in {"models", "paddlex"}:raise ValueError("unknown restore destination")
            base=args.data_dir/"models" if prefix=="models" else args.paddlex_dir
            target=(base/relative).resolve()
            if not target.is_relative_to(base.resolve()):raise ValueError("unsafe restore path")
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and digest(target)!=row["sha256"]:raise ValueError("existing weight differs: "+str(target))
            if not target.exists():shutil.copyfile(source,target)
    for row in index["ollama_blobs"]:
        if not re.fullmatch(r"sha256-[a-f0-9]{64}",row["name"]) or row["name"] != "sha256-"+row["sha256"]:
            raise ValueError("invalid Ollama blob identity")
        combined=hashlib.sha256()
        target=args.ollama_dir/"blobs"/row["name"]
        temp=target.with_suffix(".restore")
        if not args.verify_only:
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and digest(target)!=row["sha256"]:raise ValueError("existing Ollama blob differs")
        output=temp.open("wb") if not args.verify_only and not target.exists() else None
        try:
            for part in row["parts"]:
                source=checked(part["path"])
                if digest(source)!=part["sha256"]:raise ValueError("missing/corrupt LFS part: "+part["path"])
                with source.open("rb") as stream:
                    while chunk:=stream.read(1024*1024):
                        combined.update(chunk)
                        if output:output.write(chunk)
            if combined.hexdigest()!=row["sha256"]:raise ValueError("reassembled blob checksum mismatch")
        finally:
            if output:output.close()
        if output:temp.replace(target)
    manifest=index["ollama_manifest"];source=checked(manifest["path"])
    if digest(source)!=manifest["sha256"]:raise ValueError("model manifest checksum mismatch")
    if not args.verify_only:
        target=args.ollama_dir/"manifests/registry.ollama.ai/library/gemma3/4b"
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target)!=manifest["sha256"]:raise ValueError("existing Ollama manifest differs")
        shutil.copyfile(source,target)
    print("All bundled weights verified"+(" and restored" if not args.verify_only else ""))


if __name__=="__main__":main()
