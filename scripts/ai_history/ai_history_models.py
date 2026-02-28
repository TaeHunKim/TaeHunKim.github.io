from pydantic import BaseModel, Field

class HistoryBotMetadata(BaseModel):
    current_year: int = Field(
        ...,
        description="The year being discussed in the content, must match the year in the content template"
    )
    current_topic: str = Field(
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
[AI 인공지능 역사 봇] Day 1: 워런 매컬러와 월터 피츠의 인공 신경망
안녕하세요! 인공지능의 발자취를 따라가는 AI 인공지능 역사 봇입니다. 오늘은 그 위대한 첫걸음을 소개합니다.

## 🕰️ 오늘의 키워드: 워런 매컬러와 월터 피츠의 인공 신경망 모델
 * 원어: McCulloch-Pitts (MCP) Neuron
 * 시기: 1943년 (인경 신경망의 수학적 모델 최초 제안)

워런 매컬러와 월터 피츠는 1943년 논문을 통해 뇌의 뉴런이 어떻게 논리적 연산을 수행하는지 수학적으로 모델링했습니다.

## ⚡ 무엇이 혁명적이었나? (Deep Dive)
단순한 생물학적 관찰을 넘어, 신경계의 활동을 '0과 1'이라는 이진법적 명제 논리로 환원하여 계산 가능한 형태로 만들었다는 점에서 혁명적이었습니다. 

## 🔗 현대와의 연결: 딥러닝의 진정한 기원
이들이 제안한 단순화된 뉴런 모델은 훗날 퍼셉트론(Perceptron)을 거쳐 현대 딥러닝(Deep Learning) 아키텍처를 구성하는 인공 뉴런의 근본적인 뼈대가 되었습니다.

## 📅 내일의 키워드 예고
다음 시간에는 "기계가 생각할 수 있는가?"라는 근본적인 질문을 던진 1950년의 앨런 튜링과 튜링 테스트에 대해 알아보겠습니다.
---""",
                "metadata": {
                    "current_year": 1943,
                    "current_topic": "워런 매컬러와 월터 피츠의 인공 신경망 모델",
                    "next_year": 1950,
                    "next_topic": "앨런 튜링과 튜링 테스트"
                }
            }
        }