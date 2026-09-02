"""
RAG (Retrieval-Augmented Generation) & Knowledge Base Search Service
"""
import json
import re
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from ..config import settings
from ..models.knowledge import KnowledgeBase, KnowledgeArticle, TroubleshootingStep, FAQItem

STOPWORDS = {
    "a", "an", "the", "is", "it", "my", "to", "for", "in", "of", "and", "or",
    "how", "what", "why", "can", "you", "me", "do", "i", "have", "on", "with", "this", "that"
}


class RAGService:
    def __init__(self, kb_file: Optional[Path] = None):
        self.kb_file = kb_file or settings.KB_PATH
        self.knowledge_base: KnowledgeBase = self._load_knowledge_base()

    def _load_knowledge_base(self) -> KnowledgeBase:
        if not self.kb_file.exists():
            return KnowledgeBase()
        try:
            with open(self.kb_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return KnowledgeBase(**data)
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return KnowledgeBase()

    def search_articles(self, query: str, top_k: int = 2) -> List[Tuple[KnowledgeArticle, float]]:
        """
        Rank articles based on keyword matching, token overlap, and title relevance.
        Supports both English and Tamil/Tanglish terminology.
        Returns list of (article, score) tuples.
        """
        if not query or not self.knowledge_base.articles:
            return []

        q_lower = query.lower()
        all_tokens = set(re.findall(r"\w+", q_lower))
        content_tokens = all_tokens - STOPWORDS
        if not content_tokens and not any('\u0B80' <= c <= '\u0BFF' for c in query):
            return []

        # Category keyword map for rapid semantic routing
        category_synonyms = {
            "kb_network_wifi": ["wifi", "wi-fi", "internet", "net", "network", "router", "modem", "connection", "disconnected", "offline", "dns", "lan", "wan", "broadband", "speed", "slow net", "வைபை", "இன்டர்நெட்", "நெட்வொர்க்", "வலைப்பின்னல்", "ரூட்டர்", "வரல", "கனெக்ட்"],
            "kb_account_password": ["password", "passcode", "account", "login", "locked", "lockout", "reset", "forgot", "2fa", "mfa", "otp", "credentials", "கடவுச்சொல்", "லாகின்", "பாஸ்வேர்ட்", "கணக்கு", "மறந்து"],
            "kb_hardware_printer": ["printer", "print", "printing", "offline", "paper jam", "spooler", "cartridge", "toner", "scanner", "பிரிண்டர்", "அச்சுப்பொறி", "பேப்பர்"],
            "kb_os_bsod_performance": ["slow", "freeze", "freezing", "crash", "bsod", "blue screen", "performance", "cpu", "memory", "ram", "hang", "restart", "sluggish", "lag", "வேகம்", "ஹேங்", "ப்ளூ ஸ்கிரீன்", "மெதுவாக"],
            "kb_software_install": ["install", "installation", "update", "0x80070005", "access denied", "setup", "installer", "software", "நிறுவல்", "இன்ஸ்டால்"],
            "kb_critical_escalation": ["smoke", "burning", "fire", "spark", "liquid", "spill", "water", "supervisor", "human", "agent", "manager", "புகை", "தீ", "தண்ணீர்", "மேலாளர்", "மனிதர்", "எரியுது"]
        }

        scored_articles: List[Tuple[KnowledgeArticle, float]] = []

        for article in self.knowledge_base.articles:
            score = 0.0

            # Direct synonym matching
            if article.id in category_synonyms:
                for syn in category_synonyms[article.id]:
                    if syn in q_lower:
                        score += 5.0

            # 1. Title match
            title_tokens = set(re.findall(r"\w+", article.title.lower())) - STOPWORDS
            common_title = content_tokens.intersection(title_tokens)
            score += len(common_title) * 5.0

            # 2. Keywords match
            for kw in article.keywords:
                kw_lower = kw.lower()
                if kw_lower in q_lower:
                    score += 6.0
                else:
                    kw_tokens = set(re.findall(r"\w+", kw_lower)) - STOPWORDS
                    if kw_tokens and kw_tokens.issubset(content_tokens):
                        score += 3.0

            # 3. Symptoms match
            for symptom in article.common_symptoms:
                sym_tokens = set(re.findall(r"\w+", symptom.lower())) - STOPWORDS
                score += len(content_tokens.intersection(sym_tokens)) * 2.0

            # 4. Summary match
            summary_tokens = set(re.findall(r"\w+", article.summary.lower())) - STOPWORDS
            score += len(content_tokens.intersection(summary_tokens)) * 0.5

            if score > 0:
                scored_articles.append((article, score))

        scored_articles.sort(key=lambda x: x[1], reverse=True)
        return scored_articles[:top_k]

    def find_best_article(self, query: str) -> Optional[KnowledgeArticle]:
        results = self.search_articles(query, top_k=1)
        if results and results[0][1] >= 2.5:
            return results[0][0]
        return None

    def get_article_by_id(self, article_id: str) -> Optional[KnowledgeArticle]:
        for article in self.knowledge_base.articles:
            if article.id == article_id:
                return article
        return None

    def match_faq(self, query: str) -> Optional[FAQItem]:
        """Check if query is directly asking a known informational FAQ."""
        query_lower = query.lower().strip()
        all_tokens = set(re.findall(r"\w+", query_lower))
        content_tokens = all_tokens - STOPWORDS

        if len(content_tokens) == 0:
            return None

        # FAQ matching should be selective for explicit questions
        question_signals = {"what", "when", "where", "how", "who", "hours", "status", "track", "reset", "change"}
        is_question = bool(all_tokens.intersection(question_signals)) or "?" in query

        best_faq: Optional[FAQItem] = None
        best_score = 0.0

        all_faqs: List[FAQItem] = list(self.knowledge_base.general_faqs)
        for article in self.knowledge_base.articles:
            all_faqs.extend(article.faqs)

        for faq in all_faqs:
            score = 0.0
            q_tokens = set(re.findall(r"\w+", faq.question.lower())) - STOPWORDS
            matched = content_tokens.intersection(q_tokens)
            score += len(matched) * 3.0

            for kw in faq.keywords:
                kw_lower = kw.lower()
                if kw_lower in query_lower:
                    score += 5.0

            # Require strong match
            min_thresh = 5.0 if is_question else 8.0
            if score > best_score and score >= min_thresh:
                best_score = score
                best_faq = faq

        return best_faq

    def evaluate_step_response(
        self,
        step: TroubleshootingStep,
        user_reply: str
    ) -> Tuple[str, float]:
        """
        Evaluates user response to a diagnostic step question.
        Returns: ("positive" | "negative" | "unclear", confidence)
        """
        reply_lower = user_reply.lower().strip()
        tokens = set(re.findall(r"\w+", reply_lower))

        # Explicit unclear / confusion phrases
        unclear_phrases = [
            "don't know", "dont know", "not sure", "unsure", "maybe",
            "idk", "cannot tell", "no idea", "hard to say", "confused", "which one",
            "therila", "purila", "தெரியவில்லை", "புரியவில்லை"
        ]
        if any(phrase in reply_lower for phrase in unclear_phrases):
            return "unclear", 0.2

        # Check positive indicators
        pos_score = 0
        for ind in step.positive_indicators:
            if ind.lower() in reply_lower:
                pos_score += 3
            elif set(re.findall(r"\w+", ind.lower())).intersection(tokens):
                pos_score += 1

        # Check negative indicators
        neg_score = 0
        for ind in step.negative_indicators:
            if ind.lower() in reply_lower:
                neg_score += 3
            elif set(re.findall(r"\w+", ind.lower())).intersection(tokens):
                neg_score += 1

        # General affirmative & negative words (English, Tamil, Tanglish)
        general_affirmative = {
            "yes", "yeah", "yep", "sure", "done", "fixed", "worked", "working", "good", "ready", "ok", "okay", "fine",
            "aama", "aam", "seri", "sari", "velai seiyuthu", "work aaguthu", "pachai", "green", "green light",
            "sari aaiduchu", "fixed", "repaired", "solved", "all good", "solid green", "ஆமா", "ஆம்", "சரி", "வேலை செய்கிறது"
        }
        general_negative = {
            "no", "nope", "not", "didn't", "failed", "error", "still", "broken", "unresolved",
            "illa", "illai", "velai seiyala", "work aagala", "red", "red light", "orange", "amber", "sivappu",
            "same problem", "same issue", "innum varala", "marubadiyum", "blinking", "off", "இல்லை", "சிவப்பு", "வேலை செய்யவில்லை"
        }

        if any(w in reply_lower for w in general_affirmative) or any(w in tokens for w in general_affirmative):
            pos_score += 2
        if any(w in reply_lower for w in general_negative) or any(w in tokens for w in general_negative):
            neg_score += 2

        if pos_score > neg_score and pos_score >= 2:
            return "positive", min(1.0, pos_score / 4.0)
        elif neg_score > pos_score and neg_score >= 2:
            return "negative", min(1.0, neg_score / 4.0)
        else:
            return "unclear", 0.3


rag_service = RAGService()

