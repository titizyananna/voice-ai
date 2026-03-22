import os
import asyncio
import subprocess
import tempfile
import whisper
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import chromadb
from pathlib import Path
from openai import OpenAI

EMBED_MODEL = "Metric-AI/armenian-text-embeddings-2-large"
DB_DIR = "chroma_db"
CONFIDENCE_THRESHOLD = 0.4
OFF_TOPIC = "Ես չեմ կարող վստահ պատասխանել այս հարցին։"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BankRAG:
    def __init__(self):
        print("Loading embedding model...")
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
        self.emb_model = AutoModel.from_pretrained(EMBED_MODEL)
        self.emb_model.eval()
        self.collection = chromadb.PersistentClient(path=DB_DIR).get_collection("bank_knowledge")
        print(f"RAG ready — {self.collection.count()} chunks.")

    def _embed(self, text, prefix="query"):
        inputs = self.tokenizer(
            [f"{prefix}: {text}"],
            return_tensors="pt",
            truncation=True,
            padding=True
        )
        with torch.no_grad():
            hidden = self.emb_model(**inputs).last_hidden_state

        mask = inputs["attention_mask"]
        vec = hidden.masked_fill(~mask[..., None].bool(), 0.0).sum(1) / mask.sum(1)[..., None]
        return F.normalize(vec, p=2, dim=1)[0].tolist()

    def answer(self, question):
        query_vec = self._embed(question, prefix="query")

        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=3
        )

        docs = results["documents"][0]
        dists = results["distances"][0]

        sims = [1 - d for d in dists]

        print("\n--- RETRIEVAL DEBUG ---")
        for d, s in zip(docs, sims):
            print(f"{s:.2f} -> {d[:80]}")
        print("------------------------")

        best_sim = max(sims)

        if best_sim < CONFIDENCE_THRESHOLD:
            return OFF_TOPIC, best_sim

        best_idx = sims.index(best_sim)
        return docs[best_idx], best_sim

class WhisperSTT:
    def __init__(self):
        print("Loading Whisper medium...")
        self.model = whisper.load_model("medium")
        print("Whisper ready.")

    def transcribe(self, audio_file_path):
        result = self.model.transcribe(audio_file_path)  # auto language detection
        return result["text"].strip()

class ArmenianTTS:
    def __init__(self):
        self.client = client

    def speak(self, text):
        if not text.strip():
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name

        response = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )

        audio_bytes = response.read()

        with open(path, "wb") as f:
            f.write(audio_bytes)

        subprocess.run(["afplay", path])

async def handle_audio(stt, tts, rag, audio_file_path):
    print(f"\nProcessing: {audio_file_path}")

    user_text = stt.transcribe(audio_file_path)
    print(f"User said: {user_text}")

    answer, confidence = rag.answer(user_text)

    print(f"Confidence: {confidence*100:.2f}%")
    print(f"Assistant: {answer}")

    tts.speak(answer)

async def main():
    stt = WhisperSTT()
    tts = ArmenianTTS()
    rag = BankRAG()

    print("\nVoice assistant ready. Speak in Armenian...")

    while True:
        audio_file = input("\nEnter path to WAV file or 'quit': ").strip()

        if audio_file.lower() == "quit":
            break

        if not Path(audio_file).exists():
            print("File not found!")
            continue

        await handle_audio(stt, tts, rag, audio_file)

if __name__ == "__main__":
    asyncio.run(main())

