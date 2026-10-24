"""Small local Chrome lab sample; no field/representative INP claim."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    reports = []
    for width in [1440, 360]:
        page = browser.new_page(viewport={"width": width, "height": 1000})
        page.add_init_script(
            "window.__lab={lcp:[],cls:0,events:[]};new PerformanceObserver(l=>window.__lab.lcp.push(...l.getEntries().map(e=>e.startTime))).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__lab.cls+=e.value;}).observe({type:'layout-shift',buffered:true});new PerformanceObserver(l=>window.__lab.events.push(...l.getEntries().filter(e=>e.interactionId).map(e=>({id:e.interactionId,duration:e.duration,name:e.name})))).observe({type:'event',buffered:true,durationThreshold:16});"
        )
        page.goto("http://localhost:3000", wait_until="networkidle")
        page.evaluate(
            "async()=>{await document.fonts.ready;await Promise.all([...document.images].filter(i=>i.loading!=='lazy').map(i=>i.decode().catch(()=>{})));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}"
        )
        result = page.evaluate(
            "({width:innerWidth,lcp_ms:window.__lab.lcp.at(-1)||null,cls:window.__lab.cls,overflow:document.documentElement.scrollWidth>innerWidth})"
        )
        page.get_by_label("Bạn đang tìm gì?", exact=True).press_sequentially(
            "ao len nam mau den duoi 500k", delay=45
        )
        page.get_by_label("Bạn đang tìm gì?", exact=True).press("Tab")
        page.evaluate("()=>new Promise(r=>setTimeout(r,500))")
        interactions = page.evaluate("window.__lab.events")
        result["interaction_events"] = interactions
        result["inp_lab_candidate_ms"] = max(
            (e["duration"] for e in interactions), default=None
        )
        result["inp_scope"] = (
            "One short real typing/focus journey, <50 interactions: largest observed EventTiming duration (16ms reporting threshold). Lab candidate only, not field/representative INP. null means no >=16ms entry observed."
        )
        reports.append(result)
        page.close()
    (ROOT / "docs/evidence/browser-lab.json").write_text(
        json.dumps(
            {
                "scope": "Two unthrottled local Chrome navigations, Docker production frontend; lab only, no field percentile claim",
                "samples": reports,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    browser.close()
