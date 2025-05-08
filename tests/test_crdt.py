from __future__ import annotations

from hypothesis import given, strategies as st

from rt_collab.services.crdt import TextCRDT


@given(st.lists(st.text(min_size=1, max_size=3), min_size=1, max_size=5))
def test_commutativity_of_apply(chunks):
    """Applying the same operations in different orders produces the same text."""
    producer = TextCRDT(site_id="src")
    ops = [producer.local_insert(0, s) for s in chunks]

    c1 = TextCRDT(site_id="A")
    for op in ops:
        c1.apply(op)

    c2 = TextCRDT(site_id="B")
    for op in reversed(ops):
        c2.apply(op)

    assert c1.to_string() == c2.to_string()
