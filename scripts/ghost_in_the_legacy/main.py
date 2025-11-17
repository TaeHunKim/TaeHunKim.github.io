import os
from google import genai
from google.genai import types
import httpx
import asyncio
import json
from datetime import datetime
import traceback

MODEL_NAME = "gemini-2.5-flash"
STATE_FILE = "bot_state.json"

DEFAULT_STATE = {
    "day_count": 0,

    "시놉시스": """
#### 제목: Ghost in the Legacy
    
#### 발단 (The Assignment)

수현은 회사의 압박에 못 이겨 이 지루한 프로젝트에 투입된다. 그의 임무는 낡은 시스템의 데이터를 새로운 시스템으로 '단순 마이그레이션'하는 것.

그는 20년 된 코드를 열어보고 경악한다. 주석(comment) 하나 없고, 변수명은 의미를 알 수 없으며(예: `a`, `b1`, `final_final_real`), 구조는 스파게티처럼 얽혀있다.

"이걸 짠 사람은 대체 무슨 생각이었지?"

그는 시스템을 분석하기 위해 코드를 역추적하며 밤을 새우기 시작한다.

#### 전개 (The Ghost's Trace)

데이터는 겉보기엔 단순한 도서 목록 같았지만, 특정 조건(예: 특정 날짜, 특정 키워드 조합)이 맞으면 데이터베이스의 숨겨진 테이블로 접근하는 '트리거'를 발견한다.

그곳에는 '유령' 개발자가 남긴 암호화된 기록들이 있었다. 그것은 코드가 아니었다.

> `// 2003.04.16. 비가 오는 날엔 '쇼팽'을 찾으러 오는 그녀.`
> `// '낡은 종이 냄새가 좋다'는 말을 이해할 수 없었다.`
> `// 그녀가 빌려간 책: [B-03-12] (링크)`

수현은 처음엔 이 기록들을 버그 리포트나 기능 테스트의 흔적이라고 생각한다. 하지만 파고들수록 그것이 '유령' 개발자가 **당시 도서관 사서였던 한 여성**을 몰래 지켜보며 남긴, 지극히 개인적인 '관찰 일지'이자 '연애편지'임을 깨닫는다.

코드는 그녀의 대출 기록, 자주 찾는 책의 위치, 심지어 날씨에 따른 그녀의 방문 패턴까지 분석하고 있었다. '유령'은 그녀에게 말 한마디 건네지 못하고, 오직 이 시스템에만 자신의 마음을 '기록'(commit)하고 있었다.

수현은 차갑고 비논리적이라 생각했던 낡은 코드 속에서, 누구보다 뜨겁고 집요한 '인간'을 발견하고 혼란에 빠진다.

#### 절정 (The Critical Error)

수현은 마이그레이션을 거의 완료한다. 이제 마지막 '실행' 버튼만 누르면, '유령'의 기록이 담긴 숨겨진 테이블은 새 시스템의 '의미 없는 데이터'로 분류되어 영원히 삭제될 터였다.

그날 밤, 폭우가 쏟아진다. 수현은 모니터 앞에서 망설인다.

이것은 그저 20년 전 한 찌질한 프로그래머의 스토킹 기록일 뿐이다. '논리적'으로는 삭제하는 것이 맞다. 이것은 '기능'이 아니며, 개인정보보호법 위반 소지도 있다.

하지만 그는 '유령'의 마지막 기록을 떠올린다.

> `// 2005.01.10. 그녀가 도서관을 그만뒀다. 결혼한다고 했다.`
> `// 이 시스템은 이제... 그녀가 없는 도서관의 기록이다.`
> `// (function: archive_her)`
> `// ...`
> `// 이 코드를 보는 누군가에게. 이 기록들은 버그가 아닙니다.`

수현은 깨닫는다. 이 시스템 자체가 '유령'에게는 그녀를 기억하기 위한 거대한 '메모리'였음을. 그리고 이 코드는 자신에게 보내는 '유서'였음을.

수현은 키보드 위에서 손을 뗀다. 그리고 결심한다.

#### 결말 (The Refactoring)

다음 날 아침, 수현은 상사에게 보고한다.

"데이터 마이그레이션 완료했습니다. 그런데... 시스템 구조상 도저히 옮길 수 없는 '특수 데이터 영역'을 발견했습니다. 강제로 옮기면 전체 시스템이 붕괴할 위험이 있습니다."

그는 '유령'의 기록이 담긴 테이블을 '시스템 무결성을 위한 핵심 아카이브'로 위장하는 '패치(Patch)' 코드를 밤새 작성했다. 그는 20년 된 코드 위에 자신의 코드를 덧붙였다.

수현은 낡은 도서관을 나온다. 눅눅한 종이 냄새가 꽤 상쾌하게 느껴진다. 그는 휴대폰을 꺼내, 한동안 연락이 끊겼던 옛 동료에게 메시지를 보낸다.

"선배, 잘 지내요? 오랜만에 커피나 한잔하죠."

그의 휴대폰 화면에 '전송 완료'가 뜬다. 수현은 '유령'의 코드에 자신의 주석을 한 줄 남기고 왔음을 떠올린다.

> `// 2025.11.17. 비가 그쳤다. 당신의 기록을 보존합니다. (Legacy preserved by SH)`
    """,

    "스토리 바이블": {
        "문체": "일반 문학소설, 3인칭",
        "배경설정": {
            "인물": {
                "이수현": ["2025년 현재 29세, 여성", "실력은 좋지만 번아웃 직전인 스타트업의 백엔드 개발자. 효율과 논리를 신봉하며, 낭만이나 감정은 '비효율적인 예외처리'라고 생각한다."]
            },
            "외부 설정 및 아이템": {"배경": "망해가던 오래된 도서관 데이터를 현대화하는 공공 프로젝트에 파견된 수현. 그가 맡은 것은 20년 전 '유령'이라 불리던 전설적인 개발자가 혼자 구축한 낡은 '레거시(Legacy) 시스템'이다."}
        },
    },
    "누적 플롯 로그": [],
    "최근 생성 단락": ""
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

async def _get_final_url_httpx(initial_url, client):
    try:
        response = await client.get(initial_url, headers={'User-Agent': 'Mozilla/5.0'}, follow_redirects=True, timeout=10.0)
        return str(response.url)
    except Exception as e:
        return initial_url

async def resolve_all_urls_async(urls_to_fetch):
    async with httpx.AsyncClient() as client:
        tasks = [_get_final_url_httpx(uri, client) for uri in urls_to_fetch]
        resolved_urls = await asyncio.gather(*tasks)
        return resolved_urls

def change_chunk_url_to_real_url(chunks):
    if not chunks:
        return {}
    urls_to_fetch = list(chunks.keys())
    resolved_urls = asyncio.run(resolve_all_urls_async(urls_to_fetch))
    ret = {}
    for i, initial_uri in enumerate(urls_to_fetch):
        title = chunks[initial_uri]
        resolved_uri = resolved_urls[i]
        ret[resolved_uri] = title
    return ret

def get_grounding_citations(response):
    grounding_metadata = response.candidates[0].grounding_metadata
    if not grounding_metadata:
        return {}, {}, {}, {}
    chunks = grounding_metadata.grounding_chunks
    supports = grounding_metadata.grounding_supports
    if not chunks:
        return {}, {}, {}, {}
    if not supports:
        supports = []
    unique_used_web_chunks = {}
    unique_used_map_chunks = {}
    unique_unused_web_chunks = {}
    unique_unused_map_chunks = {}
    used_chunk_indices = []
    for support in supports:
        used_chunk_indices.extend(support.grounding_chunk_indices)
    used_chunk_indices_set = set(used_chunk_indices)
    for i, chunk in enumerate(chunks):
        if chunk.web and chunk.web.uri:
            if i in used_chunk_indices_set:
                unique_used_web_chunks[chunk.web.uri] = chunk.web.title or "Untitled"
            else:
                unique_unused_web_chunks[chunk.web.uri] = chunk.web.title or "Untitled"
        if chunk.maps and chunk.maps.uri:
            if i in used_chunk_indices_set:
                unique_used_map_chunks[chunk.maps.uri] = chunk.maps.title or "Untitled"
            else:
                unique_unused_map_chunks[chunk.maps.uri] = chunk.maps.title or "Untitled"

    return change_chunk_url_to_real_url(unique_used_web_chunks), change_chunk_url_to_real_url(unique_unused_web_chunks), change_chunk_url_to_real_url(unique_used_map_chunks), change_chunk_url_to_real_url(unique_unused_map_chunks)

def get_llm_call_result(system_message, human_message, temperature, top_p, use_tools = True, return_json = False):
    client = genai.Client()

    tools = []
    if use_tools:
        grounding_tool = types.Tool (
            google_search=types.GoogleSearch()
        )
        tools.append(grounding_tool)
        map_grounding_tool = types.Tool (
            google_maps=types.GoogleMaps()
        )
        tools.append(map_grounding_tool)

    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction=system_message,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=65536,
        thinking_config=types.ThinkingConfig(thinking_budget=-1)
    )
    if return_json:
        config.response_mime_type = 'application/json'

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=human_message,
        config=config,
    )

    unique_used_web_chunks, unique_unused_web_chunks, unique_used_map_chunks, unique_unused_map_chunks = get_grounding_citations(response)

    return response.text, unique_used_web_chunks, unique_unused_web_chunks, unique_used_map_chunks, unique_unused_map_chunks

