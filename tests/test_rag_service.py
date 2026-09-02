"""
Tests for RAG Knowledge Base and Step Evaluation
"""
import pytest
from backend.app.services.rag_service import rag_service
from backend.app.models.knowledge import TroubleshootingStep


def test_knowledge_base_articles_loaded():
    articles = rag_service.knowledge_base.articles
    assert len(articles) >= 5, "Knowledge base should have at least 5 articles"
    ids = [a.id for a in articles]
    assert "kb_network_wifi" in ids
    assert "kb_account_password" in ids
    assert "kb_hardware_printer" in ids
    assert "kb_os_bsod_performance" in ids
    assert "kb_software_install" in ids
    assert "kb_critical_escalation" in ids


def test_search_articles_wifi():
    results = rag_service.search_articles("my wifi keeps dropping and internet is not working")
    assert len(results) > 0
    top_article, score = results[0]
    assert top_article.id == "kb_network_wifi"
    assert score > 0


def test_search_articles_printer():
    results = rag_service.search_articles("printer is offline and paper jam error")
    assert len(results) > 0
    top_article, score = results[0]
    assert top_article.id == "kb_hardware_printer"


def test_match_general_faq():
    faq = rag_service.match_faq("what are your support hours?")
    assert faq is not None
    assert "24 hours" in faq.answer.lower()


def test_evaluate_step_response():
    step = TroubleshootingStep(
        step_number=1,
        instruction="Check router light",
        expected_result="Green light",
        follow_up_question="Is the light green?",
        positive_indicators=["solid green", "green", "yes"],
        negative_indicators=["red", "orange", "blinking red", "no"]
    )

    pos_eval, conf_pos = rag_service.evaluate_step_response(step, "Yes it is solid green now")
    assert pos_eval == "positive"

    neg_eval, conf_neg = rag_service.evaluate_step_response(step, "No it is still blinking red")
    assert neg_eval == "negative"

    unc_eval, conf_unc = rag_service.evaluate_step_response(step, "I don't know maybe")
    assert unc_eval == "unclear"
