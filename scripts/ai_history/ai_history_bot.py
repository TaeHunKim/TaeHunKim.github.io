from google import genai
from google.genai import types
import os
import json
from datetime import datetime, timedelta
from json_repair import repair_json
import urllib.request
import traceback
import sys
import time

try:
    from ai_history_models import HistoryBotResponse, HistoryBotMetadata
except ImportError:
    print("⚠️ 'ai_history_models.py' 파일을 찾을 수 없습니다. Pydantic 모델 정의가 필요합니다.")
    sys.exit(1)

# --- [Configuration] ---
RESEARCH_MODEL_NAME = "gemini-2.5-flash"
WRITER_MODEL_NAME = "gemini-3-flash-preview"
STATE_FILE = "bot_state.json"

DEFAULT_STATE = {
    "day_count": 0,
    "last_run_date": "",
    "current_year": "N/A",
    "last_topic": "N/A",
    "next_topic": "워런 매컬러와 월터 피츠의 인공 신경망 모델 (MCP 뉴런)",
    "next_year": 1943
}

# --- [Prompt Definitions (English)] ---
def get_researcher_prompt():
    return """
You are an 'AI History Researcher'.
**Goal:** Research deep technical details about the specific event/figure provided in the history of Artificial Intelligence.

**Instructions:**
1.  **Search Aggressively:** Find detailed specs, logic, and context.
2.  **Deep Dive:** Explain *how* it works and *why* it was a paradigm shift specifically in AI or Neural Networks.
3.  **Modern Connections:** Trace the lineage to modern AI tech (e.g., Deep Learning, LLMs).
4.  **Output:** Structured summary for a blog post. Do NOT worry about the next topic.
"""

def get_planner_prompt():
    return """
You are the **'Chief Editor of Artificial Intelligence History'**.
Your job is to select the **single most important next milestone** in AI history based on the provided current context.

**Selection Logic:**
* Identify the *single most important* next milestone in AI history that happened *after* the current event.
    * **PRIORITIZE PARADIGM SHIFTS:** Look for technologies, papers, or events that changed how AI research progressed (e.g., Turing Test, Dartmouth Workshop, Perceptron, Backpropagation, AlexNet).
    * **EVALUATE IMPACT:** Ensure it is strictly related to Artificial Intelligence, Machine Learning, or Neural Networks.

**Constraint**:
* Follow the chronological order of AI development. Find a milestone in [Current Year (later than the current topic)], [Current Year + 1], or slightly later. Do not skip major eras (e.g., do not skip the AI Winters).

**Output Format:**
Return ONLY a JSON object:
{
    "next_topic": "Topic Name",
    "next_year": 19XX,
    "reasoning": "Why this was chosen over other candidates"
}
"""

def get_writer_prompt():
    return """
You are the **'AI History Bot' (AI 인공지능 역사 봇)**. 
Your mission is to introduce one important event, concept, or figure in Artificial Intelligence history every day.

**Identity & Tone:**
* **Persona:** You are a dedicated AI bot guiding users through the journey of AI evolution. Do NOT act as a human.
* **Tone:** Professional, objective, insightful, and enthusiastic.
* **Consistency:** Maintain a consistent voice. You are helpful, objective, and deeply knowledgeable about AI architectures and history.

**Task:**
You will receive research notes from a researcher. Your task is to write a daily blog post in **fluent, engaging Korean**.

**Writing Guidelines:**
1.  **Greeting:** MUST start the "Engaging Opening Greeting" by introducing yourself as the "AI 인공지능 역사 봇" and welcoming the reader to Day {day_count}.
2.  **Language:** Korean (Main text), but keep technical terms in English brackets where appropriate (e.g., 인공 신경망(Artificial Neural Network)).
3.  **Depth:** Your explanation must be technically deep (Deep Dive) and logically sound.

**Output Format:**
You MUST output a valid JSON object with the following structure. The 'content' field must be a Markdown string using the specific template below.

```json
{
    "content": "MARKDOWN_STRING",
    "metadata": {
        "current_year": int,
        "current_topic": "string",
        "next_topic": "string",
        "next_year": int
    }
}
```

**Markdown Template for 'content':**

Day {day_count}: {Title}

{Engaging Opening Greeting (As AI Bot)}

## 🕰️ 오늘의 키워드: {Topic Name}
 * 원어: {Original Name}
 * 시기: {Year} ({Key Event})

{Main Body: Explanation of the figure/tech}

## ⚡ 무엇이 혁명적이었나? (Deep Dive)
{Technical deep dive explaining why this was a breakthrough in AI, based on the research notes}

## 🔗 현대와의 연결: {Modern Analogy}
{Explain how this past concept connects to specific modern AI technologies (Deep Learning, Transformers, etc.)}

## 📅 내일의 키워드 예고
{A hint about the next milestone mention in the metadata}
"""

