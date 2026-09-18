from app.utils.cache import ResearchCache


def test_cache_set_and_get():
    cache = ResearchCache()

    cache.set("Generative AI", {"result": "test"})

    assert cache.get("Generative AI") == {"result": "test"}


def test_cache_normalizes_task():
    cache = ResearchCache()

    cache.set("Generative AI", {"result": "test"})

    assert cache.get("  generative   ai  ") == {"result": "test"}


def test_cache_miss():
    cache = ResearchCache()

    assert cache.get("Unknown research task") is None


def test_cache_clear():
    cache = ResearchCache()

    cache.set("Task one", {"result": 1})
    cache.set("Task two", {"result": 2})

    assert cache.size() == 2

    cache.clear()

    assert cache.size() == 0
    assert cache.get("Task one") is None


def test_cache_expiration():
    cache = ResearchCache(ttl_seconds=0)

    cache.set("Temporary task", {"result": "expired"})

    assert cache.get("Temporary task") is None