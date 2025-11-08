from pydantic import BaseModel, Field
from typing import List

class HistoryBotMetadata(BaseModel):
    current_year: int = Field(
        ...,
        description="The year being discussed in the content, must match the year in the content template"
    )
    last_topic: str = Field(
        ...,
        description="The main topic/person being discussed, must match the keyword in the content template"
    )
    next_year: int = Field(
        ...,
        description="The year which will be discussed in the next content, must match the year of the topic in the preview section in the content template"
    )
    next_topic: str = Field(
        ...,
        description="The main topic/person which will be discussed in the next content, must match the topic in the preview section in the content template"
    )

class HistoryBotResponse(BaseModel):
    content: str = Field(
        ...,
        description="Markdown formatted content following the specified template structure"
    )
    metadata: HistoryBotMetadata = Field(
        ...,
        description="Metadata about the current history bot response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": """---
[역사 봇] Day 1: 에이다 러브레이스와 최초의 프로그래밍
안녕하세요! 오늘은 프로그래밍의 시작을 알린 위대한 인물을 소개합니다.

🕰️ 오늘의 키워드: 에이다 러브레이스
 * 원어: Ada Lovelace
 * 시기: 1843년 (최초의 컴퓨터 프로그램 발표)
에이다 러브레이스는 찰스 배비지의 해석기관을 위한 최초의 알고리즘을 작성했습니다.

⚡ 무엇이 혁명적이었나? (Deep Dive)
당시에는 기계식 계산기의 개념조차 생소했던 시기에, 에이다는 추상적인 프로그래밍 개념을 발전시켰습니다.

🔗 현대와의 연결: 현대 프로그래밍 언어의 기초
오늘날 우리가 사용하는 프로그래밍 언어의 기본 개념들이 이미 에이다의 노트에 담겨 있었습니다.

📅 내일의 키워드 예고
다음에는 부울 대수의 탄생에 대해 알아보겠습니다.
---""",
                "metadata": {
                    "current_year": 1843,
                    "last_topic": "에이다 러브레이스"
                }
            }
        }