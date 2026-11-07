"""The registry must be self-consistent, because everything downstream cites from it."""

from __future__ import annotations

import pytest

from itulib import sources


def test_exactly_one_in_force_edition_per_recommendation() -> None:
    seen: dict[str, int] = {}
    for edition in sources.IN_FORCE:
        seen[edition.key.split("#")[0]] = seen.get(edition.key.split("#")[0], 0) + 1
    assert all(count == 1 for count in seen.values()), seen


def test_keys_are_unique_across_all_editions() -> None:
    keys = [edition.key for edition in (*sources.IN_FORCE, *sources.SUPERSEDED)]
    assert len(keys) == len(set(keys))


def test_registered_urls_are_https_and_carry_the_artifact_id() -> None:
    for edition in (*sources.IN_FORCE, *sources.SUPERSEDED):
        assert edition.pdf_url.startswith("https://www.itu.int/")
        assert edition.artifact in edition.pdf_url


def test_pinned_digests_are_shaped_like_digests_or_marked_absent() -> None:
    for edition in (*sources.IN_FORCE, *sources.SUPERSEDED):
        if edition.sha256:
            assert len(edition.sha256) == 64, edition.key
            assert all(char in "0123456789abcdef" for char in edition.sha256)
        else:
            assert "not captured" in edition.note or "Digest" in edition.note, (
                f"{edition.key}: an unpinned edition has to say so"
            )


def test_in_force_editions_are_pinned_and_sized() -> None:
    """A claim of "in force" without a measured digest is just a guess with a URL."""
    for edition in sources.IN_FORCE:
        assert edition.sha256, edition.key
        assert edition.octets > 100_000, edition.key


def test_resolve_refuses_to_guess() -> None:
    assert sources.resolve("X.690").edition == "02/2021"
    assert sources.resolve("X.690#2008-11").status == "superseded"
    with pytest.raises(KeyError):
        sources.resolve("X.999")
    with pytest.raises(KeyError):
        sources.current("X.509")


def test_errata_are_registered_and_the_unfetchable_ones_say_so() -> None:
    errata = [item for item in sources.AMENDMENTS if "Erratum" in item.label]
    assert errata, "ITU publishes errata; an empty registry would misreport that"
    for item in sources.AMENDMENTS:
        if item.artifact is None:
            assert item.note, f"{item.key}: no download id and no note saying why"


def test_every_amendment_with_a_download_id_is_pinned() -> None:
    """The erratum id was read off ITU's own page after two guessed ids returned HTTP 500; keep it pinned."""
    fetchable = [item for item in sources.AMENDMENTS if item.artifact]
    assert any(item.key == "X.690#2021-02!erratum-1" for item in fetchable)
    for item in fetchable:
        assert item.pdf_url is not None and item.pdf_url.startswith("https://www.itu.int/")
        assert len(item.sha256) == 64 and item.octets > 0, item.key
        assert "!!ERSN1" not in (item.artifact or "") and "!!DOC" not in (item.artifact or "")


def test_resolve_document_finds_an_erratum_and_still_refuses_to_guess() -> None:
    assert sources.resolve_document("X.690#2021-02!erratum-1").key == "X.690#2021-02!erratum-1"
    assert sources.resolve_document("X.690").key == "X.690#2021-02"
    with pytest.raises(KeyError):
        sources.resolve_document("X.690!nonsense")
