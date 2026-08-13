"""Pine Script v6 linter for AI agent pre-flight validation.

Reads a .pine file line-by-line, strips inline comments, and emits
categorized Errors (fail the build) and Warnings (best-practice hints).
Exit code 0 = pass (warnings OK), 1 = fail (at least one error).

Usage:
    python3 pine_linter.py <path_to_script.pine>
"""

import sys
import re
import os
from typing import List


class PineLinter:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._declarations_found: int = 0

    def _add_error(self, line_num: int, message: str) -> None:
        self.errors.append(f"Line {line_num}: [ERROR] {message}")

    def _add_warning(self, line_num: int, message: str) -> None:
        self.warnings.append(f"Line {line_num}: [WARNING] {message}")

    def lint(self) -> bool:
        """Run all checks; return True if no errors (warnings are OK)."""
        if not os.path.exists(self.filepath):
            print(f"❌ Error: File '{self.filepath}' not found.", file=sys.stderr)
            return False

        with open(self.filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        has_version = False

        for i, raw_line in enumerate(lines):
            line_num = i + 1
            stripped_raw = raw_line.strip()

            # 1. Version declaration — check on raw line BEFORE comment stripping
            # (lines starting with // would otherwise be stripped to "" and skipped)
            if stripped_raw.startswith("//@version="):
                has_version = True
                if "6" not in stripped_raw:
                    self._add_error(line_num, "Script must use //@version=6")
                continue

            code = raw_line.split("//")[0].strip()

            if not code:
                continue

            # 2. Script-type declaration
            if re.match(r"^(indicator|strategy|library)\(", code):
                self._declarations_found += 1

            # 3. request.security() without explicit lookahead
            if "request.security(" in code and "lookahead" not in code:
                self._add_error(
                    line_num,
                    "Unsafe request.security() — must explicitly set"
                    " lookahead=barmerge.lookahead_on or lookahead_off.",
                )

            # 4. Strict booleans: boolean expressions inside na() / nz()
            if re.search(r"\b(?:na|nz)\(.*?(?:==|!=|>|<|\band\b|\bor\b).*?\)", code):
                self._add_error(
                    line_num,
                    "Cannot pass boolean expressions to na() or nz() in v6.",
                )

            # 5. Drawing objects recreated every tick (should use var/varip)
            if re.search(r"\b(label|line|box|table)\.new\(", code):
                leading = raw_line.lstrip()
                if not (leading.startswith("var ") or leading.startswith("varip ")):
                    self._add_warning(
                        line_num,
                        "Drawing object created without 'var' or 'varip' — "
                        "recreated on every tick; use 'var' unless intentional.",
                    )

            # 6. Bare variable initialisation without var (heuristic)
            if (
                "=" in code
                and ":=" not in code
                and "==" not in code
                and not leading_keyword(code)
            ):
                if re.match(r"^[a-zA-Z_]\w*\s*=", code):
                    self._add_warning(
                        line_num,
                        "Variable initialized without 'var'. "
                        "Ensure per-bar recreation is intentional; use ':=' for reassignment.",
                    )

        # Document-level checks
        if not has_version:
            self._add_error(1, "Missing version declaration — file must start with //@version=6")

        if self._declarations_found == 0:
            self._add_error(
                1,
                "Missing script declaration — must contain indicator(), strategy(), or library().",
            )
        elif self._declarations_found > 1:
            self._add_error(
                1,
                f"Found {self._declarations_found} declarations — only one allowed per script.",
            )

        return self._report()

    def _report(self) -> bool:
        print(f"\n--- Linting Report: {self.filepath} ---", file=sys.stderr)

        for w in self.warnings:
            print(f"⚠️  {w}", file=sys.stderr)

        for e in self.errors:
            print(f"❌ {e}", file=sys.stderr)

        if self.errors:
            print(f"\n🚨 Failed: {len(self.errors)} error(s), {len(self.warnings)} warning(s)\n", file=sys.stderr)
            return False

        if self.warnings:
            print(f"\n✅ Passed (with {len(self.warnings)} warning(s))\n", file=sys.stderr)
            return True

        print("\n✅ Passed: Perfect Script!\n", file=sys.stderr)
        return True


def leading_keyword(code: str) -> bool:
    """True if the line starts with a Pine / Python control-flow keyword."""
    keywords = ("var ", "varip ", "if ", "else", "for ", "while ", "switch", "return ")
    return any(code.startswith(k) for k in keywords)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pine_linter.py <path_to_script.pine>")
        sys.exit(1)

    linter = PineLinter(sys.argv[1])
    success = linter.lint()
    sys.exit(0 if success else 1)
