"""Deterministic native PBIR authoring using Microsoft's published schemas."""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "RetailPulse.Report"
DEFINITION = REPORT / "definition"
PAGES = [("9d3c90b721a44a1b8bea", "Executive Overview"),
         ("af672ae1cead4807ba02", "Store & Product Diagnostics"),
         ("be768aedcad84789ca03", "Forecast Performance")]
INK, MUTED, TEAL, PAPER = "#162B3B", "#526574", "#007F82", "#F3F5F7"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def literal(value):
    encoded = str(value).lower() if isinstance(value, bool) else f"{value}D" if isinstance(value, (int, float)) else "'" + value.replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": encoded}}}


def color(value):
    return {"solid": {"color": literal(value)}}


def obj(**properties):
    return [{"properties": properties}]


def field(table, name, measure=False):
    return {"Measure" if measure else "Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def column(table, name):
    return {"field": field(table, name), "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def metric(name):
    return {"field": field("Metrics", name, True), "queryRef": "Metrics." + name, "nativeQueryRef": name}


class Page:
    def __init__(self, identity, name, subtitle, footer):
        self.identity, self.visuals = identity, []
        self.path = DEFINITION / "pages" / identity
        write(self.path / "page.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": identity, "displayName": name, "displayOption": "FitToPage", "height": 1080, "width": 1920,
            "objects": {"background": obj(color=color(PAPER), transparency=literal(0))}})
        self.text("title", name, (32, 24, 780, 52), 32, INK, True)
        self.text("subtitle", subtitle, (32, 80, 1856, 32), 18)
        self.text("footer", footer, (32, 1000, 1856, 56), 17)
        nav = self.visual("navigation", "pageNavigator", (840, 24, 1048, 56))
        nav["objects"] = {
            "layout": obj(orientation=literal(0), rowCount=literal(1), columnCount=literal(3), cellPadding=literal(8)),
            "text": obj(show=literal(True), fontSize=literal(13), fontFamily=literal("Segoe UI Semibold"), fontColor=color(INK)),
            "fill": obj(show=literal(True), fillColor=color("#E5ECEF"), transparency=literal(0)),
            "outline": obj(show=literal(False)),
            "pages": obj(showHiddenPages=literal(False), showTooltipPages=literal(False))}
        nav["visualContainerObjects"]["background"] = obj(show=literal(False))
        nav["visualContainerObjects"]["border"] = obj(show=literal(False))

    def visual(self, key, kind, rect, roles=None, title=None):
        x, y, width, height = rect
        identity = hashlib.sha256((self.identity + "/" + key).encode()).hexdigest()[:20]
        visual = {"visualType": kind, "drillFilterOtherVisuals": True,
                  "visualContainerObjects": {
                      "background": obj(show=literal(True), color=color("#FFFFFF"), transparency=literal(0)),
                      "border": obj(show=literal(True), color=color("#DFE6EB"), radius=literal(8)),
                      "padding": obj(top=literal(12), bottom=literal(12), left=literal(12), right=literal(12)),
                      "subTitle": obj(show=literal(False)),
                      "title": obj(show=literal(bool(title)), text=literal(title or key), fontSize=literal(14),
                                   fontFamily=literal("Segoe UI Semibold"), fontColor=color(INK))}}
        if roles:
            visual["query"] = {"queryState": {role: {"projections": projections} for role, projections in roles.items()}}
        self.visuals.append({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
                             "name": identity, "position": {"x": x, "y": y, "z": len(self.visuals), "width": width,
                                                            "height": height, "tabOrder": len(self.visuals)}, "visual": visual})
        return visual

    def text(self, key, text, rect, size=18, ink=MUTED, bold=False):
        visual = self.visual(key, "textbox", rect)
        visual["objects"] = {"general": obj(paragraphs=[{"textRuns": [{"value": text, "textStyle": {
            "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI", "fontSize": f"{size}px", "color": ink}}]}])}
        visual["visualContainerObjects"] = {"background": obj(show=literal(False)), "border": obj(show=literal(False)),
                                            "padding": obj(top=literal(0), bottom=literal(0), left=literal(0), right=literal(0))}

    def cards(self, key, measures, rect, font=28):
        visual = self.visual(key, "cardVisual", rect, {"Data": [metric(m) for m in measures]})
        visual["objects"] = {
            "value": [{"selector": {"id": "default"}, "properties": {"fontSize": literal(font), "fontColor": color(INK), "labelDisplayUnits": literal(1)}}],
            "label": [{"selector": {"id": "default"}, "properties": {"fontSize": literal(12)}}],
            "padding": [{"selector": {"id": "default"}, "properties": {"paddingUniform": literal(8)}}],
            "layout": [{"selector": {"id": "default"}, "properties": {"paddingUniform": literal(0)}}]}
        visual["visualContainerObjects"]["padding"] = obj(top=literal(0), bottom=literal(0), left=literal(0), right=literal(0))

    def slicer(self, key, table, name, rect, *, selected=None, bounds=None, numeric=False):
        visual = self.visual(key, "slicer", rect, {"Values": [column(table, name)]})
        visual["objects"] = {
            "data": obj(mode=literal("Between" if bounds or numeric else "Dropdown")),
            "header": obj(show=literal(True), text=literal(name), textSize=literal(12), fontColor=color(INK)),
            "items": obj(textSize=literal(12), fontColor=color(INK)),
            "selection": obj(strictSingleSelect=literal(selected is not None))}
        visual["visualContainerObjects"]["padding"] = obj(top=literal(8), bottom=literal(8), left=literal(8), right=literal(8))
        semantic_column = {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": name}}
        condition = None
        if selected:
            condition = {"In": {"Expressions": [semantic_column], "Values": [[{"Literal": {"Value": "'" + selected + "'"}}]]}}
        elif bounds:
            start, end = bounds
            def datetime_literal(value):
                return {"Literal": {"Value": f"datetime'{value}T00:00:00'"}}
            visual["objects"]["data"][0]["properties"].update({"startDate": {"expr": datetime_literal(start)}, "endDate": {"expr": datetime_literal(end)}})
            condition = {"And": {
                "Left": {"Comparison": {"ComparisonKind": 2, "Left": semantic_column, "Right": datetime_literal(start)}},
                "Right": {"Comparison": {"ComparisonKind": 3, "Left": semantic_column, "Right": datetime_literal(str(date.fromisoformat(end) + timedelta(days=1)))}}}}
        if condition:
            visual["objects"]["general"] = obj(filter={"filter": {"Version": 2, "From": [{"Name": "d", "Entity": table, "Type": 0}], "Where": [{"Condition": condition}]}})

    def chart(self, key, title, category, measures, rect, *, bar=False, ascending=False):
        visual = self.visual(key, "clusteredBarChart" if bar else "lineChart", rect,
                             {"Category": [column(*category)], "Y": [metric(m) for m in measures]}, title)
        sort = metric(measures[0])["field"] if bar else column(*category)["field"]
        visual["query"]["sortDefinition"] = {"sort": [{"field": sort, "direction": "Ascending" if ascending or not bar else "Descending"}], "isDefaultSort": True}
        visual["objects"] = {
            "legend": obj(show=literal(len(measures) > 1), position=literal("Top"), fontSize=literal(11), showTitle=literal(False)),
            "categoryAxis": obj(showAxisTitle=literal(False), fontSize=literal(11)),
            "valueAxis": obj(showAxisTitle=literal(False), fontSize=literal(10)),
            "labels": obj(show=literal(bar), fontSize=literal(10))}
        if not bar:
            visual["objects"]["lineStyles"] = obj(strokeWidth=literal(2.5), areaShow=literal(False), lineChartType=literal("linear"))

    def table(self, key, title, columns, measures, rect):
        visual = self.visual(key, "tableEx", rect, {"Values": [column(*c) for c in columns] + [metric(m) for m in measures]}, title)
        visual["objects"] = {"grid": obj(rowPadding=literal(8)), "columnHeaders": obj(fontSize=literal(11)),
                             "values": obj(fontSize=literal(11)), "total": obj(totals=literal(False))}

    def save(self):
        for visual in self.visuals:
            write(self.path / "visuals" / visual["name"] / "visual.json", visual)


def build():
    theme = {"name": "RetailPulse", "dataColors": [TEAL, "#8193A3", "#C5892F", "#536CB2"], "background": "#FFFFFF", "foreground": INK,
             "tableAccent": TEAL, "good": TEAL, "neutral": "#C5892F", "bad": "#B54B45",
             "textClasses": {"callout": {"fontFace": "Segoe UI Semibold", "fontSize": 28, "color": INK},
                             "title": {"fontFace": "Segoe UI Semibold", "fontSize": 14, "color": INK},
                             "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": INK},
                             "label": {"fontFace": "Segoe UI", "fontSize": 11, "color": MUTED}},
             "visualStyles": {"tableEx": {"*": {"columnHeaders": [{"autoSizeColumnWidth": True, "columnAdjustment": "growToFit", "backColor": {"solid": {"color": PAPER}}}],
                                                     "values": [{"backColorPrimary": {"solid": {"color": "#FFFFFF"}}, "backColorSecondary": {"solid": {"color": "#F5F8FA"}}}]}},
                              "cardVisual": {"*": {"value": [{"bold": True, "$id": "default"}], "label": [{"show": True, "$id": "default"}], "cardCalloutArea": [{"paddingUniform": 0}]}}}}
    theme_name = "RetailPulse-" + hashlib.sha256(json.dumps(theme, sort_keys=True).encode()).hexdigest()[:10] + ".json"
    theme["name"] = theme_name
    write(HERE / "theme.json", theme)
    write(REPORT / "StaticResources/RegisteredResources" / theme_name, theme)
    report = json.loads((DEFINITION / "report.json").read_text(encoding="utf-8"))
    report["themeCollection"]["customTheme"] = {"name": theme_name, "reportVersionAtImport": report["themeCollection"]["baseTheme"]["reportVersionAtImport"], "type": "RegisteredResources"}
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [{"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}]
    write(DEFINITION / "report.json", report)
    write(DEFINITION / "pages/pages.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": [p[0] for p in PAGES], "activePageName": PAGES[0][0]})

    p = Page(*PAGES[0], "RETAILPULSE AI  /  HISTORICAL DEMAND  /  3 stores · 2 departments · 614 products",
             "Known Revenue Proxy sums priced observations only; it is not audited revenue. Missing prices make canonical revenue incomplete. Spikes are heuristic flags.")
    p.slicer("date", "Date", "Date", (32, 120, 500, 104), bounds=("2016-03-28", "2016-05-22"))
    p.slicer("store", "Store", "Store", (556, 120, 320, 104))
    p.slicer("department", "Department", "Department", (900, 120, 320, 104))
    p.text("context", "M5 historical pilot  |  Last observed: 22 May 2016\nFreshness is measured at the Gold snapshot date.", (1244, 128, 644, 80), 20)
    p.cards("kpis", ["Total Units", "Known Revenue Proxy", "Price Coverage", "Demand Spike Count", "Data Freshness"], (32, 248, 1856, 112))
    p.chart("units", "Demand over time · observed units", ("Date", "Date"), ["Total Units"], (32, 384, 1040, 280))
    p.chart("rolling", "Demand direction · rolling 7d / 28d", ("Date", "Date"), ["Rolling 7D Demand", "Rolling 28D Demand"], (1096, 384, 792, 280))
    p.chart("stores", "Units by store", ("Store", "Store"), ["Total Units"], (32, 688, 440, 288), bar=True)
    p.chart("departments", "Units by department", ("Department", "Department"), ["Total Units"], (496, 688, 392, 288), bar=True)
    p.chart("spikes", "Demand spikes · item/store/day flags", ("Date", "Date"), ["Demand Spike Count"], (912, 688, 616, 288))
    p.cards("change", ["Period-over-Period Change %"], (1552, 688, 336, 132))
    p.cards("previous", ["Previous Period Units"], (1552, 844, 336, 132))
    p.save()

    p = Page(*PAGES[1], "RETAILPULSE AI  /  SEGMENT DRIVERS  /  Select a product or chart segment to inspect demand",
             "Whole observed weeks; boundary weeks may be partial. Positive-demand ranks include ties and exclude zero sales. Price, event and SNAP context does not establish causation.")
    p.slicer("week", "Week", "Week Start", (32, 120, 500, 104), bounds=("2016-03-26", "2016-05-21"))
    p.slicer("store", "Store", "Store", (556, 120, 320, 104))
    p.slicer("department", "Department", "Department", (900, 120, 320, 104))
    p.slicer("product", "Product", "Product", (1244, 120, 644, 104))
    p.cards("kpis", ["Product Units", "Product Price Coverage", "Product Spike Count", "Average Price Change %"], (32, 248, 1856, 112))
    p.chart("stores", "Store ranking", ("Store", "Store"), ["Product Units"], (32, 384, 368, 280), bar=True)
    p.chart("departments", "Department ranking", ("Department", "Department"), ["Product Units"], (424, 384, 336, 280), bar=True)
    p.chart("top", "Top products · positive demand", ("Product", "Product"), ["Top Product Units"], (784, 384, 528, 280), bar=True)
    p.chart("bottom", "Bottom products · positive demand", ("Product", "Product"), ["Bottom Product Units"], (1336, 384, 552, 280), bar=True, ascending=True)
    p.chart("evolution", "Product demand · selected observed weeks", ("Week", "Week Start"), ["Product Units"], (32, 688, 904, 288))
    p.table("context", "Price, calendar and spike context · weekly", [("Week", "Week Start")], ["Average Price Change %", "Product Price Coverage", "Event-period Units", "SNAP-period Units", "Product Spike Count"], (960, 688, 928, 288))
    p.save()

    p = Page(*PAGES[2], "RETAILPULSE AI  /  FROZEN BACKTESTS  /  Historical evaluation; future forecasts are excluded",
             "Full test: LightGBM improves WMAPE and MAE versus rolling mean, with worse RMSE. Results vary by segment. WMAPE is a ratio of totals; no test-driven retuning.")
    p.slicer("date", "Date", "Date", (32, 120, 500, 104), bounds=("2016-03-28", "2016-05-22"))
    p.slicer("model", "Model", "Model", (556, 120, 320, 104), selected="LightGBM")
    p.slicer("split", "Split", "Split", (900, 120, 240, 104), selected="test")
    p.slicer("store", "Store", "Store", (1164, 120, 320, 104))
    p.slicer("department", "Department", "Department", (1508, 120, 380, 104))
    p.slicer("horizon", "Horizon", "Horizon", (32, 248, 320, 104), numeric=True)
    p.slicer("demand", "Demand", "Demand Level", (376, 248, 320, 104))
    p.cards("kpis", ["WMAPE", "MAE", "RMSE", "Forecast Bias"], (720, 248, 1168, 104), 26)
    p.chart("actual", "Actual vs predicted units · selected model", ("Date", "Date"), ["Actual Units", "Predicted Units"], (32, 384, 1040, 280))
    p.table("comparison", "Model comparison · same selected segment", [("ComparisonModel", "Model")], ["Comparison WMAPE", "Comparison MAE", "Comparison RMSE"], (1096, 384, 792, 280))
    p.chart("horizon-error", "WMAPE by horizon · selected model vs rolling mean", ("Horizon", "Horizon"), ["WMAPE", "Rolling Mean WMAPE"], (32, 688, 760, 288))
    p.chart("store-error", "WMAPE by store", ("Store", "Store"), ["WMAPE"], (816, 688, 344, 288), bar=True)
    p.chart("department-error", "WMAPE by department", ("Department", "Department"), ["WMAPE"], (1184, 688, 320, 288), bar=True)
    p.table("demand-error", "Demand-level error", [("Demand", "Demand Level")], ["WMAPE", "MAE", "RMSE"], (1528, 688, 360, 288))
    p.save()
    print("Authored exactly three native report pages.")


if __name__ == "__main__":
    build()
