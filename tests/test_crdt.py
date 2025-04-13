from __future__ import annotations

from hypothesis import given, strategies as st

from rt_collab.services.crdt import TextCRDT


@given(st.lists(st.text(min_size=1, max_size=3), min_size=1, max_size=5))
def test_commutativity_of_inserts(chunks):
    # Insert the same set of chunks at position 0 in different orders
    # Generate ops for two different orders
    a = TextCRDT(site_id="A")
    ops1 = [a.local_insert(0, s) for s in chunks]

    b = TextCRDT(site_id="B")
    ops2 = [b.local_insert(0, s) for s in reversed(chunks)]

    # Apply the ops separately and compare final text
    a2 = TextCRDT(site_id="X")
    for op in ops1:
        a2.apply(op)

    b2 = TextCRDT(site_id="Y")
    for op in ops2:
        b2.apply(op)

    assert a2.to_string() == b2.to_string()
