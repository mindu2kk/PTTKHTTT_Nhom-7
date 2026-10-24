"""Run worker unit tests with stdlib unittest and emit JUnit without installing pytest."""

import argparse
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class JUnitResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []
        self.started = 0.0

    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        node = ET.Element(
            "testcase",
            classname=test.__class__.__module__ + "." + test.__class__.__name__,
            name=test._testMethodName,
            time=f"{time.perf_counter() - self.started:.6f}",
        )
        for tag, outcomes in (("failure", self.failures), ("error", self.errors)):
            for failed, detail in outcomes:
                if failed is test:
                    ET.SubElement(node, tag).text = detail
        for skipped, reason in self.skipped:
            if skipped is test:
                ET.SubElement(node, "skipped", message=reason)
        self.cases.append(node)
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inference_directory", type=Path)
    parser.add_argument("tests_directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.inference_directory.resolve()))
    suite = unittest.defaultTestLoader.discover(str(args.tests_directory.resolve()))
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=JUnitResult).run(suite)
    xml = ET.Element(
        "testsuite",
        name="inference-unit",
        tests=str(result.testsRun),
        failures=str(len(result.failures)),
        errors=str(len(result.errors)),
        skipped=str(len(result.skipped)),
        time=f"{time.perf_counter() - started:.6f}",
    )
    xml.extend(result.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(xml).write(args.output, encoding="utf-8", xml_declaration=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
