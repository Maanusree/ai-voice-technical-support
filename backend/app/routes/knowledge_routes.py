"""
Knowledge Base and Support Scenarios Routes
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..services.rag_service import rag_service

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


@router.get("/articles")
async def list_articles():
    """Returns all technical troubleshooting articles and decision flows."""
    return {"articles": rag_service.knowledge_base.articles}


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    article = rag_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/search")
async def search_knowledge(q: str = Query(..., min_length=1)):
    """Search knowledge base articles and FAQs by keyword or problem statement."""
    results = rag_service.search_articles(q, top_k=5)
    formatted = []
    for article, score in results:
        formatted.append({
            "id": article.id,
            "title": article.title,
            "category": article.category,
            "summary": article.summary,
            "relevance_score": round(score, 2),
            "step_count": len(article.diagnostic_flow)
        })
    faq = rag_service.match_faq(q)
    return {
        "query": q,
        "matched_articles": formatted,
        "matched_faq": faq
    }


@router.get("/faqs")
async def list_faqs():
    all_faqs = list(rag_service.knowledge_base.general_faqs)
    for art in rag_service.knowledge_base.articles:
        all_faqs.extend(art.faqs)
    return {"faqs": all_faqs}
