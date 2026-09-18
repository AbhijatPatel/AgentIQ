
from app.utils.deduplication import (
    deduplicate_by_key,
    deduplicate_web_results,
    deduplicate_image_results,
    deduplicate_video_results,
)


def test_deduplicate_by_key_removes_duplicates():
    items = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
        {"url": "https://example.com/a"},
    ]

    result = deduplicate_by_key(
        items,
        lambda item: item.get("url"),
    )

    assert len(result) == 2
    assert result[0]["url"] == "https://example.com/a"
    assert result[1]["url"] == "https://example.com/b"


def test_deduplicate_by_key_is_case_insensitive():
    items = [
        {"url": "https://Example.com/article"},
        {"url": "https://example.com/article"},
    ]

    result = deduplicate_by_key(
        items,
        lambda item: item.get("url"),
    )

    assert len(result) == 1


def test_deduplicate_preserves_order():
    items = [
        {"url": "https://example.com/1"},
        {"url": "https://example.com/2"},
        {"url": "https://example.com/3"},
        {"url": "https://example.com/2"},
    ]

    result = deduplicate_by_key(
        items,
        lambda item: item.get("url"),
    )

    assert [item["url"] for item in result] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]


def test_missing_key_items_are_preserved():
    items = [
        {"title": "First"},
        {"title": "Second"},
    ]

    result = deduplicate_by_key(
        items,
        lambda item: item.get("url"),
    )

    assert len(result) == 2


def test_web_results_are_deduplicated():
    results = [
        {"url": "https://example.com/a", "title": "A"},
        {"url": "https://example.com/a", "title": "A duplicate"},
        {"url": "https://example.com/b", "title": "B"},
    ]

    result = deduplicate_web_results(results)

    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "B"


def test_image_results_are_deduplicated():
    results = [
        {"url": "https://images.com/a.jpg"},
        {"url": "https://images.com/a.jpg"},
        {"url": "https://images.com/b.jpg"},
    ]

    result = deduplicate_image_results(results)

    assert len(result) == 2


def test_video_results_are_deduplicated():
    results = [
        {"url": "https://videos.com/a"},
        {"url": "https://videos.com/a"},
        {"url": "https://videos.com/b"},
    ]

    result = deduplicate_video_results(results)

    assert len(result) == 2


def test_empty_results():
    assert deduplicate_web_results([]) == []
    assert deduplicate_image_results([]) == []
    assert deduplicate_video_results([]) == []
