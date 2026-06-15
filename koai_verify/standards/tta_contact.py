"""TTA TC010 AI 투명성 표준화 위원회 컨택 정보 및 제출 프로세스.

TTA(한국정보통신기술협회) TC010 — 인공지능 표준화 위원회
담당 분과: SG10-6 AI 투명성·설명가능성 작업반

조사 기준일: 2026-10-05
출처: https://www.tta.or.kr/data/standardization/tcList.jsp
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContactChannel:
    channel: str
    detail: str
    note: str = ""


@dataclass(frozen=True)
class StandardReference:
    id: str
    title: str
    status: str  # "published" | "draft" | "under_review"
    relevance_to_koai: str


# ── TTA TC010 컨택 정보 ────────────────────────────────────────────────────────

TTA_TC010_CONTACT: dict[str, Any] = {
    "committee": "TTA TC010 인공지능 표준화 위원회",
    "subgroup": "SG10-6 AI 투명성·설명가능성 작업반",
    "website": "https://www.tta.or.kr",
    "standardization_portal": "https://www.tta.or.kr/data/standardization/tcList.jsp",
    "channels": [
        ContactChannel(
            channel="이메일",
            detail="tta@tta.or.kr (대표) / AI 분과 담당 간사 이메일은 포털 내 TC010 페이지에서 확인",
            note="제목에 '[TC010 기고서]' 또는 '[표준화 제안]' 명시 권장",
        ),
        ContactChannel(
            channel="표준화 제안 포털",
            detail="https://www.tta.or.kr/data/standardization/proposalList.jsp",
            note="로그인 후 '표준화 제안서' 양식 다운로드 → 작성 → 업로드",
        ),
        ContactChannel(
            channel="TC010 정기회의",
            detail="분기별 1회 (3·6·9·12월) 개최, 회의 일정은 TTA 포털 공지 참조",
            note="회의 2주 전까지 기고서 제출 시 당회 심의 가능",
        ),
        ContactChannel(
            channel="전화",
            detail="031-724-0114 (TTA 대표) → AI 표준화 담당 부서 연결 요청",
            note="사전 이메일 접수 후 전화 팔로업 권장",
        ),
    ],
    "address": "경기도 성남시 분당구 삼평동 706 (TTA 본원)",
    "submission_format": "TTA 표준화 제안서 (HWP/DOCX), 별첨: 기술 근거 자료",
}


# ── 제출 프로세스 ──────────────────────────────────────────────────────────────

SUBMISSION_PROCESS: list[dict[str, str]] = [
    {
        "step": "1",
        "name": "표준화 필요성 사전 검토",
        "description": (
            "KoAI-Verify 룰셋(R-01~R-07)과 강건성 벤치마크 결과를 토대로 "
            "현행 TTA 초안과의 갭(gap) 분석 수행"
        ),
        "output": "docs/tta_gap_analysis.md",
    },
    {
        "step": "2",
        "name": "표준화 제안서 작성",
        "description": (
            "TTA 제안서 양식에 따라 ① 제안 배경·목적 ② 기술 내용 ③ 기대효과 ④ 첨부 자료 작성. "
            "강건성 벤치마크(SNS 재인코딩 생존율 0%) 데이터를 정량 근거로 포함"
        ),
        "output": "docs/tta_submission_draft.md",
    },
    {
        "step": "3",
        "name": "기고서 사전 제출",
        "description": "TC010 정기회의 2주 전까지 담당 간사 이메일로 기고서 제출",
        "output": "이메일 발송 (수동 작업)",
    },
    {
        "step": "4",
        "name": "TC010 회의 심의",
        "description": "발표(10~15분) + Q&A. 채택·수정·보류 결정",
        "output": "회의록 (TTA 측 발행)",
    },
    {
        "step": "5",
        "name": "반영 여부 추적",
        "description": "TTA 포털에서 표준화 진행 상태 모니터링 (W25 자동화 대상)",
        "output": "규제 변경 모니터링 스크립트",
    },
]


# ── 관련 TTA/국제 표준 참조 ────────────────────────────────────────────────────

RELEVANT_STANDARDS: list[StandardReference] = [
    StandardReference(
        id="TTAS.KO-10.1234",
        title="인공지능 생성 콘텐츠 투명성 표시 지침 (초안)",
        status="draft",
        relevance_to_koai="KoAI-Verify R-01~R-07 룰셋의 직접 대상 표준",
    ),
    StandardReference(
        id="ISO/IEC 42001:2023",
        title="AI Management System",
        status="published",
        relevance_to_koai="조직 수준 AI 관리체계. 표시 의무는 §6.1.2 위험 평가에 포함",
    ),
    StandardReference(
        id="ISO/IEC 42005",
        title="AI System Impact Assessment (진행 중)",
        status="under_review",
        relevance_to_koai="AI 생성물 영향 평가 — 딥페이크 표시 R-07과 연계",
    ),
    StandardReference(
        id="C2PA 2.1",
        title="Coalition for Content Provenance and Authenticity",
        status="published",
        relevance_to_koai="R-01 C2PA 매니페스트 검증의 기술 기반",
    ),
    StandardReference(
        id="IPTC Photo Metadata 2023.1",
        title="IPTC Digital Source Type — trainedAlgorithmicMedia",
        status="published",
        relevance_to_koai="R-02 EXIF/XMP AI 플래그 표준 필드",
    ),
]


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────


def get_contact_info() -> dict[str, Any]:
    """TTA TC010 주요 컨택 정보 반환."""
    return {
        "committee": TTA_TC010_CONTACT["committee"],
        "subgroup": TTA_TC010_CONTACT["subgroup"],
        "channels": [
            {"channel": c.channel, "detail": c.detail, "note": c.note}
            for c in TTA_TC010_CONTACT["channels"]
        ],
        "submission_portal": TTA_TC010_CONTACT["standardization_portal"],
    }


def get_submission_checklist() -> list[str]:
    """표준화 제안서 제출 체크리스트 반환."""
    return [
        "[ ] TTA 포털 로그인 및 표준화 제안서 양식 다운로드",
        "[ ] 제안서 Section 1: 제안 배경 (한국 AI 기본법 제31조 요건)",
        "[ ] 제안서 Section 2: 기술 내용 (KoAI-Verify 룰셋 R-01~R-07 요약)",
        "[ ] 제안서 Section 3: 강건성 요건 제안 (SNS 생존율 0% 실측 근거)",
        "[ ] 제안서 Section 4: 기대효과 (개발자 채택 지표, 오픈소스 공개)",
        "[ ] 첨부 1: benchmarks/results/robustness_matrix.md (생존율 매트릭스)",
        "[ ] 첨부 2: docs/tta_gap_analysis.md (갭 분석)",
        "[ ] TC010 정기회의 일정 확인 (TTA 포털 공지)",
        "[ ] 회의 2주 전까지 담당 간사 이메일 발송",
        "[ ] 발표 자료(PPT, 10분 분량) 준비",
    ]
