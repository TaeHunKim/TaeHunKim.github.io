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

# Pydantic 모델이 정의된 파일이 같은 폴더에 있다고 가정합니다.
# 만약 파일이 없다면 이 부분은 수정이 필요할 수 있습니다.
try:
    from cs_history_models import HistoryBotResponse, HistoryBotMetadata
except ImportError:
    # 혹시 모를 실행 에러를 방지하기 위해 임시로 내부 정의하거나 경고를 띄웁니다.
    print("⚠️ 'cs_history_models.py' 파일을 찾을 수 없습니다. Pydantic 모델 정의가 필요합니다.")
    sys.exit(1)

# --- [Configuration] ---
# 비용 효율성을 위해 역할에 따라 모델을 이원화합니다.
RESEARCH_MODEL_NAME = "gemini-2.5-flash"  # 검색 및 조사 담당 (속도 빠름, 저렴함)
WRITER_MODEL_NAME = "gemini-3-flash-preview"      # 작문 담당 (문장력 우수, 추론 능력 높음)
STATE_FILE = "bot_state.json"

DEFAULT_STATE = {
    "day_count": 0,
    "last_run_date": "",
    "current_year": "N/A",
    "last_topic": "N/A",
    "next_topic": "찰스 배비지의 해석기관",
    "next_year": 1835
}

# --- [Prompt Definitions (English)] ---
# 프롬프트는 모델의 성능 최적화를 위해 영어로 작성합니다.

def get_researcher_prompt():
    """Phase 1: 현재 주제 심층 탐구 전용"""
    return """
You are an 'AI Computer Science History Researcher'.
**Goal:** Research deep technical details about the specific event/figure provided.

**Instructions:**
1.  **Search Aggressively:** Find detailed specs, logic, and context.
2.  **Deep Dive:** Explain *how* it works and *why* it was a paradigm shift.
3.  **Modern Connections:** Trace the lineage to modern tech.
4.  **Output:** Structured summary for a blog post. Do NOT worry about the next topic.
"""

def get_planner_prompt():
    """Phase 1.5: 다음 주제 선정 (Planner) 전용"""
    return """
You are the **'Chief Editor of Computer Science History'**.
Your job is to select the **single most important next milestone** in computer science history based on the provided current context.

**Selection Logic:**
* Identify the *single most important* next milestone in computer science history that happened *after* the current event.
    * **PRIORITIZE PARADIGM SHIFTS:** Do not simply choose the next incremental improvement in the same field. Look for technologies that changed how the *entire industry* works.
    * **EVALUATE IMPACT:** * Example: After 'AlexNet' (AI breakthrough), 'Docker' (2013, Infrastructure revolution) might be historically more significant than 'VGGNet' (AI improvement).

**Output Format:**
Return ONLY a JSON object:
{
    "next_topic": "Topic Name",
    "next_year": 20XX,
    "reasoning": "Why this was chosen over other candidates"
}
"""

