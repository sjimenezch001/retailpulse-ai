"""Session-scoped presentation tokens. Never mutate global Streamlit settings."""

PALETTES = {
    "light": dict(
        bg="#F9F9F7",
        card="#FFFFFF",
        text="#1B1B18",
        muted="#626560",
        accent="#387D70",
        line="#E3E3DE",
        soft="#F0F1EC",
        blue="#798898",
        amber="#A78354",
    ),
    "dark": dict(
        bg="#111214",
        card="#1A1C1F",
        text="#F2F3F5",
        muted="#ABB0B7",
        accent="#7CC7B8",
        line="#383B40",
        soft="#202328",
        blue="#A4B7CC",
        amber="#DCC396",
    ),
}


def css(theme):
    p = PALETTES[theme]
    return f"""<style>
    :root {{ --rp-bg:{p["bg"]}; --rp-card:{p["card"]}; --rp-text:{p["text"]}; --rp-muted:{p["muted"]}; --rp-accent:{p["accent"]}; --rp-line:{p["line"]}; --rp-soft:{p["soft"]}; color-scheme:{theme}; }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {{background:var(--rp-bg);color:var(--rp-text)}}
    html,body,.stApp,.stApp p,.stApp h1,.stApp h2,.stApp h3,.stApp h4,input,textarea,button,select,[data-baseweb] {{font-family:'Segoe UI Variable','Segoe UI',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif!important}}
    .block-container {{padding-top:4.25rem;max-width:1500px;padding-bottom:2rem}}
    h1,h2,h3,h4 {{color:var(--rp-text)!important;letter-spacing:-.025em;line-height:1.25}}
    h1 {{font-size:clamp(1.85rem,3vw,3rem)!important;font-weight:350!important;letter-spacing:-.035em!important;max-width:28ch}} h3 {{font-size:1.4rem!important;font-weight:550!important}}
    [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], label, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{color:var(--rp-text)}}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{color:var(--rp-muted)!important;line-height:1.6;opacity:1!important}}
    [data-testid="stSidebar"] {{background:var(--rp-card);border-right:1px solid var(--rp-line)}}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{gap:.8rem}}
    [data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"]>div {{background:var(--rp-card);border-color:var(--rp-line)!important;border-radius:12px;box-shadow:0 3px 12px #00000005}}
    [data-testid="stMetric"] {{padding:1rem 1.1rem!important;min-height:112px;border:1px solid var(--rp-line)}}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] p {{font-weight:550;font-size:clamp(1.2rem,1.5vw,1.5rem)!important;line-height:1.3;font-variant-numeric:tabular-nums;letter-spacing:-.025em;overflow:visible;white-space:normal;text-overflow:clip}}
    [data-testid="stMetricValue"] [data-testid="stMarkdownContainer"] {{overflow:visible;white-space:normal}}
    [data-testid="stMetricLabel"] p {{font-size:.82rem;white-space:normal;line-height:1.35}}
    [data-baseweb="tab-list"] {{gap:1.25rem;border-bottom:1px solid var(--rp-line);background:transparent}}
    [data-baseweb="tab"] {{color:var(--rp-muted)!important;background:transparent;font-weight:600;padding:.7rem .15rem}}
    [data-baseweb="tab"][aria-selected="true"] {{color:var(--rp-accent)!important}}
    [data-baseweb="tab-highlight"] {{background:var(--rp-accent)}}
    [data-baseweb="input"], [data-baseweb="input"]>div, [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"]>div, [data-testid="stChatInput"] {{background:var(--rp-card)!important;color:var(--rp-text)!important;border-color:var(--rp-line)!important;border-radius:9px}}
    input,textarea, [data-baseweb="select"] span, [data-baseweb="select"] input {{color:var(--rp-text)!important;-webkit-text-fill-color:var(--rp-text)}}
    input::placeholder,textarea::placeholder {{color:var(--rp-muted)!important;opacity:1}}
    [data-testid="stTextInputRootElement"], [data-testid="stTextInputField"], input[role="combobox"], .react-aria-ComboBox, .react-aria-Group, [data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input, textarea {{background:var(--rp-card)!important;color:var(--rp-text)!important;border-color:var(--rp-line)!important}}
    [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p, [data-testid="stTooltipIcon"] button {{color:var(--rp-text)!important}}
    [data-testid="stSelectbox"] [role="group"], [data-testid="stSelectbox"] button, [data-testid="stMultiSelect"] [role="group"], [data-testid="stMultiSelect"] button {{background:var(--rp-card)!important;color:var(--rp-text)!important;border-color:var(--rp-line)!important}}
    [data-testid="stSelectbox"] svg,[data-testid="stMultiSelect"] svg,[data-testid="stTooltipIcon"] svg {{color:var(--rp-muted)!important}}
    [role="tablist"] {{border-bottom:1px solid var(--rp-line);gap:1.2rem}}
    [role="tab"] {{background:transparent!important;color:var(--rp-muted)!important;font-weight:600}}
    [role="tab"][aria-selected="true"] {{color:{"#0F766E" if theme == "light" else p["accent"]}!important}}
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [role="option"] {{background:var(--rp-card)!important;color:var(--rp-text)!important}}
    [role="option"]:hover,[role="option"][aria-selected="true"] {{background:var(--rp-soft)!important}}
    [data-baseweb="tag"] {{background:var(--rp-soft)!important;color:var(--rp-text)!important}}
    button, [data-testid="stLinkButton"] a {{border-color:var(--rp-line)!important;color:var(--rp-text)!important;background:var(--rp-card)!important;border-radius:8px}}
    [data-testid="stChatInput"]>div, [data-testid="stChatInput"]>div>div {{background:var(--rp-card)!important;border-color:var(--rp-line)!important}}
    [data-testid="stChatInputSubmitButton"]:disabled {{opacity:.45}}
    button:hover,[data-testid="stLinkButton"] a:hover {{border-color:var(--rp-accent)!important;color:var(--rp-accent)!important}}
    button:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible {{outline:2px solid var(--rp-accent)!important;outline-offset:3px}}
    [data-baseweb="radio"]>div {{border-color:var(--rp-muted)}}
    [data-testid="stExpander"] {{background:var(--rp-card);border-color:var(--rp-line);border-radius:10px}}
    [data-testid="stExpander"] summary {{color:var(--rp-text)!important;background:transparent}}
    [data-testid="stChatMessage"] {{background:var(--rp-card);border:1px solid var(--rp-line);border-radius:12px;padding:1.1rem;margin:.35rem 0}}
    [data-testid="stChatMessageContent"] p {{line-height:1.7;max-width:85ch}}
    [data-testid="stChatMessage"] [data-testid="stMetricValue"], [data-testid="stChatMessage"] [data-testid="stMetricValue"] p {{font-size:2.25rem!important;color:{"#0F766E" if theme == "light" else p["accent"]}!important}}
    [data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"] {{gap:.55rem}}
    [data-testid="stAlert"] {{background:var(--rp-soft);color:var(--rp-text);border:1px solid var(--rp-line);border-left:3px solid var(--rp-accent);border-radius:9px}}
    [data-testid="stAlert"] p {{color:var(--rp-text)!important;font-size:.92rem}}
    [data-testid="stJson"], [data-testid="stCode"], pre,code {{background:var(--rp-soft)!important;color:var(--rp-text)!important}}
    [data-testid="stJson"] span {{color:var(--rp-text)!important}}
    .rp-table {{width:100%;border-collapse:collapse;font-size:.92rem;background:var(--rp-card);color:var(--rp-text)}}
    .rp-table th,.rp-table td {{text-align:left;padding:.7rem;border-bottom:1px solid var(--rp-line)}}
    .rp-table th {{color:var(--rp-muted);font-weight:600}}
    .rp-table-wrap {{overflow-x:auto;border:1px solid var(--rp-line);border-radius:10px}}
    .rp-eyebrow {{font-size:.78rem;font-weight:650;letter-spacing:.08em;color:var(--rp-text);margin:.3rem 0 .6rem}}
    .rp-pipeline {{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:1.3rem 0}}
    .rp-stage {{position:relative;background:var(--rp-card);border:1px solid var(--rp-line);border-top:3px solid var(--rp-accent);border-radius:12px;padding:1.2rem}}
    .rp-stage small {{color:var(--rp-muted);font-size:.8rem}} .rp-stage h4 {{margin:.6rem 0}} .rp-stage p {{font-size:.94rem;line-height:1.6}}
    .rp-stage:not(:last-child):after {{content:'→';position:absolute;right:-15px;top:45%;color:var(--rp-accent);z-index:1}}
    .vega-tooltip {{background:var(--rp-card)!important;color:var(--rp-text)!important;border-color:var(--rp-line)!important}}
    hr {{border-color:var(--rp-line)}} a {{color:var(--rp-accent)}} svg {{color:inherit}}
    @media(max-width:900px) {{.block-container {{padding:4rem 1rem 1rem}} .rp-pipeline {{grid-template-columns:1fr 1fr}} .rp-stage:after {{display:none}}}}
    @media(max-width:600px) {{.rp-pipeline {{grid-template-columns:1fr}} [data-testid="stHorizontalBlock"] {{flex-wrap:wrap}} [data-testid="stColumn"] {{min-width:min(100%,220px)!important;flex:1 1 220px!important}} [data-baseweb="tab-list"] {{gap:.8rem}}}}
    </style>"""


def chart_style(chart, theme, language="en"):
    p = PALETTES[theme]
    return (
        chart.configure(
            background=p["bg"],
            font="Segoe UI",
            locale={
                "number": {
                    "decimal": "," if language == "es" else ".",
                    "thousands": "." if language == "es" else ",",
                    "grouping": [3],
                    "currency": ["", ""],
                }
            },
        )
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=p["muted"],
            titleColor=p["text"],
            gridColor=p["line"],
            domainColor=p["line"],
            tickColor=p["line"],
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_legend(labelColor=p["text"], titleColor=p["muted"], labelFontSize=12)
    )
