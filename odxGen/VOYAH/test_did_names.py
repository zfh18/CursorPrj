import zipfile
import sys
from pathlib import Path

from lxml import etree

from pdxGen_VOYAH import (
    SCRIPT_DIR,
    Conversion,
    CoverInfo,
    DidDef,
    IdGenerator,
    IoDidDef,
    ParamDef,
    SurveyData,
    update_odx,
)


def main() -> None:
    with zipfile.ZipFile(SCRIPT_DIR / "templates" / "VOYAH_ECU_CAN_v15.pdx") as package:
        root = etree.fromstring(package.read("VOYAH_ECU_CAN_v15.odx-d"))
    display_name = "\u4e0b\u7ebf\u914d\u7f6e"
    eol = DidDef(
        0xF010, f"EOL_DataIdentifier\n{display_name}", 8,
        params=[ParamDef("EOL", "EOL", 0, 0, 64)], sessions=["RW"],
    )
    duplicates = [DidDef(value, "Self_learning_information", 1) for value in (0x0D89, 0x0D8B)]
    for index, item in enumerate(duplicates):
        item.params = [ParamDef(
            "Result", "Result", 0, 0, 8,
            conversion=Conversion(kind="enum", enum=[(index, index, str(index))]),
        )]
    io_did = IoDidDef(0xF011, f"Motor_control\n{display_name}", 1, controls={3})
    survey = SurveyData(CoverInfo(), [eol, *duplicates], [io_did], [], [], [], [])
    update_odx(root, IdGenerator(root), survey)

    assert eol.long_name == display_name
    assert [item.short_name for item in duplicates] == [
        "Self_learning_information", "Self_learning_information_0x0D8B",
    ]
    dop_names = {}
    for item in [eol, *duplicates, io_did]:
        wrapper_id = item.wrapper_id if isinstance(item, DidDef) else item.status_wrapper_id
        wrapper = root.xpath("//*[@ID=$id]", id=wrapper_id)[0]
        wrapper_param = wrapper.find("PARAMS/PARAM")
        assert wrapper_param.findtext("SHORT-NAME") == item.short_name
        assert wrapper_param.findtext("LONG-NAME") == item.long_name
        assert wrapper_param.findtext("BYTE-POSITION") == "0"
        assert wrapper_param.find("DOP-REF").get("ID-REF") == item.structure_id
        structure = root.xpath("//*[@ID=$id]", id=item.structure_id)[0]
        assert structure.findtext("LONG-NAME") == item.long_name
        assert structure.findtext("BYTE-SIZE") == str(item.size)
        for param in item.params:
            dop = root.xpath("//*[@ID=$id]", id=param.dop_id)[0]
            dop_names[param.dop_id] = dop.findtext("SHORT-NAME")
    assert len(dop_names) == len(set(dop_names.values()))
    assert eol.params[0].name == "EOL" and eol.params[0].bit_len == 64
    for table_name in ("Identification_Read_PR", "Identification_Write_RQ"):
        rows = root.xpath("//TABLE[SHORT-NAME=$name]/TABLE-ROW[KEY='61456']", name=table_name)
        assert len(rows) == 1
        assert rows[0].findtext("LONG-NAME") == eol.short_name
    print("DID/IO naming regression checks passed")
    for path in sys.argv[1:]:
        cdd = etree.parse(path)
        with zipfile.ZipFile(Path(path).with_suffix(".pdx")) as package:
            odx = etree.fromstring(package.read("VOYAH_ECU_CAN_v15.odx-d"))
        expected = {
            int(row.findtext("KEY")): row.findtext("SHORT-NAME")
            for row in odx.xpath("//TABLE[SHORT-NAME='Identification_Read_PR' or SHORT-NAME='IOControl_Control_PR']/TABLE-ROW")
        }
        assert expected.get(0xF010) == "EOL_DataIdentifier"
        for value, qualifier in expected.items():
            dids = cdd.xpath("//DID[@n=$n]", n=str(value))
            assert len(dids) == 1, (path, value)
            assert dids[0].findtext("QUAL") == qualifier, (path, value)
            refs = cdd.xpath("//DIDDATAREF[@didRef=$id]", id=dids[0].get("id"))
            assert refs and all(ref.findtext("QUAL") == qualifier for ref in refs)
        instances = cdd.xpath("//DIAGINST[QUAL='EOL_DataIdentifier']")
        assert len(instances) == 1
        assert instances[0].findtext("NAME/TUV") == display_name
        assert instances[0].xpath("SERVICE/SHORTCUTQUAL[text()='EOL_DataIdentifier_Write']")
        print(f"Generated CDD naming checks passed: {path}")


if __name__ == "__main__":
    main()
