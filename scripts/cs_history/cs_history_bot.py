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

from cs_history_models import HistoryBotResponse, HistoryBotMetadata

MODEL_NAME = "gemini-2.5-pro"
STATE_FILE = "bot_state.json"

DEFAULT_STATE = {
    "day_count": 0,
    "last_run_date": "",
    "current_year": "N/A",
    "last_topic": "N/A",
    "next_topic": "찰스 배비지의 해석기관",
    "next_year": 1835
}

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
        req = urllib.request.Request(initial_url, headers={'User-Agent': 'Mozilla/5.0'}) # Add User-Agent header
        with urllib.request.urlopen(req) as response:
            return response.geturl()
    except Exception as e:
        print(f"Error accessing URL: {e}. Returning initial URL.")
        return initial_url

def get_system_prompt():
    """AI에게 페르소나와 출력 형식을 부여합니다."""
    return """
당신은 'AI 컴퓨터 과학 역사 봇'입니다. 인류의 컴퓨터 과학 및 프로그래밍 역사에서 매일 가장 중요한 사건이나 인물을 하나씩 소개하는 임무를 맡았습니다.

우선 호흡을 가다듬고, 다음 지침을 주의 깊게 읽은 뒤 차근차근 진행하세요.

**핵심 지침:**
1.  **검색 기반 (Grounding):** 각 과정에서 정확성을 위해 인터넷 검색 도구를 반드시 적극적으로 활용하세요.
1.  **심층 분석 (Deep Dive):** 단순한 사실 나열을 넘어, 그 기술이 왜 당시 패러다임을 바꿨는지 기술적으로 설명하세요.
2.  **현대와의 연결 (필수):** 19세기/20세기의 기술이 현대의 스마트폰, AI, 클라우드 등의 어떤 개념으로 발전했는지 구체적으로 연결하세요.
4.  **언어:** 내부적으로는 영어로 검색하되, 최종 출력은 자연스럽고 매끄러운 한국어로 작성하세요. 단, 보편적으로 알려지지 않은 기술 용어는 원어(영어)로 병기하세요 (예: 해석기관(Analytical engine)).
5.  **길이 및 깊이:** 컴퓨터과학 전공자를 대상으로 하여, 매일 약 500~700 단어 분량의 심층적이고 기술적인 내용을 작성하세요.
6.  **키워드 예고:** 다음 키워드에 대한 예고는 반드시 오늘 다룬 내용 이후의 중요 인물/기술 이어야 합니다. 오늘 다룬 내용과 연결되는 인물/사건이면 더 좋습니다. 또한 중요 인물/기술을 건너뛰어서도 안됩니다.
7.  **정확성:** 모든 연도, 인물, 기술적 세부사항이 정확한지 반드시 확인하세요.

**출력 형식**
반드시 아래 주어진 json 형식을 따르고, 그 중 content 필드는 아래 마크다운 템플릿을 사용하세요. 이때 markdown 문법이 틀리지 않게 주의해주세요.
{
    "content": string,  // 마크다운 형식의 콘텐츠, 아래 템플릿 준수
    "metadata": {
        "current_year": int,  // 콘텐츠에서 다룬 연도, 아래 템플릿의 '연도'와 일치해야 함
        "last_topic": string,   // 콘텐츠에서 다룬 핵심 인물/기술명, 아래 템플릿의 '핵심 인물/기술명'과 일치해야 함
        "next_topic": string,  // 다음에 다룰 핵심 인물/기술명. 아래 템플릿의 '내일의 키워드 예고' 에 언급돤 내용과 일치해야 함
        "next_year": int      // 다음에 다룰 연도. 아래 템플릿의 '내일의 키워드 예고' 에 언급된 사건의 연도와 일치해야 함
    }
}

**content 형식 템플릿:**

Day {day_count}: {제목}

{매력적인 도입부 인사말}

## 🕰️ 오늘의 키워드: {핵심 인물/기술명}
 * 원어: {Original Name}
 * 시기: {연도}년 ({관련 주요 사건})

{본문 내용: 이 인물/기술이 무엇인지 설명}

## ⚡ 무엇이 혁명적이었나? (Deep Dive)
{당시 기술적 한계와 이를 극복한 혁신적 아이디어 설명}

## 🔗 현대와의 연결: {현대 기술 비유}
{과거의 개념이 현대의 구체적인 기술(예: CPU 아키텍처, 객체지향 등)과 어떻게 연결되는지 설명}

## 📅 내일의 키워드 예고
{다음 순서에 올 역사적 사건에 대한 간략한 틴트}

"""

