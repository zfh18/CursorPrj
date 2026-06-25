#!/usr/bin/env python3
"""Generate a VF CDD by first generating PDX, then importing it with CANdelaStudio."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from lxml import etree


DEFAULT_PDX_GENERATOR = Path("pdxGen_VF.py")
DEFAULT_PDX_TEMPLATE = Path("templates") / "VF_ECU_CAN_v15.pdx"
DEFAULT_CDD_TEMPLATE = Path("templates") / "VF_ECU_CAN_v15.cdd"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


@dataclass(frozen=True)
class CandelaInstall:
    exe: Path
    version_text: str
    version_key: str
    source: str

    @property
    def major(self) -> int | None:
        for value in (self.version_key, self.version_text):
            match = re.match(r"\s*(\d+)(?:[._ ]\d+)?", value)
            if match:
                return int(match.group(1))
        path_version = infer_candela_version_from_path(self.exe)
        match = re.match(r"(\d+)", path_version)
        return int(match.group(1)) if match else None


def find_default_xlsx(base_dir: Path) -> Path:
    candidates = sorted(path for path in base_dir.glob("*.xlsx") if not path.name.startswith("~$"))
    if not candidates:
        raise FileNotFoundError("No .xlsx survey file found in the current directory")
    return candidates[0]


def read_cdd_dtd_version(cdd_path: Path) -> str | None:
    header = cdd_path.read_bytes()[:65536]
    match = re.search(rb"<CANDELA\b[^>]*\bdtdvers=['\"]([^'\"]+)", header)
    if not match:
        return None
    return match.group(1).decode("ascii", errors="ignore")


def read_cdd_dtd_major(cdd_path: Path) -> int | None:
    version = read_cdd_dtd_version(cdd_path)
    if not version:
        return None
    match = re.match(r"(\d+)", version)
    return int(match.group(1)) if match else None


def version_numbers(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or ""))


def candela_sort_key(install: CandelaInstall) -> tuple[int, ...]:
    return version_numbers(install.version_key) or version_numbers(install.version_text) or version_numbers(str(install.exe))


def infer_candela_version_from_path(exe: Path) -> str:
    match = re.search(r"Vector CANdelaStudio\s*([0-9.]+)", str(exe), flags=re.IGNORECASE)
    return match.group(1) if match else ""


def registry_candela_installs() -> list[CandelaInstall]:
    if os.name != "nt":
        return []

    import winreg

    installs: list[CandelaInstall] = []
    registry_views = [
        (r"SOFTWARE\Vector\CANdelaStudio", getattr(winreg, "KEY_WOW64_64KEY", 0)),
        (r"SOFTWARE\Vector\CANdelaStudio", getattr(winreg, "KEY_WOW64_32KEY", 0)),
        (r"SOFTWARE\WOW6432Node\Vector\CANdelaStudio", 0),
    ]
    seen: set[tuple[str, str]] = set()

    for subkey, access_flag in registry_views:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, winreg.KEY_READ | access_flag) as key:
                subkey_count, _, _ = winreg.QueryInfoKey(key)
                for index in range(subkey_count):
                    version_key = winreg.EnumKey(key, index)
                    if (subkey, version_key) in seen:
                        continue
                    seen.add((subkey, version_key))
                    try:
                        with winreg.OpenKey(key, version_key) as version_item:
                            install_path, _ = winreg.QueryValueEx(version_item, "Path")
                            try:
                                version_text, _ = winreg.QueryValueEx(version_item, "Version")
                            except FileNotFoundError:
                                version_text = version_key
                    except OSError:
                        continue

                    exe = Path(str(install_path)) / "Bin" / "CANdelaStudio.exe"
                    if exe.exists():
                        installs.append(
                            CandelaInstall(
                                exe=exe,
                                version_text=str(version_text),
                                version_key=version_key,
                                source=f"registry:{subkey}\\{version_key}",
                            )
                        )
        except (FileNotFoundError, OSError):
            continue

    return installs


def filesystem_candela_installs() -> list[CandelaInstall]:
    installs: list[CandelaInstall] = []
    base_dirs = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        r"C:\Program Files",
        r"C:\Program Files (x86)",
    ]
    for base_text in base_dirs:
        if not base_text:
            continue
        base = Path(base_text)
        if not base.exists():
            continue
        for exe in base.glob(r"Vector CANdelaStudio *\Bin\CANdelaStudio.exe"):
            version_key = infer_candela_version_from_path(exe)
            installs.append(
                CandelaInstall(
                    exe=exe,
                    version_text=version_key,
                    version_key=version_key,
                    source="filesystem",
                )
            )
    return installs


def discover_candela_installs() -> list[CandelaInstall]:
    installs: dict[Path, CandelaInstall] = {}
    for install in registry_candela_installs() + filesystem_candela_installs():
        installs.setdefault(install.exe.resolve(), install)
    return list(installs.values())


def select_candela_install(explicit_exe: Path | None, preferred_major: int | None, allow_newer: bool) -> CandelaInstall:
    if explicit_exe is not None:
        exe = explicit_exe.resolve()
        if not exe.exists():
            raise FileNotFoundError(f"Specified CANdelaStudio.exe does not exist: {exe}")
        version_key = infer_candela_version_from_path(exe)
        return CandelaInstall(exe=exe, version_text=version_key, version_key=version_key, source="--candela-exe")

    env_exe = os.environ.get("CANDELA_STUDIO_EXE")
    if env_exe:
        exe = Path(env_exe).resolve()
        if not exe.exists():
            raise FileNotFoundError(f"CANDELA_STUDIO_EXE points to a missing file: {exe}")
        version_key = infer_candela_version_from_path(exe)
        return CandelaInstall(exe=exe, version_text=version_key, version_key=version_key, source="CANDELA_STUDIO_EXE")

    installs = discover_candela_installs()
    if not installs:
        raise RuntimeError("No CANdelaStudio installation found. Use --candela-exe to specify CANdelaStudio.exe.")

    if preferred_major is not None:
        exact = [install for install in installs if install.major == preferred_major]
        if exact:
            return sorted(exact, key=candela_sort_key, reverse=True)[0]
        if not allow_newer:
            found = ", ".join(sorted({install.version_key or str(install.exe) for install in installs}, key=version_numbers))
            raise RuntimeError(
                f"CANdelaStudio {preferred_major}.x was not found. Found: {found}. "
                "Use --candela-exe to specify an executable, or --allow-newer-candela to allow a newer major version."
            )
        newer = [install for install in installs if install.major is not None and install.major > preferred_major]
        if newer:
            return sorted(newer, key=candela_sort_key)[0]

    return sorted(installs, key=candela_sort_key, reverse=True)[0]


def run_pdx_generator(
    xlsx_path: Path,
    pdx_generator: Path,
    pdx_template: Path,
    output_dir: Path,
    no_validate: bool,
) -> Path:
    output_pdx = output_dir / f"{xlsx_path.stem}.pdx"
    cmd = [
        sys.executable,
        str(pdx_generator),
        str(xlsx_path),
        "--template",
        str(pdx_template),
        "--output-dir",
        str(output_dir),
    ]
    if no_validate:
        cmd.append("--no-validate")

    print(f"Generating PDX: {output_pdx}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"PDX generation failed with return code {result.returncode}:\n{details}")
    if not output_pdx.exists():
        raise RuntimeError(f"PDX generator returned success, but output PDX was not created: {output_pdx}")
    if result.stdout.strip():
        print(result.stdout.strip())
    return output_pdx


def unique_matching_lines(text: str, patterns: list[str], limit: int, include_error_lines: bool = False) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ((include_error_lines and line.startswith("E:")) or any(pattern in line for pattern in patterns)) and line not in seen:
            matches.append(line)
            seen.add(line)
            if len(matches) >= limit:
                break
    return matches


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def sanitize_cdd_qual(value: str, fallback: str) -> str:
    base = (value or fallback).strip()
    base = base.encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9_]+", "_", base).strip("_")
    if not base:
        base = fallback
    if not re.match(r"[A-Za-z_]", base):
        base = f"X_{base}"
    return base[:120].rstrip("_") or fallback


def deterministic_cdd_oid(scope: str) -> str:
    digest = hashlib.sha1(scope.encode("utf-8")).hexdigest().upper()
    return digest[:32]


def load_snapshot_record_names(xlsx_path: Path, pdx_generator: Path) -> dict[int, str]:
    module_path = pdx_generator.resolve()
    spec = importlib.util.spec_from_file_location("vf_pdx_generator_for_cdd_patch", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load PDX generator for snapshot metadata: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    module_dir = str(module_path.parent)
    inserted_module_dir = False
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        inserted_module_dir = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
        if inserted_module_dir:
            try:
                sys.path.remove(module_dir)
            except ValueError:
                pass
    survey = module.parse_vf_survey(xlsx_path)
    return dict(getattr(survey, "snapshot_record_names", {}) or {})


def sync_snapshot_record_label(record: etree._Element, record_num: int, label: str) -> bool:
    changed = False
    name = record.find("NAME")
    if name is None:
        name = etree.SubElement(record, "NAME")
        changed = True
    tuv = name.find("TUV")
    if tuv is None:
        tuv = etree.SubElement(name, "TUV")
        changed = True
    if tuv.get(XML_LANG) != "en-US":
        tuv.set(XML_LANG, "en-US")
        changed = True
    if tuv.text != label:
        tuv.text = label
        changed = True
    qual = record.find("QUAL")
    if qual is None:
        qual = etree.SubElement(record, "QUAL")
        changed = True
    expected_qual = sanitize_cdd_qual(label, f"Snapshot_Record_0x{record_num:02X}")
    if qual.text != expected_qual:
        qual.text = expected_qual
        changed = True
    return changed


def patch_cdd_snapshot_records(cdd_path: Path, snapshot_record_names: dict[int, str]) -> list[str]:
    """CANdela imports 0xFF as a selector only; keep the CDD record list aligned with the survey."""

    if not snapshot_record_names:
        return []

    parser = etree.XMLParser(remove_blank_text=False, huge_tree=True)
    tree = etree.parse(str(cdd_path), parser)
    root = tree.getroot()
    patched: list[str] = []

    used_oids = {node.get("oid") for node in root.xpath("//*[@oid]") if node.get("oid")}
    for snapshot_records in root.xpath('//*[local-name()="SNAPSHOTRECORDS"]'):
        existing: dict[int, etree._Element] = {}
        for record in snapshot_records.xpath('./*[local-name()="SNAPSHOTRECORD"]'):
            if (record.get("rn") or "").isdigit():
                existing[int(record.get("rn"))] = record
        for record_num, label in sorted(snapshot_record_names.items()):
            if record_num in existing:
                if sync_snapshot_record_label(existing[record_num], record_num, label):
                    patched.append(f"0x{record_num:02X} {label} (renamed)")
                continue
            if record_num != 0xFF:
                continue
            oid = deterministic_cdd_oid(f"{cdd_path.name}:SNAPSHOTRECORD:{record_num:02X}:{label}")
            salt = 2
            while oid in used_oids:
                oid = deterministic_cdd_oid(f"{cdd_path.name}:SNAPSHOTRECORD:{record_num:02X}:{label}:{salt}")
                salt += 1
            used_oids.add(oid)

            record = etree.Element("SNAPSHOTRECORD", rn=str(record_num), oid=oid)
            sync_snapshot_record_label(record, record_num, label)
            snapshot_records.append(record)
            existing[record_num] = record
            patched.append(f"0x{record_num:02X} {label}")

    if patched:
        tree.write(
            str(cdd_path),
            encoding="utf-8",
            xml_declaration=True,
            standalone=False,
            doctype='<!DOCTYPE CANDELA SYSTEM "candela.dtd">',
        )
    return patched


def is_known_sprmib_skip(line: str) -> bool:
    return (
        "Skipped ODX DIAG-SERVICE" in line
        and "_NoResponse" in line
        and "already covered by second DIAG-SERVICE using SupPosRespMsgIndBit" in line
    )


def detect_license_issue(log_text: str, process_text: str) -> list[str]:
    combined = f"{log_text}\n{process_text}"
    patterns = [
        "this edition of candelastudio does not support import",
        "the following edition is licensed: viewer",
        "the following edition is licensed: view",
        "no candelastudio license",
        "no license",
        "license not found",
        "license is not available",
        "license checkout failed",
    ]
    matches: list[str] = []
    seen: set[str] = set()
    for raw_line in combined.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        folded = line.casefold()
        if (line.startswith("E:") and "license" in folded) or any(pattern in folded for pattern in patterns):
            if line not in seen:
                matches.append(line)
                seen.add(line)
                if len(matches) >= 20:
                    break
    return matches


def summarize_import_log(log_path: Path) -> tuple[bool, list[str], list[str]]:
    log_text = read_text_if_exists(log_path)
    success = "ODX ECU Import done" in log_text
    high_risk_patterns = [
        "ODX-Model: Error",
        "unknown Doctype value",
        "Unable to resolve Odxlink",
        "Skipped ODX DIAG-SERVICE",
        "BASE-VARIANT inherits from no PROTOCOL",
    ]
    warning_patterns = [
        "Skipping ODX COMPARAM",
        "Skipped ",
        "Warning:",
    ]
    high_risk = [
        line
        for line in unique_matching_lines(log_text, high_risk_patterns, limit=20, include_error_lines=True)
        if not is_known_sprmib_skip(line)
    ]
    warnings = [line for line in unique_matching_lines(log_text, warning_patterns, limit=20) if line not in high_risk]
    return success, high_risk, warnings


def import_pdx_with_candela(
    pdx_path: Path,
    cdd_template: Path,
    output_cdd: Path,
    log_path: Path,
    candela_exe: Path | None,
    candela_edition: str,
    allow_newer: bool,
    deact: int,
    timeout_seconds: int,
) -> Path:
    cdd_template = cdd_template.resolve()
    pdx_path = pdx_path.resolve()
    output_cdd = output_cdd.resolve()
    log_path = log_path.resolve()

    if not cdd_template.exists():
        raise FileNotFoundError(cdd_template)
    if not pdx_path.exists():
        raise FileNotFoundError(pdx_path)

    output_cdd.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    dtd_version = read_cdd_dtd_version(cdd_template) or "unknown"
    preferred_major = read_cdd_dtd_major(cdd_template)
    install = select_candela_install(candela_exe, preferred_major, allow_newer)

    print(f"CANdelaStudio: {install.exe} ({install.version_text or install.version_key or 'version unknown'}, {install.source})")
    print(f"CDD template: {cdd_template} (dtdvers={dtd_version})")
    print(f"Importing PDX: {pdx_path}")
    print(f"Import log: {log_path}")

    cmd = [
        str(install.exe),
        "/m",
        candela_edition,
        "/e",
        "import",
        "/fullEcu",
        "1",
        "/r",
        str(cdd_template),
        "/i",
        str(pdx_path),
        "/g",
        str(log_path),
        "/o",
        str(output_cdd),
        "/deact",
        str(deact),
        "/q",
        "1",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"CANdelaStudio import timed out after {timeout_seconds} seconds. See log: {log_path}") from exc

    log_text = read_text_if_exists(log_path)
    process_text = "\n".join(part for part in (result.stdout, result.stderr) if part)
    license_lines = detect_license_issue(log_text, process_text)
    success_marker, high_risk, warnings = summarize_import_log(log_path)

    if result.returncode != 0:
        if license_lines:
            details = "\n".join(license_lines[:10])
            raise RuntimeError(
                "CANdelaStudio import failed because the current license/edition does not support import.\n"
                f"{details}\n"
                "Please start CANdelaStudio once and confirm that Standard/Pro/Admin import is licensed, "
                "or configure the correct Vector license before running this script."
            )
        details = "\n".join(high_risk[:10]) or process_text.strip() or log_text.strip()
        raise RuntimeError(f"CANdelaStudio import failed with return code {result.returncode}.\n{details}")

    if license_lines and not output_cdd.exists():
        details = "\n".join(license_lines[:10])
        raise RuntimeError(f"CANdelaStudio license/edition issue detected:\n{details}")
    if not output_cdd.exists():
        raise RuntimeError(f"CANdelaStudio returned success, but output CDD was not created: {output_cdd}")
    if not success_marker:
        raise RuntimeError(f"CANdelaStudio returned success, but the log does not contain 'ODX ECU Import done': {log_path}")
    if high_risk:
        details = "\n".join(high_risk[:10])
        raise RuntimeError(f"CANdelaStudio import completed but high-risk log entries were found:\n{details}")

    print(f"Generated CDD: {output_cdd}")
    if warnings:
        print("CANdela import warnings:")
        for line in warnings[:10]:
            print(f"  {line}")
    return output_cdd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate VF CDD by generating PDX and importing it with CANdelaStudio.")
    parser.add_argument("xlsx", nargs="?", type=Path, help="Input VF diagnosis survey .xlsx file")
    parser.add_argument("--pdx-generator", type=Path, default=DEFAULT_PDX_GENERATOR, help="Path to pdxGen_VF.py")
    parser.add_argument("--pdx-template", type=Path, default=DEFAULT_PDX_TEMPLATE, help="Template PDX passed to pdxGen_VF.py")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Output directory for generated PDX and default CDD")
    parser.add_argument("--no-validate", action="store_true", help="Skip odxtools validation during PDX generation")
    parser.add_argument("--cdd-template", type=Path, default=DEFAULT_CDD_TEMPLATE, help="CDD template/reference document for CANdela import")
    parser.add_argument("--cdd-output", type=Path, help="Output CDD path; defaults to the generated PDX path with .cdd suffix")
    parser.add_argument("--candela-log", type=Path, help="CANdela import log path; defaults next to the output CDD")
    parser.add_argument("--candela-exe", type=Path, help="Path to CANdelaStudio.exe; otherwise auto-detected from template CDD version")
    parser.add_argument(
        "--candela-edition",
        choices=("view", "viewx", "standard", "pro", "admin"),
        default="admin",
        help="CANdelaStudio edition passed via /m; import usually needs standard/pro/admin",
    )
    parser.add_argument(
        "--allow-newer-candela",
        action="store_true",
        help="Allow using a newer CANdelaStudio major version if the template version is not installed",
    )
    parser.add_argument("--candela-deact", type=int, choices=(0, 1), default=1, help="Pass /deact to CANdela ODX import")
    parser.add_argument("--candela-timeout", type=int, default=600, help="CANdela import timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    xlsx_path = args.xlsx or find_default_xlsx(Path.cwd())
    if not xlsx_path.exists():
        raise FileNotFoundError(xlsx_path)
    if not args.pdx_generator.exists():
        raise FileNotFoundError(args.pdx_generator)
    if not args.pdx_template.exists():
        raise FileNotFoundError(args.pdx_template)
    if not args.cdd_template.exists():
        raise FileNotFoundError(args.cdd_template)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    pdx_path = run_pdx_generator(xlsx_path, args.pdx_generator, args.pdx_template, output_dir, args.no_validate)
    cdd_output = args.cdd_output or pdx_path.with_suffix(".cdd")
    candela_log = args.candela_log or cdd_output.with_suffix(".candela-import.log")

    import_pdx_with_candela(
        pdx_path=pdx_path,
        cdd_template=args.cdd_template,
        output_cdd=cdd_output,
        log_path=candela_log,
        candela_exe=args.candela_exe,
        candela_edition=args.candela_edition,
        allow_newer=args.allow_newer_candela,
        deact=args.candela_deact,
        timeout_seconds=args.candela_timeout,
    )
    snapshot_record_names = load_snapshot_record_names(xlsx_path, args.pdx_generator)
    patched_snapshot_records = patch_cdd_snapshot_records(cdd_output, snapshot_record_names)
    if patched_snapshot_records:
        print("Patched CDD snapshot records:")
        for item in patched_snapshot_records:
            print(f"  {item}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
