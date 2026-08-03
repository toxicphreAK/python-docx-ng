"""Text search and replace across the runs of a paragraph.

The public entry points are :meth:`.Paragraph.replace_text`,
:meth:`.BlockItemContainer.replace_text` and :meth:`.Document.replace_text`; this module
holds the machinery they share.

Matching is done against the paragraph's text as a whole, so a match is found whether or
not Word happened to split it across runs. Replacement is performed by
:func:`docx.oxml.text.isolate.replace_range`, which preserves the formatting of the
surrounding text.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Pattern

from docx.oxml.text.isolate import replace_range

if TYPE_CHECKING:
    from docx.oxml.text.paragraph import CT_P

# -- a replacement pass that finds this many matches in one paragraph is looping on its
# -- own output rather than converging; better to say so than to hang --
_MAX_REPLACEMENTS_PER_PARAGRAPH = 100_000


def compile_pattern(old: str, regex: bool, flags: int | re.RegexFlag = 0) -> Pattern[str]:
    """Return the compiled pattern matching `old`.

    A literal `old` is escaped, so text containing regex metacharacters — a "$" in a
    price, the "." in a file name — matches itself rather than being interpreted.
    """
    return re.compile(old if regex else re.escape(old), flags)


def replace_in_paragraph(
    p: CT_P, pattern: Pattern[str], new: str, count: int = -1, regex: bool = False
) -> int:
    """Replace up to `count` matches of `pattern` in `p` with `new`, returning how many.

    `count` of -1 replaces every match. When `regex` is True, `new` may refer to capture
    groups as ``\\1`` or ``\\g<name>``; otherwise it is used literally.

    Each replacement changes the paragraph's text, so the next match is searched for
    against the updated text, starting past the text just written. That means a
    replacement containing the pattern is not re-matched, and ``replace_text("a", "aa")``
    terminates.
    """
    if count == 0:
        return 0

    replaced = 0
    pos = 0
    while count < 0 or replaced < count:
        text = p.text
        if pos > len(text):
            break
        match = pattern.search(text, pos)
        if match is None:
            break

        replacement = match.expand(new) if regex else new
        replace_range(p, match.start(), match.end(), replacement)
        replaced += 1

        pos = match.start() + len(replacement)
        if match.start() == match.end():
            # -- a zero-width match consumes nothing; step past it or search forever --
            pos += 1

        if replaced >= _MAX_REPLACEMENTS_PER_PARAGRAPH:
            raise RuntimeError(
                f"replacement did not converge after {replaced} matches in one"
                " paragraph; check that the replacement text does not re-match the"
                " pattern"
            )

    return replaced