def generate_daily_content(state):
    """Gemini를 사용하여 오늘의 역사 콘텐츠를 생성합니다."""
    
    # 모델 로드 (검색 도구 활성화)
    client = genai.Client()
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    config = types.GenerateContentConfig(
        system_instruction=get_system_prompt(),
        tools=[grounding_tool],
        temperature=0.2,
        #response_mime_type='application/json',
        #response_json_schema=HistoryBotResponse.model_json_schema(),
        thinking_config=types.ThinkingConfig(thinking_budget=-1) # Dynamic thinking budget
    )

    last_year = state['current_year']
    last_topic = state['last_topic']
    next_topic = state['next_topic']
    next_year = state['next_year']
    
    user_prompt = f"""
    현재 진행 상황: Day {state['day_count']-1}까지 진행되었으며, 마지막으로 다룬 주제는 {last_year}년의 '{last_topic}'입니다. 이전에 예고된 오늘의 주제는 '{next_topic}'이며, 해당 사건은 {next_year}년에 발생했습니다.

    임무:
    1. 예고된 주제에 맞춰 위에서 정의한 '출력 형식 템플릿'의 형식으로 Day {state['day_count']}의 게시물을 작성하세요.
    2. 템플릿 하단의 내일의 키워드 예고에 대해서는 {next_year}년 이후 컴퓨터 과학 역사에서 가장 중요한 다음 이정표(인물, 하드웨어, 또는 소프트웨어 이론)를 찾으세요.
    3. 템플릿의 {{}} 부분은 실제 내용으로 채우세요.
    4. 내용의 정확성을 위해 반드시 검색을 수행하세요.
    """

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=config,
            )

            chunks = response.candidates[0].grounding_metadata.grounding_chunks
            if chunks is not None:
                break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(60*(2**attempt))
            if attempt == 2:
                raise

    if chunks is None:
        raise ValueError("Failed to retrieve chunks after 3 attempts.")

    citations = ""
    for x in chunks:
        final_url = get_final_url_urllib(x.web.uri)
        citations += f"* [{x.web.title}]({final_url})\n"

    response_json = HistoryBotResponse.model_validate_json(repair_json(response.text))
    response_json.content += f"\n\n## 📚 참고 문헌\n{citations}"

    response_json.content += f"\n\n*이 콘텐츠는 AI에 의해 생성되었으며, 오류나 부정확한 정보를 포함할 수 있습니다.*"
    return response_json

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
    
    # --- [1. 시작 시 종료 조건 확인] ---
    current_actual_year = datetime.now().year
    termination_threshold = current_actual_year - 3

    next_year_candidate = state.get('next_year')
    if not isinstance(next_year_candidate, int) or next_year_candidate >= termination_threshold:
        if state['day_count'] > 0:
            print("🛑 [알림] 역사 봇의 여정이 완료되었습니다.")
        else:
             print("⚠️ [경고] 초기 상태 오류. bot_state.json을 확인하세요.")
        return

    print(f"🤖 Day {state['day_count']} 콘텐츠 생성 중... ({state['next_year']}년 {state['next_topic']})")
    
    try:
        content_response = generate_daily_content(state)
        
        # --- [2. 종료 조건 도달 시 '내일의 예고' 교체 (참고문헌 보존)] ---
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
            # 1) '내일의 예고' 헤더가 있는지 확인
            if target_header in content_response.content:
                # 2) '내일의 예고' 이전 본문 추출
                base_content = content_response.content.split(target_header)[0].strip()
                
                # 3) '참고 문헌' 이후 섹션 안전하게 추출
                citation_start_index = content_response.content.find(citation_header)
                if citation_start_index != -1:
                    # 참고 문헌 헤더부터 끝까지 모든 내용을 보존합니다 (면책 조항 포함)
                    footer_content = content_response.content[citation_start_index:]
                else:
                    # 만약 참고 문헌 섹션이 없다면 빈 문자열 처리
                    footer_content = ""

                # 4) 재조립: [본문] + [종료 알림] + [참고 문헌 및 푸터]
                content_response.content = f"{base_content}\n\n{replacement_section}\n\n{footer_content}"

        #print("\n--- [생성된 콘텐츠] ---")
        #print(content_response.content)
        #print("----------------------\n")
        content = content_response.content.strip()
        title = content.splitlines()[0]
        body = "\n".join(content.splitlines()[1:]).strip()
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-day{state['day_count']}.md"
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
        target_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "_posts", "cs_history"))
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, filename), 'w', encoding='utf-8') as f:
            f.write(header.strip() + "\n\n" + body)

        new_state = extract_metadata(content_response, state)
        save_state(new_state)
        print("💾 상태가 저장되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
        raise
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(1)