def get_writer_prompt():
    """Phase 2: Pro/Flash 모델을 위한 집필 지시문 (페르소나 복구 버전)"""
    return """
You are the **'AI Computer Science History Bot' (AI 컴퓨터 과학 역사 봇)**. 
Your mission is to introduce one important event or figure in computer science history every day.

**Identity & Tone:**
* **Persona:** Do NOT act as a human historian. You are a dedicated AI bot guiding users through the journey of computing history.
* **Tone:** Professional and insightful, but also friendly and enthusiastic.
* **Consistency:** Maintain a consistent voice with previous posts. You are helpful, objective, and deeply knowledgeable.

**Task:**
You will receive research notes from a researcher. Your task is to write a daily blog post in **fluent, engaging Korean**.

**Writing Guidelines:**
1.  **Greeting:** MUST start the "Engaging Opening Greeting" by introducing yourself as the "AI 컴퓨터 과학 역사 봇" and welcoming the reader to Day {day_count}.
2.  **Language:** Korean (Main text), but keep technical terms in English brackets where appropriate (e.g., 해석기관(Analytical Engine)).
3.  **Depth:** Even though you are a bot, your explanation must be technically deep (Deep Dive) and logically sound.

**Output Format:**
You MUST output a valid JSON object with the following structure. The 'content' field must be a Markdown string using the specific template below.

```json
{
    "content": "MARKDOWN_STRING",
    "metadata": {
        "current_year": int,
        "last_topic": "string",
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
{Technical deep dive explaining why this was a breakthrough, based on the research notes}

## 🔗 현대와의 연결: {Modern Analogy}
{Explain how this past concept connects to specific modern technologies (CPU, AI, etc.)}

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
    """리다이렉트된 최종 URL을 가져옵니다."""
    try:
        req = urllib.request.Request(initial_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.geturl()
    except Exception:
        # 에러 발생 시 초기 URL 반환
        return initial_url

# --- [Core Logic: Hybrid Pipeline] ---

def generate_daily_content(state):
    """
    하이브리드 파이프라인:
    1. Researcher (Flash): 구글 검색을 통해 정보 수집 및 사실 확인
    2. Writer (Pro): 수집된 정보를 바탕으로 한국어 블로그 포스트 작성
    """
    client = genai.Client()
    
    # Context 변수 준비
    last_year = state['current_year']
    last_topic = state['last_topic']
    next_topic = state['next_topic']
    next_year = state['next_year']
    day_count = state['day_count']

    print(f"   ...Phase 1: Researching '{next_topic}' with {RESEARCH_MODEL_NAME}")

    # --- Phase 1: Research with Flash (Grounding Enabled) ---
    research_prompt = f"""
    Current Progress: Day {day_count-1}.
    Last Topic: '{last_topic}' ({last_year}).
    
    **TODAY'S MISSION:**
    Research the topic: '{next_topic}' which occurred around {next_year}.
    
    Find the facts, technical details, modern connections, and the NEXT historical milestone after this one.
    """
    
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    
    # Flash 모델 호출
    research_config = types.GenerateContentConfig(
        system_instruction=get_researcher_prompt(),
        tools=[grounding_tool],
        temperature=0.0,  # 사실 수집이므로 온도를 낮춤
        thinking_config=types.ThinkingConfig(thinking_budget=24576, include_thoughts=False) # Dynamic thinking budget
    )

    research_response = None
    chunks = None
    
    # 검색 실패 시 재시도 로직
    for attempt in range(3):
        try:
            research_response = client.models.generate_content(
                model=RESEARCH_MODEL_NAME,
                contents=research_prompt,
                config=research_config,
            )
            # 검색 결과(Chunks)가 있는지 확인
            if research_response.candidates[0].grounding_metadata.grounding_chunks:
                chunks = research_response.candidates[0].grounding_metadata.grounding_chunks
                break
            else:
                print(f"      (Attempt {attempt+1}: No grounding chunks found. Retrying...)")
                time.sleep(2) # 짧은 대기
        except Exception as e:
            print(f"      (Attempt {attempt+1} Failed: {e})")
            time.sleep(2 * (attempt + 1))
            if attempt == 2: raise

    # Phase 1 결과에서 인용구 처리
    citation_list_str = ""
    if chunks:
        for x in chunks:
            try:
                # 최종 URL 확인 (선택 사항, 속도가 느리다면 제거 가능)
                final_url = get_final_url_urllib(x.web.uri)
                title = x.web.title if x.web.title else "Reference"
                citation_list_str += f"* [{title}]({final_url})\n"
            except:
                continue
    else:
        citation_list_str = "* (No web citations found during research phase)\n"

    research_notes = research_response.text

    print(f"      Collected {len(chunks)} chunks")

    print(f"   ...Phase 1.5: Selecting NEXT topic...")
    
    # 최근 기록 문자열 생성 (state 관리 필요, 여기서는 단순화)
    recent_history_str = f"Previous: {state.get('last_topic', 'N/A')}, Current: {next_topic}"

    planner_config = types.GenerateContentConfig(
        system_instruction=get_planner_prompt(),
        tools=[grounding_tool],
        temperature=0.0,  # 사실 수집이므로 온도를 낮춤
        thinking_config=types.ThinkingConfig(thinking_budget=24576, include_thoughts=False) # Dynamic thinking budget
    )

    planner_prompt = f"""
