"""Check field bindings, deterministic identities and canvas geometry offline."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = ["Executive Overview", "Store & Product Diagnostics", "Forecast Performance"]
NATIVE = {"textbox", "pageNavigator", "slicer", "cardVisual", "lineChart", "clusteredBarChart", "tableEx"}


def validate(project=HERE):
    definition = project / "RetailPulse.Report/definition"
    model = project / "RetailPulse.SemanticModel/definition"
    fields = {}
    for path in (model / "tables").glob("*.tmdl"):
        text = path.read_text(encoding="utf-8-sig")
        table = re.search(r"^table (.+)$", text, re.M)[1].strip("'")
        fields[table] = {kind: {match.strip("'") for match in re.findall(rf"^\t{kind} ('[^']+'|[^\s=]+)", text, re.M)} for kind in ("column", "measure")}
    metadata = json.loads((definition / "pages/pages.json").read_text(encoding="utf-8"))
    page_ids = metadata["pageOrder"]
    assert len(page_ids) == len(set(page_ids)) == 3
    assert {p.name for p in (definition / "pages").iterdir() if p.is_dir()} == set(page_ids)
    ids, total = set(), 0
    for identity, name in zip(page_ids, EXPECTED, strict=True):
        page_path = definition / "pages" / identity
        page = json.loads((page_path / "page.json").read_text(encoding="utf-8"))
        assert page["displayName"] == name and page["name"] == identity
        rectangles, types = [], []
        for path in sorted((page_path / "visuals").glob("*/visual.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["name"] not in ids and data["name"] == path.parent.name
            ids.add(data["name"])
            visual = data["visual"]
            types.append(visual["visualType"])
            assert types[-1] in NATIVE
            pos = data["position"]
            x, y, w, h = (pos[k] for k in ("x", "y", "width", "height"))
            assert x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= page["width"] and y+h <= page["height"], path
            for px, py, pw, ph in rectangles:
                assert not (x < px+pw and x+w > px and y < py+ph and y+h > py), path
            rectangles.append((x, y, w, h))
            for role in visual.get("query", {}).get("queryState", {}).values():
                for projection in role["projections"]:
                    kind, value = next(iter(projection["field"].items()))
                    table = value["Expression"]["SourceRef"]["Entity"]
                    assert value["Property"] in fields[table][kind.lower()], (path, projection)
            total += 1
        assert types.count("pageNavigator") == 1 and "slicer" in types and "cardVisual" in types
    relations = (model / "relationships.tmdl").read_text(encoding="utf-8-sig")
    assert len(re.findall(r"^relationship ", relations, re.M)) == 14
    assert "bothDirections" not in relations
    assert 'expression DataFolder = ""' in (model / "expressions.tmdl").read_text(encoding="utf-8-sig")
    return {"pages": 3, "visuals": total, "tables": len(fields), "measures": len(fields["Metrics"]["measure"]), "status": "PASS"}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
