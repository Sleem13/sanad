"""Package installed model weights for Git LFS; excludes all document data."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "weights"
CHUNK = 1024**3  # below GitHub Free's per-object LFS limit


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=True)
    index = {"format": "sanad-weights-1", "files": [], "ollama_blobs": []}
    for group in ["paddle-vl", "layout"]:
        for source in (ROOT/"data/models"/group).iterdir():
            if source.suffix not in {".gguf", ".json", ".yml", ".pdiparams"}:
                continue
            target = OUTPUT/group/source.name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            index["files"].append({"path":target.relative_to(OUTPUT).as_posix(), "restore":"models/"+target.relative_to(OUTPUT).as_posix(), "sha256":digest(target)})
    for model in ["PP-OCRv5_server_det", "arabic_PP-OCRv5_mobile_rec"]:
        for name in ["inference.json","inference.yml","inference.pdiparams"]:
            source=Path.home()/".paddlex/official_models"/model/name
            target=OUTPUT/"arabic"/model/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            index["files"].append({"path":target.relative_to(OUTPUT).as_posix(),"restore":"paddlex/"+model+"/"+name,"sha256":digest(target)})
    source_root=Path.home()/".ollama/models"
    manifest_path=source_root/"manifests/registry.ollama.ai/library/gemma3/4b"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    target=OUTPUT/"ollama/gemma3-4b.manifest.json";target.parent.mkdir(exist_ok=True)
    shutil.copyfile(manifest_path,target)
    index["ollama_manifest"]={"path":"ollama/gemma3-4b.manifest.json","sha256":digest(target)}
    for layer in [manifest["config"],*manifest["layers"]]:
        identifier=layer["digest"]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}",identifier):
            raise ValueError("invalid model digest")
        name=identifier.replace(":","-");source=source_root/"blobs"/name
        parts=[]
        with source.open("rb") as stream:
            number=0
            while block:=stream.read(CHUNK):
                target=OUTPUT/"ollama/blobs"/(name+f".part{number:03}")
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(block)
                parts.append({"path":target.relative_to(OUTPUT).as_posix(),"bytes":len(block),"sha256":hashlib.sha256(block).hexdigest()})
                number+=1
        actual=digest(source)
        if actual!=identifier.split(":")[1]:raise ValueError("installed Ollama blob checksum mismatch")
        index["ollama_blobs"].append({"name":name,"sha256":actual,"parts":parts})
        if layer["mediaType"]=="application/vnd.ollama.image.license":
            shutil.copyfile(source,OUTPUT/"GEMMA-LICENSE.txt")
    shutil.copyfile(ROOT/"data/models/manifest.json",OUTPUT/"upstream-manifest.json")
    (OUTPUT/"index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")
    print("Bundled and verified model weights",flush=True)


if __name__=="__main__":
    main()