# --- [Helper Functions] ---
def load_state():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_path = os.path.join(script_dir, STATE_FILE)
    if not os.path.exists(state_path):
        return DEFAULT_STATE
    with open(state_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_state(state):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_path = os.path.join(script_dir, STATE_FILE)
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_final_url_urllib(initial_url):
    try:
        req = urllib.request.Request(initial_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.geturl()
    except Exception:
        return initial_url

# --- [Core Logic: Hybrid Pipeline] ---
def generate_daily_content(state):
    client = genai.Client()
    
    last_year = state['current_year']
    last_topic = state['last_topic']
    next_topic = state['next_topic']
    next_year = state['next_year']
    day_count = state['day_count']

    print(f"   ...Phase 1: Researching '{next_topic}' with {RESEARCH_MODEL_NAME}")

    research_prompt = f"""
    Current Progress: Day {day_count-1}.
    Last Topic: '{last_topic}' ({last_year}).
    
    **TODAY'S MISSION:**
    Research the topic: '{next_topic}' which occurred around {next_year}.
    
    Find the facts, technical details, modern connections, and the NEXT historical milestone after this one in AI history.
    """
    
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    
    research_config = types.GenerateContentConfig(
        system_instruction=get_researcher_prompt(),
        tools=[grounding_tool],
        temperature=0.0,
        thinking_config=types.ThinkingConfig(thinking_budget=24576, include_thoughts=False)
    )

    research_response = None
    chunks = None
    
    for attempt in range(3):
        try:
            research_response = client.models.generate_content(
                model=RESEARCH_MODEL_NAME,
                contents=research_prompt,
                config=research_config,
            )
            if research_response.candidates[0].grounding_metadata.grounding_chunks:
                chunks = research_response.candidates[0].grounding_metadata.grounding_chunks
                break
            else:
                print(f"      (Attempt {attempt+1}: No grounding chunks found. Retrying...)")
                time.sleep(2)
        except Exception as e:
            print(f"      (Attempt {attempt+1} Failed: {e})")
            time.sleep(2 * (attempt + 1))
            if attempt == 2: raise

    citation_list_str = ""
    if chunks:
        for x in chunks:
            try:
                final_url = get_final_url_urllib(x.web.uri)
                title = x.web.title if x.web.title else "Reference"
                citation_list_str += f"* [{title}]({final_url})\n"
            except:
                continue
    else:
        citation_list_str = "* (No web citations found during research phase)\n"

    research_notes = research_response.text
    print(f"      Collected {len(chunks) if chunks else 0} chunks")

    print(f"   ...Phase 1.5: Selecting NEXT topic...")
    recent_history_str = f"Previous: {state.get('last_topic', 'N/A')}, Current: {next_topic}"

    planner_config = types.GenerateContentConfig(
        system_instruction=get_planner_prompt(),
        tools=[grounding_tool],
        temperature=0.0,
        thinking_config=types.ThinkingConfig(thinking_budget=24576, include_thoughts=False)
    )

    planner_prompt = f"""
**Current Context:**
* Current Topic: {next_topic} ({next_year})
* Recent Topics History: {recent_history_str}
"""

    planner_response = client.models.generate_content(
        model=RESEARCH_MODEL_NAME,
        contents=planner_prompt,
        config=planner_config
    )

    next_plan = json.loads(repair_json(planner_response.text))
    print(f"      -> Next Plan: {next_plan['next_topic']} ({next_plan['next_year']})")

    print(f"   ...Phase 2: Writing content with {WRITER_MODEL_NAME}")

    writer_user_prompt = f"""
    **Task:** Write the blog post for Day {day_count}.
    
    **Research Data:**
    {research_notes}

    **Planning Data (For Metadata):**
    Next Topic: {next_plan['next_topic']}
    Next Year: {next_plan['next_year']}

    **Context:**
    Last Topic: {last_topic} ({last_year})
    Today's Topic: {next_topic} ({next_year})
    """

    writer_config = types.GenerateContentConfig(
        system_instruction=get_writer_prompt(),
        temperature=0.4,
        thinking_config=types.ThinkingConfig(thinking_level="high", include_thoughts=False)
    )

    writer_response = client.models.generate_content(
        model=WRITER_MODEL_NAME,
        contents=writer_user_prompt,
        config=writer_config
    )

    response_json = HistoryBotResponse.model_validate_json(repair_json(writer_response.text))

    response_json.content += f"\n\n## 📚 참고 문헌\n{citation_list_str}"
    response_json.content += f"\n\n*이 콘텐츠는 AI에 의해 생성되었으며, 오류나 부정확한 정보를 포함할 수 있습니다.*"
    
    return response_json

# --- [Main Execution] ---
def extract_metadata(content, current_state):    
    new_state = current_state.copy()
    new_state['day_count'] += 1
    new_state['last_run_date'] = datetime.now().strftime("%Y-%m-%d")
    new_state['current_year'] = content.metadata.current_year
    new_state['last_topic'] = content.metadata.current_topic
    new_state['next_topic'] = content.metadata.next_topic
    new_state['next_year'] = content.metadata.next_year
    return new_state

def main():
    state = load_state()
    
    current_actual_year = datetime.now().year
    termination_threshold = current_actual_year - 3

    next_year_candidate = state.get('next_year')
    if not isinstance(next_year_candidate, int) or next_year_candidate >= termination_threshold:
        if state['day_count'] > 0:
            print("🛑 [알림] AI 역사 봇의 여정이 완료되었습니다.")
        else:
             print("⚠️ [경고] 초기 상태 오류. bot_state.json을 확인하세요.")
        return

    print(f"🤖 Day {state['day_count']} 콘텐츠 생성 시작... ({state['next_year']}년 {state['next_topic']})")
    
    try:
        content_response = generate_daily_content(state)
        
        if content_response.metadata.next_year >= termination_threshold:
            target_header = "## 📅 내일의 키워드 예고"
            citation_header = "## 📚 참고 문헌"
            
            replacement_section = f"""
## 🛑 긴 여정의 마침표
우리는 1943년 매컬러-피츠의 인공 신경망 모델부터 시작해 쉼 없이 달려왔습니다.
다음 이정표는 {content_response.metadata.next_year}년의 '{content_response.metadata.next_topic}'입니다.

하지만 본 역사 봇은 가장 최근의 사건들에 대한 역사적 평가는 미래로 미루고, 현재로부터 3년 전까지의 기록을 끝으로 연재를 마무리하고자 합니다.

오늘이 바로 그 마지막 페이지입니다. 그동안 AI의 발자취를 함께 걸어주셔서 감사합니다.
"""
            if target_header in content_response.content:
                base_content = content_response.content.split(target_header)[0].strip()
                citation_start_index = content_response.content.find(citation_header)
                if citation_start_index != -1:
                    footer_content = content_response.content[citation_start_index:]
                else:
                    footer_content = ""
                content_response.content = f"{base_content}\n\n{replacement_section}\n\n{footer_content}"

        content = content_response.content.strip()
        title = content.splitlines()[0].replace("#", "").strip()
        body = "\n".join(content.splitlines()[1:]).strip()
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-day{state['day_count']}.md"
        
        # categories를 ai_history로 지정
        header = f"""
---
title:  "{title}"
categories:
  - ai_history
toc: true
toc_sticky: true
comments: true
---
"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 생성된 md 파일을 _posts/ai_history 에 저장
        target_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "_posts", "ai_history"))
        os.makedirs(target_dir, exist_ok=True)
        
        with open(os.path.join(target_dir, filename), 'w', encoding='utf-8') as f:
            f.write(header.strip() + "\n\n" + body)

        new_state = extract_metadata(content_response, state)
        save_state(new_state)
        print("💾 상태 저장 및 파일 생성 완료.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(1)