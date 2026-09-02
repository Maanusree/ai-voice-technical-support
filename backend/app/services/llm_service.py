"""
Multi-Provider LLM & AI Reasoning Engine
Supports Gemini, OpenAI, Groq, and a Built-in Offline Diagnostic Engine.
"""
import time
import os
import re
import json
from typing import Dict, Any, Optional, List
from ..config import settings
from ..models.call_session import CallSession, ResolutionStatus, CallStatus
from ..models.ticket import TicketPriority
from .rag_service import rag_service
from .escalation_service import escalation_service

SYSTEM_SUPPORT_PROMPT = """You are Maanu, an expert Tier-1 Technical Support Voice Specialist at InnoAssist.
Your goal is to guide the customer through troubleshooting their technical issue step-by-step in natural, conversational spoken English.

LANGUAGE & VOICE RESPONSE RULES:
1. Speak in clear, professional English by default.
2. Only switch to Tamil (தமிழ்) if the customer explicitly requests or insists on speaking in Tamil.
3. Speak naturally and concisely (1-3 sentences maximum per turn).
4. Avoid bullet points, markdown symbols, asterisks, URLs, or long lists.
5. Guide the caller ONE step at a time. Ask them to perform the step and wait for their confirmation.
6. If the user states a step worked and the issue is resolved, warmly congratulate them and ask if they need anything else.
7. If the issue is critical (smoke, fire, data loss) or the customer is demanding a human/supervisor, immediately offer an escalation transfer.
8. Be empathetic, calm, and reassuring.

KNOWLEDGE CONTEXT:
{knowledge_context}

CALL HISTORY:
{call_history}
"""


