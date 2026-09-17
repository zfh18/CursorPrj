import importlib.util
import sys
import tempfile
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parent


def load_cdd_generator(project: str):
    path = ROOT / project / f"cddGen_{project}.py"
    spec = importlib.util.spec_from_file_location(f"cddGen_{project}_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_normalizer(project: str) -> None:
    module = load_cdd_generator(project)
    root = etree.fromstring(
        b"<CANDELA><DID id='did1'><NAME><TUV>Chinese name</TUV></NAME><QUAL>z</QUAL></DID>"
        b"<DIAGINST><NAME><TUV>Chinese name</TUV></NAME><QUAL>English_name</QUAL>"
        b"<DIDDATAREF didRef='did1'><NAME><TUV>Chinese name</TUV></NAME><QUAL>z</QUAL>"
        b"</DIDDATAREF></DIAGINST></CANDELA>"
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.cdd"
        etree.ElementTree(root).write(str(path), encoding="utf-8", xml_declaration=True)
        module.normalize_internal_did_qualifiers(path)
        result = etree.parse(str(path))
    assert result.findtext("DID/QUAL") == "English_name"
    assert result.findtext("DIAGINST/DIDDATAREF/QUAL") == "English_name"
    assert result.findtext("DID/NAME/TUV") == "Chinese name"
    assert result.findtext("DIAGINST/NAME/TUV") == "Chinese name"


if __name__ == "__main__":
    for name in ("JAC", "SERES"):
        check_normalizer(name)
    print("JAC/SERES internal DID naming checks passed")