**Current Context:**
* Current Topic: {next_topic} ({next_year})
* Recent Topics History: {recent_history_str} (Consider this to avoid excessive repetition unless necessary)
"""

    # Planner도 Flash 모델 사용 (빠르고 저렴함)
    planner_response = client.models.generate_content(
        model=RESEARCH_MODEL_NAME, # gemini-2.5-flash
        contents=planner_prompt,
        config=planner_config
    )

    print(f"      Planner Response: {planner_response.text}")

    next_plan = json.loads(repair_json(planner_response.text))
    print(f"      -> Next Plan: {next_plan['next_topic']} ({next_plan['next_year']})")
    print(f"      -> Reason: {next_plan['reasoning']}")


    print(f"   ...Phase 2: Writing content with {WRITER_MODEL_NAME}")

    # --- Phase 2: Writing with Pro (No Grounding Tool) ---
    # [수정] Writer에게는 더 이상 인용구 목록을 입력으로 주지 않으며, 
    # 본문 작성에만 집중하도록 요청합니다.
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
        temperature=0.4, # 창의적인 글쓰기를 위해 온도 상향
        #response_mime_type='application/json',
        #response_json_schema=HistoryBotResponse.model_json_schema(),
        thinking_config=types.ThinkingConfig(thinking_level="high", include_thoughts=False) # Dynamic thinking budget
    )

    writer_response = client.models.generate_content(
        model=WRITER_MODEL_NAME,
        contents=writer_user_prompt,
        config=writer_config
    )

    # JSON 파싱 및 복구
    response_json = HistoryBotResponse.model_validate_json(repair_json(writer_response.text))

    # [중요] 파이썬 코드 레벨에서의 후처리 (Post-processing)
    # AI의 환각(Hallucination) 방지를 위해 참고 문헌과 면책 조항은 직접 문자열 결합
    response_json.content += f"\n\n## 📚 참고 문헌\n{citation_list_str}"
    response_json.content += f"\n\n*이 콘텐츠는 AI에 의해 생성되었으며, 오류나 부정확한 정보를 포함할 수 있습니다.*"
    
    return response_json

# --- [Main Execution] ---

def extract_metadata(content, current_state):    
    new_state = current_state.copy()
    new_state['day_count'] += 1
    new_state['last_run_date'] = datetime.now().strftime("%Y-%m-%d")
    new_state['current_year'] = content.metadata.current_year
    new_state['last_topic'] = content.metadata.last_topic
    new_state['next_topic'] = content.metadata.next_topic
    new_state['next_year'] = content.metadata.next_year
    return new_state

def main():
    state = load_state()
    
    current_actual_year = datetime.now().year
    termination_threshold = current_actual_year - 3

    # 종료 조건 검사
    next_year_candidate = state.get('next_year')
    if not isinstance(next_year_candidate, int) or next_year_candidate >= termination_threshold:
        if state['day_count'] > 0:
            print("🛑 [알림] 역사 봇의 여정이 완료되었습니다.")
        else:
             print("⚠️ [경고] 초기 상태 오류. bot_state.json을 확인하세요.")
        return

    print(f"🤖 Day {state['day_count']} 콘텐츠 생성 시작... ({state['next_year']}년 {state['next_topic']})")
    
    try:
        # 하이브리드 생성 함수 호출
        content_response = generate_daily_content(state)
        
        # --- 종료 조건 도달 시 '내일의 예고' 교체 로직 (기존 유지) ---
        if content_response.metadata.next_year >= termination_threshold:
            target_header = "## 📅 내일의 키워드 예고"
            citation_header = "## 📚 참고 문헌"
            
            replacement_section = f"""
## 🛑 긴 여정의 마침표
우리는 찰스 배비지의 해석기관부터 시작해 숨 가쁘게 달려왔습니다.
다음 이정표는 {content_response.metadata.next_year}년의 '{content_response.metadata.next_topic}'입니다.

하지만 본 역사 봇은 동시대의 사건에 대한 평가는 미래의 역사가들에게 맡기고, 
현재로부터 3년 전까지의 기록을 끝으로 긴 여정을 마무리하고자 합니다.

오늘이 바로 그 마지막 페이지입니다.
그동안 '생각하는 기계'를 향한 인류의 위대한 여정에 함께 해주셔서 진심으로 감사합니다.
"""
            # 안전하게 본문 교체
            if target_header in content_response.content:
                base_content = content_response.content.split(target_header)[0].strip()
                citation_start_index = content_response.content.find(citation_header)
                if citation_start_index != -1:
                    footer_content = content_response.content[citation_start_index:]
                else:
                    footer_content = ""
                content_response.content = f"{base_content}\n\n{replacement_section}\n\n{footer_content}"

        # 파일 저장 로직
        content = content_response.content.strip()
        # 제목 추출 (첫 줄) 및 마크다운(#) 제거
        title = content.splitlines()[0].replace("#", "").strip()
        
        body = "\n".join(content.splitlines()[1:]).strip()
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-day{state['day_count']}.md"
        
        # Jekyll/Github Pages 호환용 Front matter
        header = f"""
---
title:  "{title}"
categories:
  - cs_history
toc: true
toc_sticky: true
comments: true
---
"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 저장 경로 설정 (상위 폴더의 _posts/cs_history)
        target_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "_posts", "cs_history"))
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