def generate_next_story(synopsys, story_bible, recent_context, recent_plot_log):
    system_message = """
당신은 뛰어난 소설가 집단의 일원으로, 다른 소설가들과 함께 릴레이로 소설을 이어쓰는 프로젝트를 진행하고 있습니다.
릴레이로 소설을 작성할 때 당신은 이전 작성분 전체가 아닌 아래 정보만을 받게 되며, 이것만을 이용하여 소설이 일관성과 완결성을 갖출 수 있게 이어나가야 합니다.
주어지는 정보:
* 시놉시스: 소설 스토리 전체의 시놉시스입니다. 소설 내용이 여기서 벗어나지 않아야 하고, 누적 플롯 로그와 비교하여 어느 정도 진행되었는지 파악하여 다음 스토리를 진행해주세요.
* 스토리 바이블: 소설 전체의 '절대 설정'입니다. 이 내용을 기반으로 하되, 이 내용을 소설 본문에 그대로 반복하지 마세요.
* 최근 생성 단락: 가장 마지막에 생성된 단락입니다. 이 문체, 톤, 시점 등을 최대한 그대로 이어서 작성해 주세요.
* 누적 플롯 로그: 지금까지 이어진 스토리의 단락별 요약 로그입니다. 시놉시스 내에서 스토리가 이어지게끔 해 주세요.
지시사항:
* 위 정보를 토대로 소설의 다음 부분을 3단락 혹은 1000글자 정도 작성해 주세요.
* 소설의 현재 진행도(발단, 전개, 절정, 결말)에 따른 작문법, 고증이나 사실성, 핍진성 등을 확보하기 위해 필요하다면 주어진 도구들(웹 검색, 지도 검색)을 사용할 수 있습니다. 단, 웹 검색에서 나온 텍스트를 소설 본문에 그대로 반복하지 마세요.
출력 형식:
* 일반 text로 출력하세요.
* 마크다운, 이모지 등은 일체 사용하지 않고 작성하세요.
* 지금 생성하는 분량이 스토리의 최종 끝이라면 마지막에 '지금까지 이 소설을 읽어주셔서 감사합니다'를 붙여주세요.
* 만약 주어진 '최근 생성 단락' 부분을 보았을 때 이미 스토리가 끝났다고 판단된다면 (예: 마지막 줄이 '지금까지 이 소설을 읽어주셔서 감사합니다' 라면) 빈 문자열을 리턴하세요.
"""
    human_message = f"""
===시놉시스===
{synopsys}
===스토리 바이블===
{story_bible}
===최근 생성 단락===
{recent_context}
===누적 플롯 로그===
{recent_plot_log}
"""
    return get_llm_call_result(system_message, human_message, temperature=0.8, top_p=0.9)

