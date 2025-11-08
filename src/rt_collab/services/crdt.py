from __future__ import annotations

import itertools
import string
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple


# A compact sequence CRDT using Logoot/LSEQ-like positional identifiers.
# Each atom has a position (list[int]) and a tiebreaker (site_id, counter) to ensure total order.


BASE = 2**16


def between_pos(left: List[int] | None, right: List[int] | None, base: int = BASE) -> List[int]:
    """Generate a position strictly between left and right (lexicographic order).
    left/right are position lists; None represents -inf/+inf.
    """
    l = left or []
    r = right or []
    depth = 0
    while True:
        l_digit = l[depth] if depth < len(l) else 0
        r_digit = r[depth] if depth < len(r) else base
        if r_digit - l_digit > 1:
            return [*(l[:depth]), (l_digit + r_digit) // 2]
        depth += 1


@dataclass(order=True)
class Atom:
    # Order by pos first, then site and counter for deterministic tie-breaking
    pos: List[int] = field(compare=True)
    site_id: str = field(compare=True)
    counter: int = field(compare=True)
    char: str = field(compare=False, default="")
    deleted: bool = field(compare=False, default=False)

    @property
    def id(self) -> Tuple[Tuple[int, ...], str, int]:
        return (tuple(self.pos), self.site_id, self.counter)


class TextCRDT:
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self._counter = 0
        self._atoms: List[Atom] = []  # always maintained sorted

    # Utilities
    def _next_counter(self) -> int:
        self._counter += 1
        return self._counter

    def _sort(self) -> None:
        self._atoms.sort()

    def to_string(self) -> str:
        return "".join(a.char for a in self._atoms if not a.deleted)

    def atoms(self) -> List[Atom]:
        return list(self._atoms)

    # Position helpers
    def _pos_of_index(self, index: int) -> List[int] | None:
        # position of atom currently at index (visible only)
        visible = [a for a in self._atoms if not a.deleted]
        if not visible:
            return None
        if index < 0:
            return None
        if index >= len(visible):
            return None
        return visible[index].pos

    def _neighbor_positions(self, index: int) -> tuple[List[int] | None, List[int] | None]:
        visible = [a for a in self._atoms if not a.deleted]
        left = visible[index - 1].pos if index - 1 >= 0 else None
        right = visible[index].pos if index < len(visible) else None
        if index == len(visible):
            right = None
        return left, right

    # Local ops (generate CRDT ops)
    def local_insert(self, index: int, text: str) -> dict:
        ops: List[dict] = []
        for ch in text:
            left, right = self._neighbor_positions(index)
            pos = between_pos(left, right)
            atom = Atom(pos=pos, site_id=self.site_id, counter=self._next_counter(), char=ch)
            self._atoms.append(atom)
            self._sort()
            index += 1
            ops.append({
                "type": "ins",
                "pos": atom.pos,
                "site": atom.site_id,
                "ctr": atom.counter,
                "ch": atom.char,
            })
        return {"type": "ins_batch", "atoms": ops}

    def local_delete(self, index: int, length: int) -> dict:
        visible = [a for a in self._atoms if not a.deleted]
        to_delete = visible[index : index + length]
        for a in to_delete:
            a.deleted = True
        return {
            "type": "del_batch",
            "targets": [
                {"pos": a.pos, "site": a.site_id, "ctr": a.counter} for a in to_delete
            ],
        }

    # Remote op application (idempotent)
    def apply(self, op: dict) -> None:
        t = op.get("type")
        if t == "ins_batch":
            for atom in op.get("atoms", []):
                self._apply_ins(atom)
            self._sort()
        elif t == "del_batch":
            for tgt in op.get("targets", []):
                self._apply_del(tgt)
        elif t == "ins":
            self._apply_ins(op)
            self._sort()
        elif t == "del":
            self._apply_del(op)

    def _apply_ins(self, atom: dict) -> None:
        pos = list(atom["pos"])  # ensure list
        site = str(atom["site"]) 
        ctr = int(atom["ctr"]) 
        ch = str(atom["ch"]) 
        # idempotency: if same id exists, ignore
        if any(a.pos == pos and a.site_id == site and a.counter == ctr for a in self._atoms):
            return
        self._atoms.append(Atom(pos=pos, site_id=site, counter=ctr, char=ch))

    def _apply_del(self, tgt: dict) -> None:
        pos = list(tgt["pos"]) 
        site = str(tgt["site"]) 
        ctr = int(tgt["ctr"]) 
        for a in self._atoms:
            if a.pos == pos and a.site_id == site and a.counter == ctr:
                a.deleted = True
                break

