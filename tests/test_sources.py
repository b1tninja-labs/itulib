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


def test_errata_surface_is_honest_about_what_was_not_found() -> None:
    """The X.690 erratum is real and listed In force; the download id was not discovered, and that is said."""
    errata = [item for item in sources.AMENDMENTS if "Erratum" in item.label]
    assert errata, "ITU publishes errata; an empty registry would misreport that"
    for item in errata:
        assert item.artifact is None
        assert "500" in item.note or "discover" in item.note.lower()