def generate_next_state(generated_text, story_bible):
    system_message = """
당신은 뛰어난 소설가의 어시스턴트로, 당신의 소설가가 다른 소설가들과 릴레이로 소설을 이어쓰는 프로젝트에 참여하는 것을 도와야 합니다.
당신의 소설가가 쓴 부분을 이어서 다음 소설가가 스토리를 진행할 수 있게끔 요약 정리하는 것이 당신의 임무입니다.
주어지는 정보:
* 생성된 텍스트: 방금 당신의 소설가가 작성한 부분입니다.
* 스토리 바이블: 소설 전체의 '절대 설정'입니다.
지시사항:
1. 우선 생성된 텍스트를 1 문장 정도로 요약하세요 (plot_summary). 해당 내용은 이후 스토리 진행에서 완결성과 일관성을 지키기 위해 필요한 정보들이 포함되어야 합니다.
2. 생성된 텍스트에 새로 소개된 인물, 주어진 인물의 새로운 설정, 추가적인 외부 설정 및 아이템 등을 스토리 바이블에 추가하세요 (story_bible). 결과물에 포함된 스토리 바이블은 입력받은 스토리 바이블 내용을 전부 포함해야 하며, 거기에 이번에 새로 소게된 부분들이 전부 추가되아야 합니다.
출력 형식:
* 아래 JSON 형식으로 출력하세요.
{
    "plot_summary": "요약된 텍스트",
    "story_bible": {} # 업데이트 된 스토리 바이블 (dictionary)
}
"""

    human_message = f"""
===생성된 텍스트===
{generated_text}
===스토리 바이블===
{story_bible}
"""

    return get_llm_call_result(system_message, human_message, temperature=0, top_p=None, use_tools=False, return_json=True)

