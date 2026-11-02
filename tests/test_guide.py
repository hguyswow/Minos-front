# Acceptance tests.
import re
from editor.app import guide

HANGUL = re.compile("[가-힣]")
TITLES = ["처음 시작하기", "게임 추가하기", "제목 고치기", "적용 버튼과 기종 표시",
          "기기에 반영하기", "훅 상태 보는 법", "안전과 되돌리기", "화면·소리 설정", "백업과 복구", "꾸미기(배경·영상·음악)", "게임별 화면 비율", "화질과 기종별 설정", "아직 없는 기능"]
BANNED = ["patch", "NUL", "offset", "hook", "바이너리", "Traceback", "exception", "UTF-"]


def test_sections_order_and_titles():
    s = guide.get_sections()
    assert [x.title for x in s] == TITLES


def test_bodies_are_korean_and_jargon_free():
    for x in guide.get_sections():
        assert len(x.body.strip()) >= 40, x.title
        assert HANGUL.search(x.body)
        for b in BANNED:
            assert b.lower() not in x.body.lower(), (x.title, b)


def test_key_terms_present():
    body = {x.title: x.body for x in guide.get_sections()}
    assert "찾아보기" in body["처음 시작하기"] and "C:" in body["처음 시작하기"]
    assert "덮어" in body["게임 추가하기"]
    assert "28" in body["제목 고치기"]
    assert "적용" in body["적용 버튼과 기종 표시"] and "꼭" in body["적용 버튼과 기종 표시"]
    assert "안전" in body["기기에 반영하기"]
    assert "정상" in body["훅 상태 보는 법"] and "주의" in body["훅 상태 보는 법"]
    assert ".bak" in body["안전과 되돌리기"] and "240" in body["안전과 되돌리기"]
    assert "모음" in body["아직 없는 기능"] and "배경" not in body["아직 없는 기능"]  # backgrounds now exist
    ratio = body["게임별 화면 비율"]
    assert "단축키" in ratio and "하나" in ratio and "기본" in ratio and "시험" in ratio and "확인됨" in ratio
    q = body["화질과 기종별 설정"]
    assert all(k in q for k in ("부드럽게", "선명", "우선", "여러", "기종", "줄무늬"))
    deco = body["꾸미기(배경·영상·음악)"]
    assert "원래대로" in deco and "한 가지" in deco and "ffmpeg" not in deco.lower()
    assert "비율" not in body["아직 없는 기능"]  # screen settings now exist
    assert "저장" in body["화면·소리 설정"] and ".bak" in body["화면·소리 설정"]
    assert "미리보기" in body["백업과 복구"] and "전체 이미지" in body["백업과 복구"] and "자동" in body["백업과 복구"]
    assert "카드 전체 이미지 백업" in body["아직 없는 기능"]


def test_gui_has_guide_handler_and_no_import_side_effects():
    import tkinter
    import editor.app.gui as gui
    assert hasattr(gui.PandoraEditorApp, "_on_show_guide")
    assert getattr(tkinter, "_default_root", None) is None
