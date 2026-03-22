import os, json, glob, re
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import chromadb

MODEL    = "Metric-AI/armenian-text-embeddings-2-large"
DATA_DIR = "data/scraped"
DB_DIR   = "chroma_db"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model= AutoModel.from_pretrained(MODEL)
model.eval()
print("Model ready.\n")

def clean_text(text: str) -> str:
    text = re.sub(r'\b(ՀԱՅ|EN|РУ|IR)\b', '', text)
    noise = [
        "Դիմել հիմա", "Իմանալ ավելին", "Դիմել օնլայն",
        "Տեսնել բոլորը", "Ավելին", "Loan calculator",
        "Վարկային հաշվիչ", "Ավանդի հաշվիչ",
        "Հարգելի հաճախորդ, հաշվարկը կրում է տեղեկատվական բնույթ",
        "և կարող է փոփոխվել",
        "Հարցեր ունե՞ս", "Ասա կարծիքդ",
        "Թարմացված է առ",
        "arrow_drop_down", "chevron_left", "chevron_right",
        "expand_more",
    ]
    for phrase in noise:
        text = text.replace(phrase, " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def embed(texts, prefix="passage"):
    inputs = tokenizer(
        [f"{prefix}: {t}" for t in texts],
        max_length=512,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    with torch.no_grad():
        hidden = model(**inputs).last_hidden_state

    mask = inputs["attention_mask"]
    vecs = hidden.masked_fill(~mask[..., None].bool(), 0.0).sum(1) / mask.sum(1)[..., None]
    return F.normalize(vecs, p=2, dim=1).tolist()

def split_text(text, max_len=500, overlap=100):
    sentences = re.split(r'(?<=[.!?։])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) < max_len:
            current += " " + sent
        else:
            chunks.append(current.strip())
            current = current[-overlap:] + " " + sent
    if current.strip():
        chunks.append(current.strip())
    return chunks

# ── BUILD CHUNKS ─────────────────────────────────────────
chunks = []

for filepath in glob.glob(os.path.join(DATA_DIR, "*.json")):
    data = json.load(open(filepath, encoding="utf-8"))
    bank = data["bank"]
    print(f"Loading {bank}...")
    for topic in ["credits", "deposits"]:
        for item in data.get(topic, []):
            if not item.get("details"):
                continue
            full_text = clean_text(f"{bank} — {item['title']}։ {item['details']}")
            for chunk_text in split_text(full_text):
                chunks.append({
                    "text": chunk_text,
                    "bank": bank,
                    "topic": topic,
                    "title": item["title"],
                })
    for branch in data.get("branches", []):
        text = f"""
Բանկ՝ {bank}
Մասնաճյուղ՝ {branch.get('name','')}
Հասցե՝ {branch.get('address','')}
Աշխատաժամեր՝ {branch.get('working_hours', branch.get('schedule',''))}
Հեռախոս՝ {branch.get('phone','')}
""".strip()

        if not branch.get("address"):
            continue
        for chunk_text in split_text(text, max_len=300):
            chunks.append({
                "text": chunk_text,
                "bank": bank,
                "topic": "branches",
                "title": branch.get("name", ""),
            })

    print(f"  {sum(1 for c in chunks if c['bank'] == bank)} chunks")

print(f"\nTotal chunks: {len(chunks)}")

client = chromadb.PersistentClient(path=DB_DIR)

try:
    client.delete_collection("bank_knowledge")
except:
    pass

collection = client.create_collection(
    name="bank_knowledge",
    metadata={"hnsw:space": "cosine"}
)

BATCH = 16

for i in range(0, len(chunks), BATCH):
    batch = chunks[i:i+BATCH]

    collection.add(
        ids=[f"c{i+j}" for j in range(len(batch))],
        documents=[c["text"] for c in batch],
        embeddings=embed([c["text"] for c in batch]),
        metadatas=[
            {"bank": c["bank"], "topic": c["topic"], "title": c["title"]}
            for c in batch
        ],
    )

    print(f"Stored {min(i+BATCH, len(chunks))}/{len(chunks)}")

print("\nDone! ChromaDB is ready.")

# ── TEST ─────────────────────────────────────────────────
print("\n--- TEST ---")

queries = [
    "վարկի տոկոս",
    "ավանդի պայմաններ",
    "մասնաճյուղ Երևան"
]

for q in queries:
    result = collection.query(
        query_embeddings=embed([q], prefix="query"),
        n_results=3
    )

    print(f"\nQ: {q}")
    for doc, meta in zip(result["documents"][0], result["metadatas"][0]):
        print(f"  [{meta['topic']}] {doc[:100]}...")