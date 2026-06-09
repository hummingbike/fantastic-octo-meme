# W16 수동 작업 항목

이 파일은 자동화/코드로 완료할 수 없어 수동으로 처리해야 하는 항목을 기록합니다.

---

## 1. PyPI 배포

**상태**: CI 설정 완료 (`.github/workflows/release.yml`) — **토큰 등록 필요**

**수동 단계:**
1. [PyPI](https://pypi.org) 계정 생성 (또는 로그인)
2. Settings → API tokens → "Add API token" → Scope: Entire account
3. GitHub 저장소 → Settings → Secrets and variables → Actions
4. `PYPI_TOKEN` 이름으로 발급한 토큰 등록
5. `git tag v0.1.0 && git push origin v0.1.0` — 자동으로 CI가 배포

**확인 URL**: https://pypi.org/project/koai-verify/

---

## 2. Tistory 기술 블로그 게시

**상태**: 초안 완료 (`docs/blog/tistory_w16_draft.md`) — **수동 게시 필요**

**수동 단계:**
1. Tistory 로그인
2. 글쓰기 → `docs/blog/tistory_w16_draft.md` 내용 붙여넣기
3. 태그: `AI기본법, 오픈소스, 검증기, C2PA, EXIF, 한국AI규제`
4. 카테고리: 기술 / 오픈소스
5. 게시 후 URL을 `docs/blog/published_links.md` 에 기록

---

## 3. GeekNews 게시

**상태**: 초안 완료 (`docs/blog/community_post_draft.md`) — **수동 게시 필요**

**수동 단계:**
1. [GeekNews](https://news.hada.io) 로그인 → 링크 제출
2. URL: `https://github.com/hummingbike/fantastic-octo-meme`
3. 제목: `docs/blog/community_post_draft.md` GeekNews 섹션 참조

---

## 4. 디스콰이엇 게시

**상태**: 초안 완료 (`docs/blog/community_post_draft.md`) — **수동 게시 필요**

**수동 단계:**
1. [디스콰이엇](https://disquiet.io) 로그인 → 제품 등록
2. `docs/blog/community_post_draft.md` 디스콰이엇 섹션 참조

---

## 5. GitHub Release 생성

**상태**: CI 설정 완료 — **태그 푸시 필요**

```bash
git tag v0.1.0
git push origin v0.1.0
```

태그를 푸시하면 `.github/workflows/release.yml` 이 자동 실행되어:
- 전체 테스트 통과 확인
- GitHub Release 자동 생성 (`dist/*.whl`, `dist/*.tar.gz` 첨부)
- PyPI 업로드 (PYPI_TOKEN 등록 후)

---

## 요약

| 항목 | 코드 준비 | 수동 작업 |
|---|---|---|
| PyPI 배포 | ✅ release.yml 완료 | PYPI_TOKEN 등록 + 태그 푸시 |
| GitHub Release | ✅ release.yml 완료 | 태그 푸시 (`v0.1.0`) |
| Tistory | ✅ 초안 완료 | 로그인 후 게시 |
| GeekNews | ✅ 초안 완료 | 로그인 후 제출 |
| 디스콰이엇 | ✅ 초안 완료 | 로그인 후 등록 |
