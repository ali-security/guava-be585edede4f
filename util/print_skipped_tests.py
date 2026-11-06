#!/usr/bin/env python3
"""Print every skipped test with its reason, plus per-module pass/fail totals.

Surefire 2.7.2 records JUnit assumption skips as a bare <skipped/> with no
message, so the reason is recovered from the assume()/assumeTrue() lines in the
test method's source. Run from the repository root after `mvn verify`.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET


def module_reports():
    for d in sorted(set(glob.glob("*/target/surefire-reports") + glob.glob("android/*/target/surefire-reports"))):
        files = sorted(glob.glob(os.path.join(d, "TEST-*.xml")))
        if files:
            yield d.split("/target/")[0], files


_index = {}


def method_index(module):
    """Map method name -> list of assumption lines found in its body (first lines)."""
    if module in _index:
        return _index[module]
    idx = {}
    for path in glob.glob(os.path.join(module, "test", "**", "*.java"), recursive=True) + glob.glob(
        os.path.join(module, "src", "test", "**", "*.java"), recursive=True
    ):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            m = re.search(r"\bvoid\s+(\w+)\s*\(", line)
            if not m:
                continue
            body = []
            for nxt in lines[i + 1 : i + 12]:
                if re.search(r"\bvoid\s+\w+\s*\(", nxt):
                    break
                if "assume" in nxt.lower():
                    body.append(nxt.strip())
            if body:
                idx.setdefault(m.group(1), []).extend(body)
    _index[module] = idx
    return idx


def main():
    grand = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    summaries = []
    for module, files in module_reports():
        tot = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        skipped = []
        for path in files:
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError as e:
                print("WARN could not parse %s: %s" % (path, e))
                continue
            for k in tot:
                tot[k] += int(float(root.get(k, "0") or 0))
            for tc in root.iter("testcase"):
                sk = tc.find("skipped")
                if sk is None:
                    continue
                cls = tc.get("classname", "?")
                name = tc.get("name", "?")
                reason = (sk.get("message") or (sk.text or "")).strip()
                if not reason:
                    base = re.sub(r"\[.*$", "", name).split("(")[0]
                    hits = method_index(module).get(base)
                    if hits:
                        reason = "JUnit assumption not met: " + " ".join(sorted(set(hits)))[:300]
                    else:
                        reason = "JUnit assumption not met (surefire 2.7.2 records no message)"
                skipped.append((cls, name, reason))
        if skipped:
            print("=== Skipped tests in %s (%d) ===" % (module, len(skipped)))
            for cls, name, reason in skipped:
                print("SKIPPED %s#%s -- %s" % (cls, name, reason))
        passed = tot["tests"] - tot["failures"] - tot["errors"] - tot["skipped"]
        summaries.append(
            "SUMMARY %s: Tests run: %d, Passed: %d, Failures: %d, Errors: %d, Skipped: %d"
            % (module, tot["tests"], passed, tot["failures"], tot["errors"], tot["skipped"])
        )
        for k in grand:
            grand[k] += tot[k]
    for s in summaries:
        print(s)
    passed = grand["tests"] - grand["failures"] - grand["errors"] - grand["skipped"]
    print(
        "SUMMARY TOTAL: Tests run: %d, Passed: %d, Failures: %d, Errors: %d, Skipped: %d"
        % (grand["tests"], passed, grand["failures"], grand["errors"], grand["skipped"])
    )
    print("SEAL_TEST_REPORT_" + "COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