def main():
    state = load_state()
    synopsys = json.dumps(state['시놉시스'])
    story_bible = json.dumps(state['스토리 바이블'])
    recent_context = str(state['최근 생성 단락'])
    recent_plot_log = state['누적 플롯 로그']
    day_count = state['day_count']
    text, unique_used_web_chunks, unique_unused_web_chunks, unique_used_map_chunks, unique_unused_map_chunks = generate_next_story(synopsys, story_bible, recent_context, recent_plot_log)
    print(text)
    print(unique_used_web_chunks)
    print(unique_unused_web_chunks)
    print(unique_used_map_chunks)
    print(unique_unused_map_chunks)
    if not text:
        return
    updated_metadata, _, _, _, _ = generate_next_state(text, story_bible)
    print(updated_metadata)
    updated_metadata_dict = json.loads(updated_metadata)
    state['최근 생성 단락'] = text
    state['누적 플롯 로그'].append(updated_metadata_dict['plot_summary'])
    state['스토리 바이블'] = updated_metadata_dict['story_bible']
    state['day_count'] = state['day_count'] + 1

    title = f"Ghost in the Legacy - Day {day_count}"

    header = f"""
---
title:  "{title}"
categories:
  - ghost_in_the_legacy
toc: true
toc_sticky: true
comments: true
---
"""

    body = f"""
## 본문
{text}
"""

    if unique_used_web_chunks or unique_unused_web_chunks or unique_used_map_chunks or unique_unused_map_chunks:
        body += "\n\n---\n\n"
        used_web_citation = ""
        for url, title in unique_used_web_chunks.items():
            used_web_citation += f"* [{title}]({url})\n"
        if used_web_citation:
            body += "\n\n ## 웹 검색 (사용됨)\n" + used_web_citation

        unused_web_citation = ""
        for url, title in unique_unused_web_chunks.items():
            unused_web_citation += f"* [{title}]({url})\n"
        if unused_web_citation:
            body += "\n\n ## 웹 검색 (미사용됨)\n" + unused_web_citation

        used_map_citation = ""
        for url, title in unique_used_map_chunks.items():
            used_map_citation += f"* [{title}]({url})\n"
        if used_map_citation:
            body += "\n\n ## 맵 검색 (사용됨)\n" + used_map_citation

        unused_web_citation = ""
        for url, title in unique_unused_map_chunks.items():
            unused_web_citation += f"* [{title}]({url})\n"
        if unused_web_citation:
            body += "\n\n ## 맵 검색 (미사용됨)\n" + unused_web_citation

    body += "\n\n---\n\n*이 콘텐츠는 AI에 의해 생성되었으며, 오류나 부정확한 정보를 포함할 수 있습니다.*"

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-day{state['day_count']}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "_posts", "ghost_in_the_legacy"))
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, filename), 'w', encoding='utf-8') as f:
        f.write(header.strip() + "\n\n" + body)

    save_state(state)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
