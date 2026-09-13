from pathlib import Path
import sys
import tempfile

from .core import audit, git
from .report import write

OLD = '''def discount(total):
    return total * 0.10 if total > 100 else 0


def shipping(total):
    return 0 if total > 50 else 5
'''
NEW = OLD.replace('> 100', '>= 100').replace('> 50', '>= 50')
TEST = '''import unittest
from shop import discount, shipping

class ShopTests(unittest.TestCase):
    def test_discount_boundary(self):
        self.assertEqual(discount(100), 10)

    def test_shipping_ordinary_order(self):
        self.assertEqual(shipping(20), 5)
'''


def commit(folder, message):
    git(folder, "add", ".")
    git(folder, "-c", "user.name=Greenblind Demo", "-c", "user.email=demo@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", message)


def demo(output):
    with tempfile.TemporaryDirectory(prefix="greenblind-demo-") as tmp:
        folder = Path(tmp)
        git(folder, "init", "-q")
        (folder / "shop.py").write_text(OLD, encoding="utf-8")
        commit(folder, "Before boundary fixes")
        (folder / "shop.py").write_text(NEW, encoding="utf-8")
        (folder / "test_shop.py").write_text(TEST, encoding="utf-8")
        commit(folder, "Fix both boundaries; test only one boundary")
        report = audit(folder, "HEAD~1", "HEAD", ["shop.py"], [],
                       [sys.executable, "-m", "unittest", "discover", "-v"],
                       progress=lambda s: print(s, file=sys.stderr, flush=True))
        write(report, output)
        return report
