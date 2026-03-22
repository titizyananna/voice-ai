import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyDXXrCSAFwSzzIZr7q4tv_1tGDaaNo4fWo"
OFF_TOPIC = "Ես չեմ կարող պատասխանել ձեր հարցին, կներեք։"

SYSTEM_PROMPT = """Դու հայկական բանկերի AI օգնականն ես։
Պատասխանիր ՄԻԱՅՆ ստորև տրված տեղեկատվության հիման վրա։
Արտաքին գիտելիքներ մի օգտագործիր։
Պատասխանիր հայերեն։
Եթե տեղեկատվությունը բազայում չկա, ասա որ չգիտես։"""


class LLM:

    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        print("Gemini ready.")

    def answer(self, question: str, chunks: list[dict]) -> str:
        context = "\n\n".join(c["text"] for c in chunks)

        prompt = f"""{SYSTEM_PROMPT}

ՏԵՂԵԿԱՏՎՈՒԹՅՈՒՆ՝
{context}

ՀԱՐՑԸ՝
{question}

ՊԱՏԱՍԽԱՆ՝"""

        response = self.model.generate_content(prompt)
        return response.text.strip()


llm = LLM()

chunks = [{
        "text": "Ameriabank — Սպառողական վարկ։ Անվանական տոկոսադրույք 15-21%։ Մարման ժամկետ մինչև 60 ամիս։",
        "bank": "Ameriabank",
        "topic": "credits",
}]

q = "Ամերիաբանկի սպառողական վարկի տոկոսը քանի՞ տոկոս է"
print(f"Q: {q}")
print(f"A: {llm.answer(q, chunks)}")