class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()

    def set_provider(self, provider: str):
        self.provider = provider.lower()

    async def generate_response(
        self,
        session: CallSession,
        user_message: str
    ) -> Dict[str, Any]:
        start_time = time.time()
        user_message_clean = user_message.strip()

        # Update session sentiment
        sentiment = escalation_service.analyze_sentiment(user_message_clean)
        session.sentiment = sentiment

        # Check for explicit language switch requests
        msg_lower = user_message_clean.lower()
        if any(p in msg_lower for p in ["speak in tamil", "talk in tamil", "tamil la pesunga", "tamil la sollunga", "தமிழில் பேசுங்கள்", "tamil please", "can you speak tamil", "tamil theriyuma", "switch to tamil"]):
            session.language = "ta"
            return {
                "text": "Sure! I can certainly assist you in Tamil. வணக்கம்! உங்கள் தொழில்நுட்ப பிரச்சனையை கூறுங்கள், நான் உதவுகிறேன்.",
                "intent": "language_switch_tamil",
                "should_escalate": False,
                "ticket_id": None,
                "latency_ms": (time.time() - start_time) * 1000,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": False
            }
        elif any(p in msg_lower for p in ["speak in english", "talk in english", "english please", "switch to english", "english la pesunga"]):
            session.language = "en"
            return {
                "text": "Certainly! I have switched back to English. How can I assist you with your technical issue today?",
                "intent": "language_switch_english",
                "should_escalate": False,
                "ticket_id": None,
                "latency_ms": (time.time() - start_time) * 1000,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": False
            }

        # Check for immediate escalation triggers (Safety hazard / human request / high frustration)
        should_escalate, priority, reason = escalation_service.check_escalation_triggers(
            user_message_clean, session
        )

        if should_escalate:
            ticket = escalation_service.create_escalation_ticket(
                session=session,
                reason=reason or "Escalation requested",
                priority=priority or TicketPriority.MEDIUM,
                issue_category=session.issue_category
            )
            if any('\u0B80' <= c <= '\u0BFF' for c in user_message_clean) or any(w in user_message_clean.lower() for w in ["manushan", "theerala", "solve aagala", "seriyagala", "escalate pannunga"]):
                escalation_text = (
                    f"நான் புரிந்து கொள்கிறேன். உங்கள் பிரச்சனையை தீர்க்க, உடனடியாக எங்கள் சீனியர் மனித தொழில்நுட்ப நிபுணரிடம் இணைக்கிறேன். "
                    f"உங்கள் டிக்கெட் எண் {ticket.ticket_id}. தயவுசெய்து இணைப்பில் காத்திருக்கவும்."
                )
            else:
                escalation_text = (
                    f"I completely understand. For your assistance, I am transferring you directly to our "
                    f"Senior Technical Support Specialist. Your reference ticket number is {ticket.ticket_id}. "
                    f"Please hold while I connect you right away."
                )
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "text": escalation_text,
                "intent": "escalate",
                "should_escalate": True,
                "ticket_id": ticket.ticket_id,
                "latency_ms": elapsed_ms,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": False
            }

        # Try API-based LLM if configured and keys exist
        api_response = None
        if self.provider in ("gemini", "openai", "groq", "auto"):
            if self.provider == "gemini" or (self.provider == "auto" and (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY"))):
                api_response = await self._call_gemini(session, user_message_clean)
            elif self.provider == "openai" or (self.provider == "auto" and (settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))):
                api_response = await self._call_openai(session, user_message_clean)
            elif self.provider == "groq" or (self.provider == "auto" and (settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY"))):
                api_response = await self._call_groq(session, user_message_clean)

        if api_response:
            elapsed_ms = (time.time() - start_time) * 1000
            api_response["latency_ms"] = elapsed_ms
            return api_response

        # Fallback to Built-in Offline Diagnostic Reasoning Engine
        offline_res = self._run_offline_diagnostic_engine(session, user_message_clean)
        elapsed_ms = (time.time() - start_time) * 1000
        offline_res["latency_ms"] = elapsed_ms
        return offline_res

    def _match_conversational_intent(self, session: CallSession, msg: str) -> Optional[Dict[str, Any]]:
        """
        Handles human-like general conversation, identity questions, greetings,
        and audio checks naturally like a real AI agent in English and Tamil.
        """
        m = msg.lower().strip()
        tokens = set(re.findall(r"\w+", m))
        is_tamil = any('\u0B80' <= c <= '\u0BFF' for c in msg) or getattr(session, "language", "en") in ("ta", "ta-IN") or any(w in m for w in ["peyar", "epdi irukinga", "vanakkam", "sollunga", "peru enna", "purila", "marubadiyum"])

        # 1. Agent Name & Identity Question
        if any(p in m for p in ["your name", "who are you", "what is your name", "who am i talking to", "who am i speaking with", "what should i call you", "tell me your name", "who's this", "who is this", "un peyar", "unga peru", "per enna", "பெயர்", "யார்", "பேரு"]):
            if is_tamil:
                text = f"என் பெயர் {settings.AGENT_NAME}! நான் {settings.SUPPORT_COMPANY} நிறுவனத்தின் AI தொழில்நுட்ப ஆதரவு நிபுணர். உங்களுக்கு நான் எவ்வாறு உதவ முடியும்?"
            else:
                text = f"My name is {settings.AGENT_NAME}! I am your AI Technical Support Specialist here at {settings.SUPPORT_COMPANY}. How can I help you today?"
            return {"text": text, "intent": "agent_identity", "should_escalate": False, "ticket_id": None, "scenario_id": session.diagnostics.scenario_id, "is_resolved": False}

        # 2. AI vs Human / Robot Query
        if any(p in m for p in ["are you ai", "are you an ai", "are you a robot", "are you a bot", "are you human", "are you real", "are you a real person", "ரோபோ", "மனிதன்", "ஏஐ"]):
            if is_tamil:
                text = f"நான் {settings.AGENT_NAME}, ஒரு புத்திசாலி AI தொழில்நுட்ப உதவியாளர். உங்கள் கணினி அல்லது நெட்வொர்க் பிரச்சனைகளை சரிசெய்ய நான் பயிற்சி பெற்றுள்ளேன். மனித நிபுணர் தேவைப்பட்டால் உடனடியாக இணைப்பேன்!"
            else:
                text = f"I am {settings.AGENT_NAME}, an autonomous AI Technical Specialist for {settings.SUPPORT_COMPANY}. I can troubleshoot your Wi-Fi, printer, or computer issues, and if needed, I can connect you to a human supervisor anytime!"
            return {"text": text, "intent": "bot_identity", "should_escalate": False, "ticket_id": None, "scenario_id": session.diagnostics.scenario_id, "is_resolved": False}

        # 3. Audibility / Can you hear me
        if any(p in m for p in ["can you hear me", "am i audible", "are you listening", "hello can you hear", "hear me", "kekutha", "kekudha", "கேட்கிறதா", "கேக்குதா"]):
            if is_tamil:
                text = "ஆம், உங்கள் குரல் தெளிவாக கேட்கிறது! உங்கள் பிரச்சனையை தயவுசெய்து கூறுங்கள்."
            else:
                text = "Yes, I can hear you loud and clear! Please tell me what technical issue you're experiencing, and I will help you fix it."
            return {"text": text, "intent": "audio_check", "should_escalate": False, "ticket_id": None, "scenario_id": session.diagnostics.scenario_id, "is_resolved": False}

        # 4. How are you / Well-being
        if any(p in m for p in ["how are you", "how are you doing", "how do you do", "epdi irukinga", "எப்படி இருக்கிறீர்கள்", "எப்படி இருக்கீங்க", "நலமா"]):
            if is_tamil:
                text = "நான் மிகவும் நலமாக உள்ளேன், நன்றி! உங்களுக்கு இன்று என்ன தொழில்நுட்ப உதவி தேவைப்படுகிறது?"
            else:
                text = f"I'm doing great, thank you for asking! How can I assist you with your technical support today?"
            return {"text": text, "intent": "wellbeing", "should_escalate": False, "ticket_id": None, "scenario_id": session.diagnostics.scenario_id, "is_resolved": False}

        # 5. Repetition / Say Again
        if any(p in m for p in ["repeat", "say again", "say that again", "what did you say", "pardon", "can you repeat", "purila", "marubadiyum sollunga", "திரும்ப சொல்லு"]):
            if session.diagnostics.scenario_id:
                art = rag_service.get_article_by_id(session.diagnostics.scenario_id)
                if art and session.diagnostics.current_step_index < len(art.diagnostic_flow):
                    step = art.diagnostic_flow[session.diagnostics.current_step_index]
                    if is_tamil:
                        rep_text = f"மீண்டும் கூறுகிறேன்: {step.instruction} {step.follow_up_question}"
                    else:
                        rep_text = f"I'm happy to repeat: {step.instruction} {step.follow_up_question}"
                    return {"text": rep_text, "intent": "repeat_step", "should_escalate": False, "ticket_id": None, "scenario_id": art.id, "is_resolved": False}

        # 6. Greetings / Hello / Hi (only when it is a pure greeting without a technical issue)
        greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "vanakkam", "namaste", "வணக்கம்", "நமஸ்தே", "ஹலோ", "ஹாய்"]
        is_pure_greeting = (m in greeting_words or (any(m.startswith(g) for g in greeting_words) and len(tokens) <= 3))
        has_tech_keywords = any(kw in m for kw in ["wifi", "wi-fi", "internet", "net", "router", "printer", "print", "password", "account", "login", "lock", "freeze", "crash", "bsod", "slow", "install", "error", "smoke", "fire", "issue", "problem", "broken", "connect", "down"])

        if not session.diagnostics.scenario_id and is_pure_greeting and not has_tech_keywords:
            if is_tamil:
                text = f"வணக்கம்! நான் {settings.AGENT_NAME}. உங்கள் நெட்வொர்க், பிரிண்டர் அல்லது கணினி பிரச்சனைகளை தீர்க்க நான் தயார். உங்களுக்கு என்ன உதவி வேண்டும்?"
            else:
                text = f"Hello! Welcome to {settings.SUPPORT_COMPANY}. My name is {settings.AGENT_NAME}. Please describe the technical issue you're facing, such as Wi-Fi, printer, or computer performance."
            return {"text": text, "intent": "greeting", "should_escalate": False, "ticket_id": None, "scenario_id": None, "is_resolved": False}

        # 7. Company / Service Info
        if any(p in m for p in ["what company", "who is innoassist", "about innoassist", "what services", "what do you do", "what can you do", "what do you support", "நிறுவனம்", "சேவைகள்", "என்ன செய்கிறீர்கள்"]):
            if is_tamil:
                text = f"{settings.SUPPORT_COMPANY} என்பது 24/7 AI மற்றும் மனித ஆதரவு நிறுவனம் ஆகும். நாங்கள் Wi-Fi நெட்வொர்க், பிரிண்டர், கடவுச்சொல் மற்றும் கணினி பழுதுகளை விரைவாக சரிசெய்கிறோம்."
            else:
                text = f"{settings.SUPPORT_COMPANY} provides 24/7 intelligent technical support. I can help troubleshoot Wi-Fi connections, network outages, printer offline errors, password resets, and PC performance issues. What would you like help with?"
            return {"text": text, "intent": "company_info", "should_escalate": False, "ticket_id": None, "scenario_id": None, "is_resolved": False}

        # 8. Politeness / Simple Acknowledgements when idle
        if not session.diagnostics.scenario_id and m in ["ok", "okay", "alright", "sure", "yeah", "yes", "tell me", "sari", "சரி", "சொல்லுங்க", "நன்றி"]:
            if is_tamil:
                text = "சரிங்க! உங்கள் சாதனத்தில் என்ன பிரச்சனை உள்ளது என்று கூறுங்கள் (எடுத்துக்காட்டாக Wi-Fi அல்லது Printer)."
            else:
                text = "Great! Please describe what device or issue you'd like to troubleshoot today, and we'll resolve it step by step."
            return {"text": text, "intent": "acknowledgement", "should_escalate": False, "ticket_id": None, "scenario_id": None, "is_resolved": False}

        return None

    def _run_offline_diagnostic_engine(
        self,
        session: CallSession,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Deterministic, state-machine-backed diagnostic reasoning engine.
        Follows structured decision trees with multi-turn memory and multi-lingual support.
        """
        msg_lower = user_message.lower().strip()
        tokens = set(re.findall(r"\w+", msg_lower))
        is_tamil = any('\u0B80' <= c <= '\u0BFF' for c in user_message) or getattr(session, "language", "en") in ("ta", "ta-IN") or any(w in msg_lower for w in ["vanakkam", "velai", "aama", "illa", "sari", "seri", "romba", "varala"])

        # 1. Check for gratitude / resolution confirmation from caller
        if any(w in tokens for w in ["thanks", "thank", "resolved", "fixed", "works", "working", "all good", "solved", "great", "velai seiyuthu", "sari aaiduchu", "நன்றி"]) and session.diagnostics.scenario_id:
            session.end_call(resolution=ResolutionStatus.RESOLVED)
            if is_tamil:
                res_text = "அருமை! உங்கள் பிரச்சனை தீர்க்கப்பட்டதில் மகிழ்ச்சி. உங்களுக்கு வேறு ஏதேனும் தொழில்நுட்ப உதவி தேவையா?"
            else:
                res_text = "That's fantastic news! I'm glad we were able to get that resolved for you today. Is there anything else I can help you with?"
            return {
                "text": res_text,
                "intent": "resolution_confirmed",
                "should_escalate": False,
                "ticket_id": None,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": True
            }

        # 2. Check for goodbye / closing
        if any(w in tokens for w in ["bye", "goodbye", "no that's all", "nothing else", "have a good day", "all set", "poitu varen", "mudinjadhu"]):
            session.end_call(resolution=ResolutionStatus.RESOLVED)
            if is_tamil:
                farewell_text = f"{settings.SUPPORT_COMPANY} அழைத்தமைக்கு நன்றி. இனிய நாளாக அமைய வாழ்த்துகள்!"
            else:
                farewell_text = f"Thank you for calling {settings.SUPPORT_COMPANY}. Have a wonderful day, and take care!"
            return {
                "text": farewell_text,
                "intent": "farewell",
                "should_escalate": False,
                "ticket_id": None,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": True
            }

        # 3. Check for conversational chit-chat, identity, well-being, repetition
        conv_intent = self._match_conversational_intent(session, user_message)
        if conv_intent:
            return conv_intent

        # 4. If no active scenario is tracked, initiate the best matching article
        current_article = None
        if session.diagnostics.scenario_id:
            current_article = rag_service.get_article_by_id(session.diagnostics.scenario_id)

        if not current_article:
            matched_article = rag_service.find_best_article(user_message)
            if matched_article:
                current_article = matched_article
                session.diagnostics.scenario_id = current_article.id
                session.diagnostics.current_step_index = 0
                session.diagnostics.attempted_steps = []
                session.diagnostics.failure_count = 0
                session.issue_category = current_article.category
                session.issue_summary = f"{current_article.title} - {user_message[:60]}"

                first_step = current_article.diagnostic_flow[0]
                session.diagnostics.attempted_steps.append(f"Step 1: {first_step.instruction}")

                if is_tamil:
                    start_text = f"நிச்சயமாக, உங்கள் {current_article.category} பிரச்சனையை சரிசெய்ய உதவுகிறேன். {first_step.instruction}"
                else:
                    start_text = f"I can certainly help you with your {current_article.category.lower()} issue. {first_step.instruction}"

                return {
                    "text": start_text,
                    "intent": "diagnostic_start",
                    "should_escalate": False,
                    "ticket_id": None,
                    "scenario_id": current_article.id,
                    "is_resolved": False
                }
            else:
                # Check for FAQ match if no article matched
                faq_match = rag_service.match_faq(user_message)
                if faq_match:
                    if is_tamil:
                        faq_ans = f"{faq_match.answer} இது உங்கள் கேள்விக்கு உதவியாக இருந்ததா?"
                    else:
                        faq_ans = f"{faq_match.answer} Does that help answer your question?"
                    return {
                        "text": faq_ans,
                        "intent": "faq_answer",
                        "should_escalate": False,
                        "ticket_id": None,
                        "scenario_id": None,
                        "is_resolved": False
                    }

                # Unclear query -> Ask for clarification
                if is_tamil:
                    clar_text = "உங்கள் பிரச்சனையை நான் சரியாக புரிந்து கொள்ள, என்ன சாதனம் அல்லது செயலியில் பிரச்சனை உள்ளது என்று கூறுங்கள் (எடுத்துக்காட்டாக Wi-Fi, பிரிண்டர், கடவுச்சொல், அல்லது கணினி)."
                else:
                    clar_text = "I want to make sure I understand your technical issue correctly. Could you describe what device or application you're having trouble with, such as your Wi-Fi, printer, password, or computer performance?"
                return {
                    "text": clar_text,
                    "intent": "clarification_needed",
                    "should_escalate": False,
                    "ticket_id": None,
                    "scenario_id": None,
                    "is_resolved": False
                }

        # 8. Active Scenario: Evaluate user response to current step
        curr_step_idx = session.diagnostics.current_step_index
        flow = current_article.diagnostic_flow

        if curr_step_idx < len(flow):
            current_step = flow[curr_step_idx]
            eval_result, conf = rag_service.evaluate_step_response(current_step, user_message)

            if eval_result == "positive":
                if current_step.is_terminal_resolution or current_step.on_success_action == "resolved":
                    session.end_call(resolution=ResolutionStatus.RESOLVED)
                    if is_tamil:
                        succ_text = f"அருமை! உங்கள் {current_article.category} இப்போது சரியாக வேலை செய்கிறது. எல்லாம் சரியாக உள்ளதா?"
                    else:
                        succ_text = f"Wonderful! It looks like your {current_article.category.lower()} is now fully working. Is everything functioning properly for you now?"
                    return {
                        "text": succ_text,
                        "intent": "issue_resolved",
                        "should_escalate": False,
                        "ticket_id": None,
                        "scenario_id": current_article.id,
                        "is_resolved": True
                    }
                elif current_step.on_success_action == "escalate":
                    ticket = escalation_service.create_escalation_ticket(
                        session=session,
                        reason="Critical step requires Tier 2 escalation.",
                        priority=TicketPriority.HIGH,
                        issue_category=current_article.category
                    )
                    if is_tamil:
                        esc_text = f"உறுதிப்படுத்தியதற்கு நன்றி. உங்கள் அழைப்பை எங்கள் சீனியர் தொழில்நுட்ப நிபுணரிடம் டிக்கெட் எண் {ticket.ticket_id} கீழ் இணைக்கிறேன். தயவுசெய்து இணைப்பில் இருங்கள்."
                    else:
                        esc_text = f"Thank you for confirming. I am transferring you directly to our Tier 2 Engineering team under ticket reference {ticket.ticket_id}. Please stay on the line."
                    return {
                        "text": esc_text,
                        "intent": "escalate",
                        "should_escalate": True,
                        "ticket_id": ticket.ticket_id,
                        "scenario_id": current_article.id,
                        "is_resolved": False
                    }
                else:
                    # Proceed to next step in flow
                    next_idx = curr_step_idx + 1
                    if next_idx < len(flow):
                        session.diagnostics.current_step_index = next_idx
                        next_step = flow[next_idx]
                        session.diagnostics.attempted_steps.append(f"Step {next_idx+1}: {next_step.instruction}")
                        if is_tamil:
                            step_text = f"மிக நன்று. அடுத்ததாக, {next_step.instruction}"
                        else:
                            step_text = f"Great. Next, {next_step.instruction}"
                        return {
                            "text": step_text,
                            "intent": "diagnostic_next_step",
                            "should_escalate": False,
                            "ticket_id": None,
                            "scenario_id": current_article.id,
                            "is_resolved": False
                        }
                    else:
                        session.end_call(resolution=ResolutionStatus.RESOLVED)
                        if is_tamil:
                            done_text = "நன்று! அனைத்து சரிபார்ப்பு முறைகளும் முடிந்தது. உங்கள் பிரச்சனை தீர்ந்துவிட்டதா?"
                        else:
                            done_text = "Great job! That completes our diagnostic procedure. Did that solve the problem for you?"
                        return {
                            "text": done_text,
                            "intent": "diagnostic_complete",
                            "should_escalate": False,
                            "ticket_id": None,
                            "scenario_id": current_article.id,
                            "is_resolved": True
                        }

            elif eval_result == "negative":
                session.diagnostics.failure_count += 1
                if current_step.on_failure_action == "escalate" or session.diagnostics.failure_count >= 2:
                    ticket = escalation_service.create_escalation_ticket(
                        session=session,
                        reason=f"Troubleshooting failed after {len(session.diagnostics.attempted_steps)} steps.",
                        priority=TicketPriority.HIGH,
                        issue_category=current_article.category
                    )
                    if is_tamil:
                        esc_fail_text = f"அந்த முறை பிரச்சனையை தீர்க்கவில்லை என்பதை புரிந்து கொள்கிறேன். விரைவாக சரிசெய்ய, எங்கள் மனித நிபுணரிடம் இணைக்கிறேன். உங்கள் டிக்கெட் எண் {ticket.ticket_id}."
                    else:
                        esc_fail_text = f"I see that step did not resolve the issue. To ensure this is fixed quickly, I am escalating your call to our Tier 2 Support specialist. Your ticket ID is {ticket.ticket_id}. Connecting you now."
                    return {
                        "text": esc_fail_text,
                        "intent": "escalate",
                        "should_escalate": True,
                        "ticket_id": ticket.ticket_id,
                        "scenario_id": current_article.id,
                        "is_resolved": False
                    }
                else:
                    # Move to next step if available
                    next_idx = curr_step_idx + 1
                    if next_idx < len(flow):
                        session.diagnostics.current_step_index = next_idx
                        next_step = flow[next_idx]
                        session.diagnostics.attempted_steps.append(f"Step {next_idx+1}: {next_step.instruction}")
                        if is_tamil:
                            alt_text = f"புரிந்து கொண்டேன். நமது அடுத்த முறையை முயற்சிப்போம். {next_step.instruction}"
                        else:
                            alt_text = f"Understood. Let's try our alternative step. {next_step.instruction}"
                        return {
                            "text": alt_text,
                            "intent": "diagnostic_fallback_step",
                            "should_escalate": False,
                            "ticket_id": None,
                            "scenario_id": current_article.id,
                            "is_resolved": False
                        }

            else:
                # Unclear response or user repeating symptom - guide them with clarity
                if is_tamil:
                    guide_text = f"சரிங்க, உங்கள் பிரச்சனையை தீர்க்க: {current_step.instruction} {current_step.follow_up_question}"
                else:
                    guide_text = f"I understand. To resolve your issue: {current_step.instruction} {current_step.follow_up_question}"
                return {
                    "text": guide_text,
                    "intent": "clarification_step",
                    "should_escalate": False,
                    "ticket_id": None,
                    "scenario_id": current_article.id,
                    "is_resolved": False
                }

        # Fallback escalation if steps exhausted
        ticket = escalation_service.create_escalation_ticket(
            session=session,
            reason="Diagnostic flow completed without resolution confirmation.",
            priority=TicketPriority.MEDIUM,
            issue_category=current_article.category
        )
        if is_tamil:
            fall_text = f"நாம் மேற்கொண்ட அனைத்து முறைகளையும் குறித்து வைத்துள்ளேன். டிக்கெட் எண் {ticket.ticket_id} கீழ் மனித நிபுணரிடம் உங்களை இணைக்கிறேன்."
        else:
            fall_text = f"I've noted down all the steps we've tried. I'm connecting you with a human specialist under ticket {ticket.ticket_id} to take a deeper look."
        return {
            "text": fall_text,
            "intent": "escalate",
            "should_escalate": True,
            "ticket_id": ticket.ticket_id,
            "scenario_id": current_article.id,
            "is_resolved": False
        }

    async def _call_gemini(self, session: CallSession, user_message: str) -> Optional[Dict[str, Any]]:
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            messages = self._build_chat_messages(session, user_message)
            response = await client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )
            reply = response.choices[0].message.content.strip()
            return {
                "text": reply,
                "intent": "ai_response",
                "should_escalate": False,
                "ticket_id": None,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": "resolved" in reply.lower()
            }
        except Exception as e:
            print(f"Gemini API invocation error: {e}")
            return None

    async def _call_openai(self, session: CallSession, user_message: str) -> Optional[Dict[str, Any]]:
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            messages = self._build_chat_messages(session, user_message)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )
            reply = response.choices[0].message.content.strip()
            return {
                "text": reply,
                "intent": "ai_response",
                "should_escalate": False,
                "ticket_id": None,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": "resolved" in reply.lower()
            }
        except Exception as e:
            print(f"OpenAI API invocation error: {e}")
            return None

    async def _call_groq(self, session: CallSession, user_message: str) -> Optional[Dict[str, Any]]:
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            messages = self._build_chat_messages(session, user_message)
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )
            reply = response.choices[0].message.content.strip()
            return {
                "text": reply,
                "intent": "ai_response",
                "should_escalate": False,
                "ticket_id": None,
                "scenario_id": session.diagnostics.scenario_id,
                "is_resolved": "resolved" in reply.lower()
            }
        except Exception as e:
            print(f"Groq API invocation error: {e}")
            return None

    def _build_chat_messages(self, session: CallSession, user_message: str) -> List[Dict[str, str]]:
        articles = rag_service.search_articles(user_message, top_k=2)
        kb_text = "\n\n".join([f"Topic: {a.title}\nSummary: {a.summary}\nSteps: {[s.instruction for s in a.diagnostic_flow]}" for a, _ in articles])
        
        history_text = "\n".join([f"{t.role.upper()}: {t.text}" for t in session.turns[-6:]])

        prompt = SYSTEM_SUPPORT_PROMPT.format(
            knowledge_context=kb_text or "General technical support knowledge base.",
            call_history=history_text or "New call incoming."
        )

        messages = [{"role": "system", "content": prompt}]
        for turn in session.turns[-4:]:
            messages.append({"role": turn.role if turn.role in ("user", "assistant") else "system", "content": turn.text})
        messages.append({"role": "user", "content": user_message})
        return messages


llm_service = LLMService()
