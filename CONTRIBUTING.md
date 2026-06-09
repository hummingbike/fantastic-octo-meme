# Contributing to KoAI-Verify

KoAI-Verify에 기여해주셔서 감사합니다! 이 문서는 코드 스타일, 테스트 요건, PR 절차를 설명합니다.

---

## 시작하기 / Getting Started

```bash
git clone https://github.com/seokwoo-han/fantastic-octo-meme.git
cd fantastic-octo-meme
poetry install
```

---

## 코드 스타일 / Code Style

- **Python 3.10+**, type hints 필수
- 포매터: **black** (line-length=120)
- 린터: **ruff** (E, F, I 규칙)
- 공개 API에만 docstring — 한 줄 요약만, 장황한 설명 금지
- 탐지 불가 케이스는 반드시 `DetectionResult.UNKNOWN` 반환 — 임의 추정 금지

```bash
# 린트 + 포매팅 확인
ruff check .
black --check .

# 자동 수정
black .
ruff check --fix .
```

---

## 커밋 규칙 / Commit Convention

접두어를 반드시 포함하세요:

| 접두어 | 용도 |
|---|---|
| `feat:` | 새 기능 |
| `fix:` | 버그 수정 |
| `test:` | 테스트 추가·수정 |
| `bench:` | 벤치마크 관련 |
| `docs:` | 문서 |
| `refactor:` | 리팩터링 |
| `ci:` | CI/CD 변경 |

W번호를 포함하는 것을 권장합니다:

```
feat(W6): add C2PA manifest parser
fix(W8): correct R-03 rule evaluation for deepfake case
docs(W13): expand README with Korean/English quickstart
```

---

## 테스트 요건 / Testing Requirements

- **mock 금지** — 실제 이미지 픽스처로만 검증 (과거 mock/prod 불일치로 인한 오류 방지)
- 각 탐지 엔진은 **양성/음성/UNKNOWN** 케이스 모두 커버
- 강건성 하니스 테스트는 `tests/integration/` 위치
- 단위 테스트는 `tests/unit/`

```bash
# 단위 테스트 실행
pytest tests/unit/ -v

# 특정 파일
pytest tests/unit/test_c2pa_detector.py -v

# 커버리지 확인
pytest tests/unit/ --tb=short
```

### 픽스처 / Fixtures

테스트용 이미지 픽스처는 `tests/fixtures/` 에 위치합니다. 새 픽스처 추가 시:
- 저작권 클리어한 이미지만 허용
- 합성 이미지는 `tests/fixtures/make_synthetic_samples.py` 패턴 참고
- 픽스처 설명을 `tests/conftest.py` 에 추가

---

## PR 절차 / Pull Request Process

1. `main` 에서 `feat/<W번호>-<brief-description>` 브랜치를 생성
2. 기능 구현 + 단위 테스트 작성 (테스트 먼저 작성 권장)
3. 로컬에서 CI 통과 확인:
   ```bash
   ruff check . && black --check . && pytest tests/unit/ -v
   ```
4. PR 제목: 커밋 규칙과 동일한 형식
5. PR 설명에 변경 사항, 테스트 결과, 관련 룰/스펙 참조 포함
6. 리뷰어 지정 (없으면 @seokwoo-han)

### PR 체크리스트 / PR Checklist

- [ ] 단위 테스트 추가/수정 완료
- [ ] `ruff check .` 통과
- [ ] `black --check .` 통과
- [ ] `pytest tests/unit/` 전체 통과
- [ ] `UNKNOWN` 케이스 처리 확인
- [ ] 보안: 외부 URL 직접 fetch 없음, 이미지 데이터 리포트 미포함

---

## 보안 고지 / Security Notes

- 외부 이미지 URL 처리 시 SSRF 방지 — URL 직접 fetch 금지, 파일 경로만 수신
- 판정 리포트에 원본 이미지 데이터 포함 금지 — 경로/해시만 허용
- 취약점 발견 시 이슈 트래커 대신 이메일(h9379203@gmail.com)로 직접 보고

---

## 문의 / Questions

이슈 트래커나 [GitHub Discussions](https://github.com/seokwoo-han/fantastic-octo-meme/discussions)를 이용해주세요.
