import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CATEGORY_RULES = {
    "api_integration": ("api", "endpoint", "integration", "webhook", "token", "401", "403"),
    "billing": ("invoice", "payment", "refund", "charged", "billing", "subscription"),
    "delivery": ("delivery", "shipment", "tracking", "courier", "parcel", "late"),
    "account": ("login", "password", "account", "sign in", "profile", "locked"),
}

def classify_ticket(subject: str, message: str) -> dict:
    text = f"{subject} {message}".lower()
    category, best_count = "general", 0
    for label, keywords in CATEGORY_RULES.items():
        count = sum(1 for word in keywords if word in text)
        if count > best_count:
            category, best_count = label, count
    urgent_terms = ("urgent", "asap", "immediately", "blocked", "outage", "down", "cannot process")
    negative_terms = ("angry", "frustrated", "unacceptable", "terrible", "disappointed", "not working")
    escalation_terms = ("legal action", "lawyer", "complaint", "data breach", "security incident")
    urgent = any(term in text for term in urgent_terms)
    escalated = any(term in text for term in escalation_terms)
    negative = any(term in text for term in negative_terms) or escalated
    priority = "critical" if escalated or ("outage" in text and urgent) else "high" if urgent else "normal"
    return {"category": category, "priority": priority,
            "sentiment": "negative" if negative else "neutral", "escalated": escalated}

def retrieve_articles(question: str, articles: list, top_k: int = 3):
    if not articles:
        return []
    docs = [f"{a.title} {a.tags} {a.content}" for a in articles]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(docs + [question])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return [(articles[i], float(score)) for i, score in ranked[:top_k] if score > 0.01]

def fallback_answer(question: str, matches: list) -> str:
    if not matches:
        return "I couldn't find a sufficiently relevant knowledge-base article. Please create a support ticket or add an article on this topic."
    parts = []
    for article, _score in matches:
        excerpt = re.sub(r"\s+", " ", article.content).strip()
        parts.append(f"**{article.title}:** {excerpt[:700]}")
    return "I found this information in the support knowledge base. Please verify it for your specific account or integration.\n\\n" + "\\n\\n".join(parts)

def generate_answer(question: str, matches: list, api_key: str | None, model: str):
    if api_key and matches:
        try:
            from openai import OpenAI
            context = "\\n\\n".join(f"Source: {a.title}\\n{a.content}" for a, _ in matches)
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model, temperature=0.2,
                messages=[
                    {"role": "system", "content": "Answer only from the supplied knowledge-base context. If it lacks the answer, say so. Never invent account-specific facts or policies."},
                    {"role": "user", "content": f"Question: {question}\\n\\nContext:\\n{context}"},
                ],
            )
            return response.choices[0].message.content or fallback_answer(question, matches), "openai_rag"
        except Exception:
            return fallback_answer(question, matches), "local_fallback"
    return fallback_answer(question, matches), "local_tfidf"
