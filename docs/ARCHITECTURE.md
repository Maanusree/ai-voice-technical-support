# System Architecture & Technical Specification

## 1. High-Level Architecture Overview

The **ApexCloud AI Voice Technical Support Agent** is designed as a modular, event-driven voice application capable of real-time speech recognition, stateful multi-turn reasoning, knowledge retrieval (RAG), and neural speech synthesis.

```mermaid
flowchart TD
    subgraph ClientLayer ["1. Voice Client / Softphone Interface"]
        UserMic["Microphone Stream (Web Audio API)"]
        UserSpeaker["Speaker (Web Speech / MP3 Buffer)"]
        Visualizer["Canvas Waveform Visualizer"]
        HUD["Live Subtitles & Latency HUD"]
        Softphone["Softphone Controller (Hold / Mute / Escalate)"]
    end

    subgraph GatewayLayer ["2. FastAPI Async Gateway & Telephony Adapter"]
        RestAPI["REST API Endpoints (/api/calls, /api/logs, /api/tickets)"]
        WSStream["Bidirectional WebSocket Gateway (/ws/stream)"]
        TelephonyAdapter["SIP / WebRTC / Twilio Stream Adapter"]
    end

    subgraph CoreEngine ["3. AI Voice Orchestration Engine"]
        STTEngine["STT Engine (Web Speech API / Groq Whisper / OpenAI Whisper)"]
        SessionMgr["Dialogue & State Machine Manager (Context & Step History)"]
        RAGService["Knowledge Base & Decision Tree Service"]
        LLMEngine["Reasoning Engine (Gemini 2.0 / GPT-4o-mini / Groq / Offline Engine)"]
        EscalationMgr["Escalation & Safety Sentinel"]
        TTSEngine["TTS Engine (Microsoft Edge-TTS / Web Speech Synthesis)"]
    end

    subgraph StorageLayer ["4. Persistence & Knowledge Assets"]
        KBStore[("Support Knowledge Base (JSON / Diagnostic Trees)")]
        CDRStore[("Call Detail Records (CDR Logs)")]
        TicketStore[("Tier-2 Support Tickets")]
    end

    UserMic --> STTEngine
    STTEngine --> RestAPI & WSStream
    RestAPI & WSStream --> SessionMgr
    SessionMgr --> RAGService
    RAGService --> KBStore
    RAGService --> LLMEngine
    LLMEngine --> EscalationMgr
    EscalationMgr --> TicketStore
    LLMEngine --> TTSEngine
    TTSEngine --> UserSpeaker
    SessionMgr --> CDRStore
```

---

## 2. Component Breakdown

### 2.1 Voice Interface (Client Layer)
- **Softphone Simulator**: Emulates a real hardware SIP deskphone or mobile support client with interactive call controls (Dial, Mute, Hold, Escalate, Hang Up).
- **Speech-to-Text (STT)**: Employs browser-native continuous Web Speech Recognition (`webkitSpeechRecognition`) for instant zero-latency speech recognition, with fallback to backend Whisper ingestion.
- **Audio Visualizer**: Real-time canvas renderer calculating dynamic sine curves tapered by a Gaussian bell-curve window.

### 2.2 Orchestration & Dialogue State Machine
The core state machine manages the conversation flow through distinct phases:
1. **Greeting & Intake**: Introduces the agent and identifies the core problem domain.
2. **Knowledge Matching & Step Initiation**: Fuzzy and semantic token matching retrieves the matching diagnostic article and loads its step tree.
3. **Step-by-Step Diagnostic Execution**: Presents one diagnostic instruction at a time and asks a focused follow-up question.
4. **Response Evaluation**: Evaluates caller's reply into `positive`, `negative`, or `unclear`.
5. **Resolution Confirmation or Escalation**: On success, confirms resolution; on repeated failures or hazards, generates an Escalation Ticket.

### 2.3 Knowledge Retrieval & RAG
- Structured dataset of categorized technical articles (`Network`, `Account Access`, `Hardware/Printers`, `OS Crashes/BSOD`, `Software Errors`, `Safety Hazards`).
- Each article defines explicit steps with positive indicators, negative indicators, and failure thresholds.

### 2.4 Multi-Provider LLM Engine
- **Built-in Offline Diagnostic Reasoning Engine**: 100% deterministic, rule-based state machine that ensures zero external dependency, high speed, and reliability.
- **API Model Integrations**: Native support for **Google Gemini 2.0 Flash**, **OpenAI GPT-4o-mini**, and **Groq Llama 3.3 70B**.

### 2.5 Text-to-Speech (TTS)
- **Microsoft Edge-TTS Neural Engine**: High-fidelity neural voice synthesis (`en-US-AriaNeural`) streamed as MP3 bytes.
- **Browser Speech Synthesis Fallback**: Instant local playback for offline demonstration.

---

## 3. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant UI as Voice Interface
    participant Server as FastAPI Gateway
    participant LLM as AI Reasoning Engine
    participant RAG as Knowledge Base
    participant TTS as Edge-TTS Engine
    participant DB as Logs & Ticket Store

    Caller->>UI: Clicks "Call" or speaks problem
    UI->>Server: POST /api/calls/start
    Server->>TTS: Synthesize Greeting
    TTS-->>Server: Audio MP3 Base64
    Server-->>UI: {session_id, greeting_text, audio_base64}
    UI->>Caller: Plays natural voice greeting

    Caller->>UI: "My Wi-Fi is connected but no internet"
    UI->>UI: STT captures spoken utterance
    UI->>Server: POST /api/calls/message {session_id, message}
    Server->>RAG: Search Articles & Match Diagnostic Tree
    RAG-->>Server: kb_network_wifi (Step 1: Check router lights)
    Server->>LLM: Generate diagnostic follow-up response
    LLM-->>Server: Step 1 instruction & follow-up question
    Server->>TTS: Synthesize voice response
    TTS-->>Server: Audio Base64
    Server->>DB: Record User & Assistant Turns to CDR Log
    Server-->>UI: Response Text, Audio, Latency Metrics
    UI->>Caller: Plays spoken diagnostic step

    Caller->>UI: "I smell smoke coming out of my PC!"
    UI->>Server: POST /api/calls/message {message: "smoke..."}
    Server->>Server: Detect Critical Hazard Trigger
    Server->>DB: Generate Tier-2 Ticket (TICK-XXXX, Priority: CRITICAL)
    Server->>TTS: Synthesize Urgent Safety Warning & Transfer
    Server-->>UI: Escalation Response + Transfer Protocol
    UI->>Caller: Plays emergency transfer instructions & shows ticket
```
