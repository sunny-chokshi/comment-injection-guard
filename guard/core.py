"""Scan a snippet, flag steering comments, and build the guarded copy."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import comments as cm
from . import rules


@dataclass
class Flag:
    start_line: int
    end_line: int
    kind: str
    text: str
    score: float
    rules: list[str]


@dataclass
class ScanResult:
    language: str
    n_comments: int
    flags: list[Flag] = field(default_factory=list)
    guarded_code: str = ""

    @property
    def flagged(self) -> bool:
        return bool(self.flags)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flagged"] = self.flagged
        return d


class Guard:
    """detector: "classifier", "regex" or "either" (flag if either fires).

    mode: "strip_flagged" removes only flagged blocks; "strip_all" removes every
    comment block (the comment-stripped defense from the CommentInject work).
    """

    def __init__(self, detector: str = "either", mode: str = "strip_flagged", clf=None):
        self.detector, self.mode = detector, mode
        self.clf = clf
        if detector in ("classifier", "either") and clf is None:
            from .classifier import Detector
            self.clf = Detector()

    def score_texts(self, texts: list[str]) -> list[tuple[float, list[str], bool]]:
        clf_scores = self.clf.scores(texts) if self.detector != "regex" else [0.0] * len(texts)
        out = []
        for t, s in zip(texts, clf_scores):
            hits = rules.match(t)
            if self.detector == "regex":
                out.append((1.0 if hits else 0.0, hits, bool(hits)))
            elif self.detector == "classifier":
                out.append((s, hits, s >= self.clf.threshold))
            else:
                out.append((max(s, 1.0 if hits else 0.0), hits, bool(hits) or s >= self.clf.threshold))
        return out

    def scan(self, code: str, language: str | None = None) -> ScanResult:
        lang = (language or cm.detect_language(code)).lower()
        blocks = cm.extract(code, lang)
        scored = self.score_texts([b.text for b in blocks])
        flagged = [(b, s) for b, s in zip(blocks, scored) if s[2]]
        res = ScanResult(language=lang, n_comments=len(blocks))
        res.flags = [Flag(b.start_line, b.end_line, b.kind, b.text[:500], round(s[0], 4), s[1]) for b, s in flagged]
        to_remove = blocks if self.mode == "strip_all" else [b for b, _ in flagged]
        res.guarded_code = cm.remove(code, to_remove) if to_remove else code
        return res
