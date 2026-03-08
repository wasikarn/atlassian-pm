#!/usr/bin/env python3
"""Create Confluence page: Backend-Driven Player Architecture — Design Proposal.

Creates under BEP space as a child of 'Player Doc' (page 81592324).
Idempotent: checks if page already exists by title.
"""

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts")
)
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib import ConfluenceAPI

SPACE_KEY = "BEP"
PARENT_PAGE_ID = "81592324"  # Player Doc
PAGE_TITLE = "Architecture Proposal: Backend-Driven Player — Dumb Renderer + Offline Resilience"
ARCH_PAGE_ID = "165019751"  # The architecture page itself

# ─── Sub-Page Config ───
PAGE_IDS_FILE = Path(__file__).parent / "architecture-page-ids.json"

SUB_PAGE_TITLES = {
    "1_problem_current": "1. ปัญหาปัจจุบันและสถาปัตยกรรมเดิม (Problem Statement)",
    "2_proposed": "2. สถาปัตยกรรมที่เสนอ (Proposed Architecture)",
    "3_key_flows": "3. Flow หลัก (Key Flows)",
    "4_tech_algorithm": "4. Technical Design: Algorithm และ Models",
    "5_tech_player": "5. Technical Design: Player Components",
    "6_interrupt_makegood": "6. Interrupt Controller และระบบ Make-Good",
    "7_events": "7. สถาปัตยกรรม Event-Driven",
    "8_edge_migration": "8. Edge Cases, Migration และ Terminology Reference",
    "9_es_big_picture": "9. Event Storming: ภาพรวม (Big Picture)",
    "10_es_process": "10. Event Storming: Process Modelling",
    "11_es_design": "11. Event Storming: Software Design",
    "12_usecase_distribution": "12. Use Case: การกระจาย Ad และรอบการคำนวณ (Ad Distribution & Scheduling)",
    "13_usecase_industry": "13. Industry Context: Standards, Comparison & Design Rationale",
    "14_usecase_catalog": "14. Use Case Catalog: ทุก Scenarios ที่เป็นไปได้",
}


def load_page_ids() -> dict:
    if PAGE_IDS_FILE.exists():
        return json.loads(PAGE_IDS_FILE.read_text(encoding="utf-8"))
    return {"parent": ARCH_PAGE_ID, "pages": {k: None for k in SUB_PAGE_TITLES}}


def save_page_ids(data: dict):
    PAGE_IDS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

# ─── Mermaid Forge App Constants ───
MERMAID_APP_ID = "23392b90-4271-4239-98ca-a3e96c663cbb"
MERMAID_ENV_ID = "63d4d207-ac2f-4273-865c-0240d37f044a"
MERMAID_INSTALL_ID = "5c245bad-32e8-4c74-aa1c-6d227f18fa22"
CLOUD_ID = "85ad5bd2-ef9c-477e-b000-062f1421d0c0"
RESOURCE_UPLOAD_ID = "9f9d6c69-f97f-4e32-b336-cca6d907aa0b"
ACCOUNT_ID = "712020:64219948-720a-4925-a48c-d7a53557993c"
BEP_SPACE_ID = "1081347"
WORKSPACE_ID = "2f960cad-efff-4621-bb36-aa7f65cf74df"
ICON_URL = (
    f"https://icon.cdn.prod.atlassian-dev.net/"
    f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/{RESOURCE_UPLOAD_ID}/icons/app-icon.png"
)

# ─── Diagram Files ───
DIAGRAMS_DIR = Path(__file__).parent / "diagrams"


def load_diagram(name: str) -> str:
    """Load .mmd file from diagrams/ directory."""
    return (DIAGRAMS_DIR / name).read_text(encoding="utf-8").strip()


# Global code block counter (Forge index counts ALL code blocks on page)
_code_block_count = 0


def toc():
    return (
        '<ac:structured-macro ac:name="toc" ac:schema-version="1">'
        '<ac:parameter ac:name="minLevel">2</ac:parameter>'
        '<ac:parameter ac:name="maxLevel">3</ac:parameter>'
        "</ac:structured-macro>\n"
    )


def info_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def note_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def warning_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="warning" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def success_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="success" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def error_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="error" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def code_block(code: str, language: str = "text", title: str = "",
               collapse: bool = False) -> str:
    parts = [
        '<ac:structured-macro ac:name="code" ac:schema-version="1">',
        f'<ac:parameter ac:name="language">{language}</ac:parameter>',
    ]
    if title:
        parts.append(f'<ac:parameter ac:name="title">{title}</ac:parameter>')
    if collapse:
        parts.append('<ac:parameter ac:name="collapse">true</ac:parameter>')
    parts.append(f"<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>")
    parts.append("</ac:structured-macro>")
    return "".join(parts)


def tracked_code_block(code: str, language: str = "text", title: str = "",
                       collapse: bool = False) -> str:
    """code_block() with global counter for Forge index tracking."""
    global _code_block_count
    result = code_block(code, language, title, collapse=collapse)
    _code_block_count += 1
    return result


def mermaid_diagram(code: str, page_id: str) -> str:
    """Generate mermaid code block + Forge renderer macro.

    Uses global _code_block_count as the Forge index, then increments it.
    """
    global _code_block_count
    index = _code_block_count
    _code_block_count += 1

    local_id = str(uuid.uuid4())
    code_local_id = str(uuid.uuid4())
    ext_id = (
        f"ari:cloud:ecosystem::extension/"
        f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/static/mermaid-diagram"
    )
    ext_key = f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/static/mermaid-diagram"
    consent_url = (
        f"https://id.atlassian.com/outboundAuth/start?"
        f"containerId={MERMAID_APP_ID}_{MERMAID_ENV_ID}"
        f"&amp;serviceKey=atlassian-token-service-key"
        f"&amp;cloudId={CLOUD_ID}"
        f"&amp;isAccountBased=true"
        f"&amp;scopes=read%3Apage%3Aconfluence+offline_access"
    )
    context_ari = f"ari:cloud:confluence:{CLOUD_ID}:workspace/{WORKSPACE_ID}"

    params = (
        f'<ac:adf-parameter key="local-id">{local_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-id">{ext_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-title">Mermaid diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="layout">extension</ac:adf-parameter>'
        f'<ac:adf-parameter key="forge-environment">PRODUCTION</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-properties">'
        f'<ac:adf-parameter key="extension">'
        f'<ac:adf-parameter key="id">{ext_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="app-id">{MERMAID_APP_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="key">mermaid-diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-id">{MERMAID_ENV_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-type">PRODUCTION</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-key">production</ac:adf-parameter>'
        f'<ac:adf-parameter key="properties">'
        f'<ac:adf-parameter key="resource-upload-id">{RESOURCE_UPLOAD_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="resource">custom-ui</ac:adf-parameter>'
        f'<ac:adf-parameter key="icon">{ICON_URL}</ac:adf-parameter>'
        f'<ac:adf-parameter key="description">Render a Mermaid diagram from a code block on a page</ac:adf-parameter>'
        f'<ac:adf-parameter key="categories">'
        f'<ac:adf-parameter-value>confluence-content</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>development</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>formatting</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>visuals</ac:adf-parameter-value>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="title">Mermaid diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">xen:macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="config">'
        f'<ac:adf-parameter key="render">native</ac:adf-parameter>'
        f'<ac:adf-parameter key="resource">macro-config</ac:adf-parameter>'
        f'<ac:adf-parameter key="title">Mermaid diagram configuration</ac:adf-parameter>'
        f'<ac:adf-parameter key="viewport-size">small</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="key">mermaid-diagram</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">xen:macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="installation-id">{MERMAID_INSTALL_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="app-version">2.45.0</ac:adf-parameter>'
        f'<ac:adf-parameter key="consent-url">{consent_url}</ac:adf-parameter>'
        f'<ac:adf-parameter key="egress"><ac:adf-parameter-value></ac:adf-parameter-value></ac:adf-parameter>'
        f'<ac:adf-parameter key="scopes"><ac:adf-parameter-value>read:page:confluence</ac:adf-parameter-value></ac:adf-parameter>'
        f'<ac:adf-parameter key="data-classification-policy-decision">'
        f'<ac:adf-parameter key="status">ALLOWED</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-data">'
        f'<ac:adf-parameter key="type">macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="content">'
        f'<ac:adf-parameter key="id">{page_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">page</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="space">'
        f'<ac:adf-parameter key="key">BEP</ac:adf-parameter>'
        f'<ac:adf-parameter key="id">{BEP_SPACE_ID}</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="account-id">{ACCOUNT_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="cloud-id">{CLOUD_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="context-ids">'
        f'<ac:adf-parameter-value>{context_ari}</ac:adf-parameter-value>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="guest-params">'
        f'<ac:adf-parameter key="index" type="integer">{index}</ac:adf-parameter>'
        f'</ac:adf-parameter>'
    )

    def adf_node():
        return (
            f'<ac:adf-node type="extension">'
            f'<ac:adf-attribute key="extension-key">{ext_key}</ac:adf-attribute>'
            f'<ac:adf-attribute key="extension-type">com.atlassian.ecosystem</ac:adf-attribute>'
            f'<ac:adf-attribute key="parameters">{params}</ac:adf-attribute>'
            f'<ac:adf-attribute key="text">Mermaid diagram</ac:adf-attribute>'
            f'<ac:adf-attribute key="layout">default</ac:adf-attribute>'
            f'<ac:adf-attribute key="local-id">{local_id}</ac:adf-attribute>'
            f'</ac:adf-node>'
        )

    expand_local_id = str(uuid.uuid4())
    code_html = (
        f'<ac:structured-macro ac:local-id="{code_local_id}" '
        f'ac:name="code" ac:schema-version="1">'
        f'<ac:parameter ac:name="language">mermaid</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )
    # Wrap code block in Expand macro — hides source code by default
    expand_html = (
        f'<ac:structured-macro ac:local-id="{expand_local_id}" '
        f'ac:name="expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">Mermaid Source</ac:parameter>'
        f'<ac:rich-text-body>{code_html}</ac:rich-text-body>'
        f'</ac:structured-macro>'
    )
    forge_html = (
        f'<ac:adf-extension>'
        f'{adf_node()}'
        f'<ac:adf-fallback>{adf_node()}</ac:adf-fallback>'
        f'</ac:adf-extension>'
    )
    # Expand (collapsed source) + Forge renderer (always visible diagram)
    return expand_html + forge_html


def expand_section(title: str, content: str) -> str:
    """Wrap content in an Expand macro (collapsed by default)."""
    local_id = str(uuid.uuid4())
    return (
        f'<ac:structured-macro ac:local-id="{local_id}" '
        f'ac:name="expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{title}</ac:parameter>'
        f'<ac:rich-text-body>{content}</ac:rich-text-body>'
        f'</ac:structured-macro>'
    )


def status_macro(text: str, colour: str = "Grey") -> str:
    return (
        f'<ac:structured-macro ac:name="status" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{text}</ac:parameter>'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f"</ac:structured-macro>"
    )


def children_macro() -> str:
    """Confluence Children macro — lists child pages automatically."""
    return (
        '<ac:structured-macro ac:name="children" ac:schema-version="2">'
        '<ac:parameter ac:name="all">true</ac:parameter>'
        '<ac:parameter ac:name="sort">creation</ac:parameter>'
        "</ac:structured-macro>"
    )


def build_parent_content(page_id: str = ARCH_PAGE_ID) -> str:
    """Parent page: Executive Summary text + Children macro (0 mermaid, 0 code blocks)."""
    sections = []

    # Header metadata
    sections.append(info_panel(
        "<p>"
        "<strong>Status:</strong> " + status_macro("DRAFT", "Yellow") + "<br/>"
        "<strong>Author:</strong> BIG-TATHEP<br/>"
        "<strong>Date:</strong> 2026-02-20<br/>"
        "<strong>Related:</strong> "
        '<a href="https://100-stars.atlassian.net/wiki/spaces/BEP/pages/81592324">Player Doc</a>'
        " | "
        '<a href="https://100-stars.atlassian.net/browse/BEP-3335">BEP-3335 Redis Optimization Epic</a>'
        "</p>"
    ))

    # Executive Summary (TEXT ONLY — diagrams moved to page 2)
    sections.append("<h2>Executive Summary</h2>")
    sections.append(success_panel(
        "<p><strong>Problem:</strong> Player มี scheduling logic <strong>3,500+ บรรทัด</strong> "
        "ที่จัดลำดับ ad เอง + ไม่มี offline resilience (fresh boot + no internet = <strong>จอดำ</strong>) "
        "+ ไม่รองรับ premium products (Daypart Takeover, Exact-Time Spot)</p>"
        "<p><strong>Solution:</strong> Backend ส่ง <strong>ordered screen schedule (loop sequence)</strong> แทนที่จะส่ง bag of creatives + rules. "
        "Player แค่เล่น <code>sequence[i++]</code> (Dumb Renderer) + <strong>Interrupt Controller</strong> สำหรับ P0/P1 premium เท่านั้น</p>"
        "<p><strong>Impact:</strong> Player complexity <strong>&darr;80%</strong>, "
        "offline support ผ่าน 3-tier cache (Live &rarr; Buffer &rarr; Fallback), "
        "idempotent sync ป้องกัน duplicate PoP, "
        "<strong>+ premium products:</strong> Daypart Takeover (เหมา time block) + Exact-Time Spot (เล่นตรงเวลา) "
        "with make-good compensation</p>"
    ))

    # Children macro — auto-lists sub-pages
    sections.append("<h2>Contents</h2>")
    sections.append(children_macro())

    return "\n".join(sections)


def build_content(page_id: str = ARCH_PAGE_ID) -> str:
    """LEGACY — original monolithic build. Kept for reference."""
    return build_parent_content(page_id)


# ═══════════════════════════════════════════════════════════════
# Sub-Page Builders
# ═══════════════════════════════════════════════════════════════


def build_page_1(page_id: str) -> str:
    """Page 1: Problem Statement & Current Architecture (2 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())

    # ── Problem Statement ──
    sections.append("<h2>1. ปัญหาปัจจุบัน (Problem Statement)</h2>")
    sections.append(error_panel(
        "<p><strong>Smart Player (ความซับซ้อนของ Scheduling)</strong></p>"
        "<ul>"
        "<li>Player จัดลำดับ creatives เองใน local (SchedulePlay, TimeSlot, Playlist components)</li>"
        "<li>Guaranteed spot interrupt logic: <code>calculatePlaySchedules</code> poll ทุก <strong>1 วินาที</strong> ผ่าน <code>useQuery</code>, "
        "เช็ค <code>dayjs().isBetween(start, end)</code> &mdash; ความแม่นยำ ±2 วินาที</li>"
        "<li><code>pausePlayData</code> เป็น <strong>ตัวแปรตัวเดียว</strong> &mdash; กรณี nested guaranteed interrupts จะทำให้ creative เดิมหาย "
        "(SMIL standard ใช้ pause <em>queue/stack</em>)</li>"
        "<li>Guaranteed spot media หาย &rarr; <strong>silent failure</strong>: creative ที่โดน interrupt ค้าง pause ตลอด ไม่มี recovery</li>"
        "<li>Guaranteed spots ซ้อนกัน &rarr; <code>find()</code> เลือกตัวแรกเจอ ไม่มี priority logic</li>"
        "<li>มี 2 path แยกกันสร้าง guaranteed PlaySchedules (approval push + loop injection) &mdash; logic ซ้ำซ้อน</li>"
        "<li>Retry queue (สูงสุด 3 ครั้ง), spot rotation tracking, daypart gate</li>"
        "<li>ความซับซ้อนของ Player: scheduling logic <strong>3,500+ บรรทัด</strong> ใน <code>src/components/screen/device/schedule/</code></li>"
        "</ul>"
        "<p><strong>การจัดการ Offline (ปัจจุบัน)</strong></p>"
        "<ul>"
        "<li>ตรวจจับ offline: <code>fetch</code> error ที่ <code>err?.message === 'Load failed'</code></li>"
        "<li>เล่นจาก <code>localStorage</code> cache (schedules + playlists)</li>"
        "<li>ไม่มี graceful fallback: fresh boot + ไม่มี internet = <strong>จอดำ</strong></li>"
        "<li>ไม่มี checksum validation สำหรับ creative assets ที่ download</li>"
        "<li>Guaranteed spot ได้รับ approve ขณะ offline &rarr; Pusher push หาย ไม่มี buffer mechanism</li>"
        "</ul>"
    ))

    # BEP-2998: Impression Delivery Accuracy
    sections.append(warning_panel(
        "<p><strong>Impression Delivery Accuracy (Under-Delivery Problem)</strong> "
        '&mdash; <a href="https://100-stars.atlassian.net/browse/BEP-2998">BEP-2998</a> '
        '(Epic: <a href="https://100-stars.atlassian.net/browse/BEP-2134">BEP-2134</a>)</p>'
        "<ul>"
        "<li>กำหนด impression target 15 plays/hr &rarr; ระบบเล่น ~13-15 (<strong>under-delivery up to 13%</strong>)</li>"
        "<li>กำหนด 100 plays/day &rarr; ระบบเล่น ~90-100 (<strong>under-delivery up to 10%</strong>)</li>"
        "<li>สาเหตุ: <code>calculateAdDisplayCount</code> rounding + proportional allocation (<code>Math.ceil(adsAmount * ratio)</code>) ไม่สม่ำเสมอ</li>"
        "<li>Player-side: <code>decrementSchedulePlayCount</code> ใช้ mutex lock + PlayKey idempotency แต่ยัง race condition ได้</li>"
        "<li>DOOH industry เรียกปัญหานี้ว่า <strong>impression shortfall</strong> &mdash; "
        "แก้ด้วย <strong>campaign pacing algorithm</strong> + <strong>SOV (Share of Voice) allocation</strong></li>"
        "</ul>"
    ))

    # ── Current Architecture ──
    sections.append("<hr/>")
    sections.append("<h2>2. สถาปัตยกรรมปัจจุบัน (Current Architecture)</h2>")
    sections.append("<h3>2.1 Backend (tathep-platform-api)</h3>")

    sections.append(mermaid_diagram(
        load_diagram("03-1-backend-pipeline.mmd"),
        page_id=page_id,
    ))

    sections.append(expand_section("Backend Components (13 ไฟล์)",
        '<table>'
        '<tr><th>Component</th><th>File</th><th>Purpose</th></tr>'
        '<tr><td>PlaySchedule model</td><td><code>app/Models/PlaySchedule.ts</code></td><td>Status: WAITING&rarr;PLAYING&rarr;PLAYED, ประเภท: guaranteed/ROS/spot-rotation</td></tr>'
        '<tr><td>Screen model</td><td><code>app/Models/Billboard.ts</code></td><td>ownerTime/platformTime = SOV (Share of Voice) budget (วินาที/ชั่วโมง)</td></tr>'
        '<tr><td>Scheduling Engine</td><td><code>app/Jobs/PlayScheduleCalculate.ts</code></td><td>สร้าง per-screen jobs ทุก N นาที</td></tr>'
        '<tr><td>Per-screen calc</td><td><code>app/Jobs/PlayScheduleCalculatePerScreen.ts</code></td><td>สร้าง PlaySchedule rows สำหรับ 1 จอ</td></tr>'
        '<tr><td>Player-pull mode</td><td><code>app/Jobs/PlayScheduleRoundCreate.ts</code></td><td>POST /v2/play-schedules/request {amount: N}</td></tr>'
        '<tr><td>House content rotation</td><td><code>app/Services/PlayScheduleFrequencyService.ts</code></td><td>หมุนเวียน creative ของเจ้าของจอ + random jitter</td></tr>'
        '<tr><td>Campaign period</td><td><code>app/Services/PlaySchedulePeriodService.ts</code></td><td>Campaign ขายตรง: PER_HOUR/PER_DAY/custom avails</td></tr>'
        '<tr><td>Guaranteed service</td><td><code>app/Services/v2/PlayScheduleExclusiveService.ts</code></td><td>แทรก guaranteed spots ที่ทับ loop window ปัจจุบัน</td></tr>'
        '<tr><td>Guaranteed job</td><td><code>app/Jobs/PlayScheduleCreateByExclusive.ts</code></td><td>On-demand: BullMQ job ทำงานเมื่อ owner approve &rarr; สร้าง PlaySchedule + push ผ่าน Pusher</td></tr>'
        '<tr><td>Guaranteed model</td><td><code>app/Models/AdvertisementDisplayExclusive.ts</code></td><td>จองเวลาต่อจอ (startDateTime/endDateTime/timePerSlot)</td></tr>'
        '<tr><td>Guaranteed time window</td><td><code>app/Models/AdGroupDisplayTimeExclusive.ts</code></td><td>ช่วงเวลา guaranteed ระดับ AdGroup สำหรับแทรกใน loop</td></tr>'
        '<tr><td>Reservation check</td><td><code>app/Services/ServiceHelpers/checkIsBillboardsReserved.ts</code></td><td>ป้องกัน double-booking: ตรวจ overlap ก่อนสร้าง guaranteed avails</td></tr>'
        '<tr><td>Pusher service</td><td><code>app/Services/PusherPlayScheduleService.ts</code></td><td>Channel: play-schedule-{deviceCode}</td></tr>'
        '</table>'
    ))

    sections.append("<h3>2.2 Player (bd-vision-player)</h3>")
    sections.append(mermaid_diagram(
        load_diagram("03-2-player-architecture.mmd"),
        page_id=page_id,
    ))

    sections.append(expand_section("Player Features (8 รายการ)",
        '<table>'
        '<tr><th>Feature</th><th>Implementation</th><th>File</th></tr>'
        '<tr><td>ประเภท Schedule</td><td><code>exclusive</code> (guaranteed spot), <code>continuous</code> (ขายตรง ROS), <code>frequency</code> (หมุนเวียน spot)</td><td><code>src/constants/schedule.constant.ts</code></td></tr>'
        '<tr><td>Loop rotation</td><td><code>(currentIndex + 1) % activeSchedules.length</code></td><td><code>screen.device.schedule.play.timeslot.component.tsx</code></td></tr>'
        '<tr><td>Guaranteed preempt</td><td><code>calculatePlaySchedules</code> (poll ทุก 1 วิ ผ่าน <code>useQuery</code>): '
        '<code>dayjs().isBetween(start, end)</code> &rarr; <code>setPausePlayData(current)</code> &rarr; เล่น guaranteed spot &rarr; '
        'จบแล้ว restore <code>pausePlayData</code>. ตัวแปรเดียว = ไม่รองรับ nested interrupt</td>'
        '<td><code>screen.device.schedule.play.component.tsx</code></td></tr>'
        '<tr><td>Retry queue</td><td>สูงสุด 3 ครั้ง, เก็บใน localStorage</td><td><code>screen.device.schedule.play.timeslot.component.tsx</code></td></tr>'
        '<tr><td>Media download</td><td>Tauri <code>plugin-upload</code> (native HTTP), ดาวน์โหลดทีละไฟล์</td><td><code>screen.device.schedule.setup.schedule-download.tsx</code></td></tr>'
        '<tr><td>File cleanup</td><td>ทุก 24 ชม. ช่วง off-hours, ลบแบบ LRU</td><td><code>src/services/file-cleanup.service.ts</code></td></tr>'
        '<tr><td>ตรวจจับ Offline</td><td><code>err?.message === "Load failed"</code></td><td><code>screen.device.schedule.component.tsx</code></td></tr>'
        '<tr><td>PoP (Proof of Play) retry</td><td>Tauri Store (<code>player.history.json</code>), batch 10 รายการ, ทุก 1 นาที</td><td><code>player-history.store.ts</code></td></tr>'
        '</table>'
    ))

    sections.append("<h3>2.3 Pusher Events</h3>")
    sections.append(expand_section("Pusher Events (6 events)",
        '<table>'
        '<tr><th>Event</th><th>Trigger</th><th>Player Action</th></tr>'
        '<tr><td><code>update-play-schedule</code></td><td>Scheduling engine loop เสร็จ</td><td>ดึง <code>GET /v2/play-schedules</code> ใหม่</td></tr>'
        '<tr><td><code>created-play-schedule</code></td><td>Player-pull job เสร็จ</td><td>ดึง schedules ใหม่</td></tr>'
        '<tr><td><code>approved-advertisement-exclusive</code></td><td>Guaranteed spot ได้รับ approve</td><td>แทรกทันที (ไม่ต้อง re-fetch)</td></tr>'
        '<tr><td><code>stop-advertisement</code></td><td>Creative ถูกยกเลิก</td><td>ลบออกจาก local schedule</td></tr>'
        '<tr><td><code>new/update/delete-play-schedule</code></td><td>Schedule CRUD</td><td>ดึง schedules ใหม่</td></tr>'
        '<tr><td><code>un-pair-screen</code></td><td>Device ถูก unpair</td><td>ล้างทั้งหมด กลับหน้า pair</td></tr>'
        '</table>'
    ))

    return "\n".join(sections)


def build_page_2(page_id: str) -> str:
    """Page 2: Proposed Architecture (3 mermaid — overview + daily schedule + proposed flow)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())

    # Architecture overview diagram (moved from Executive Summary)
    sections.append("<h2>ภาพรวมสถาปัตยกรรม (Architecture Overview)</h2>")
    sections.append(mermaid_diagram(
        load_diagram("01-proposed-architecture.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>ตัวอย่าง Daily Schedule</h3>")
    sections.append(info_panel(
        "<p>ตัวอย่าง billboard 1 จอ ตลอดวัน — แสดงสัดส่วนเวลาจริงระหว่าง priority levels ต่างๆ. "
        "<strong>P1-TK</strong> (แดง) กินเวลา 1 ชั่วโมงเต็ม, <strong>P1-ET</strong> (แดง) เป็น exact-time spot ที่เล่นตรงเวลา, "
        "<strong>P1-G</strong> (ฟ้า) กระจายตลอดวัน, <strong>P2-P4</strong> เติมช่วงที่เหลือ</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("01-2-daily-schedule.mmd"),
        page_id=page_id,
    ))
    sections.append(_gantt_legend_mini())

    sections.append("<hr/>")
    sections.append("<h2>สถาปัตยกรรมที่เสนอ: Backend-Driven Player</h2>")
    sections.append(info_panel(
        "<p><strong>แนวคิดหลัก:</strong> Backend ส่ง <strong>ordered screen schedule (loop sequence)</strong> แทนที่จะส่ง bag of creatives + rules. "
        "Player แค่เล่น <code>sequence[i++]</code> (Dumb Renderer pattern &mdash; มาตรฐาน DOOH)</p>"
    ))

    # Version Isolation Strategy
    sections.append("<h3>Version Isolation Strategy (v1/v2 แยกกันสมบูรณ์)</h3>")
    sections.append(warning_panel(
        "<p><strong>Architectural Decision:</strong> v2 เป็น <strong>new modules ใน repo เดิม</strong> "
        "&mdash; ไม่ reuse business logic จาก v1 เลย ทั้ง Player และ API</p>"
        "<p><strong>เหตุผล:</strong></p>"
        "<ul>"
        "<li><strong>Release isolation:</strong> deploy v2 ได้โดยไม่กระทบ v1 production &mdash; ทั้ง 2 version ทำงานพร้อมกันได้</li>"
        "<li><strong>Rollback safety:</strong> ถ้า v2 มีปัญหา สลับกลับ v1 ทันที เพราะ code + DB คนละชุด</li>"
        "<li><strong>Clean architecture:</strong> ไม่ต้อง workaround legacy schema หรือ backward compatibility</li>"
        "<li><strong>Migration path:</strong> เมื่อ v2 stable แล้วค่อย sunset v1 ทีละป้าย</li>"
        "</ul>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Layer</th><th>v1 (ปัจจุบัน)</th><th>v2 (ใหม่)</th><th>Shared?</th></tr>'
        '<tr><td><strong>Player repo</strong></td><td><code>bd-vision-player</code></td><td><code>bd-vision-player</code> (repo เดิม)</td><td>' + status_macro("SAME REPO", "Green") + '</td></tr>'
        '<tr><td><strong>Player modules</strong></td><td>existing components</td><td><strong>new modules ทั้งหมด</strong></td><td>' + status_macro("NO REUSE", "Red") + '</td></tr>'
        '<tr><td><strong>API repo</strong></td><td><code>tathep-platform-api</code></td><td><code>tathep-platform-api</code> (repo เดิม)</td><td>' + status_macro("SAME REPO", "Green") + '</td></tr>'
        '<tr><td><strong>API modules</strong></td><td>existing services/routes</td><td><strong>new services/routes ทั้งหมด</strong></td><td>' + status_macro("NO REUSE", "Red") + '</td></tr>'
        '<tr><td><strong>Database (API)</strong></td><td>current tables</td><td><strong>new tables/schema แยก</strong></td><td>' + status_macro("NO SHARE", "Red") + '</td></tr>'
        '<tr><td><strong>Database (Player)</strong></td><td>localStorage + Tauri Store</td><td><strong>new store format แยก</strong></td><td>' + status_macro("NO SHARE", "Red") + '</td></tr>'
        '<tr><td><strong>S3 Storage</strong></td><td>media files</td><td>media files (เดิม)</td><td>' + status_macro("SHARED", "Green") + '</td></tr>'
        '<tr><td><strong>Video Processing</strong></td><td><code>tathep-video-processing</code></td><td><code>tathep-video-processing</code> (เดิม)</td><td>' + status_macro("SHARED", "Green") + '</td></tr>'
        '<tr><td><strong>Infra</strong></td><td>ECS, CDN, Redis, Pusher</td><td>ECS, CDN, Redis, Pusher (เดิม)</td><td>' + status_macro("SHARED", "Green") + '</td></tr>'
        '</table>'
    )
    sections.append(note_panel(
        "<p><strong>ผลลัพธ์:</strong> v1 ทำงานบน API v1 + DB v1 / v2 ทำงานบน API v2 + DB v2. "
        "ป้ายแต่ละตัวสามารถเลือกใช้ v1 หรือ v2 ได้อิสระ &mdash; "
        "rollout ทีละป้าย (canary deployment) แล้ว sunset v1 เมื่อทุกป้ายอยู่บน v2.</p>"
    ))

    sections.append("<h3>สิ่งที่เปลี่ยน vs สิ่งที่คงเดิม</h3>")
    sections.append(info_panel(
        "<p><strong>หมายเหตุ:</strong> ตาม Version Isolation Strategy &mdash; v2 modules เขียนใหม่ทั้งหมด "
        "แม้ concept จะ <em>คล้าย</em> v1 แต่ <strong>ไม่ reuse code จาก v1</strong>. "
        "คอลัมน์ &quot;v1 Reference&quot; แสดงไว้เพื่ออ้างอิงแนวคิด ไม่ใช่ code ที่จะ reuse.</p>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Component</th><th>v1 Reference</th><th>v2 (New Module)</th><th>Change Type</th></tr>'
        '<tr><td>Scheduling Engine</td><td>PlayScheduleCalculate (cron 5 นาที)</td><td><strong>v2 Scheduling Engine:</strong> new cron + event-driven trigger + Ad Decisioning</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Per-screen calc</td><td>PlayScheduleCalculatePerScreen</td><td><strong>v2 PerScreenBuilder:</strong> สร้าง ordered ScreenSchedule</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Pusher events</td><td>6 event types, channel per device</td><td><strong>v2 Event Bus:</strong> typed events + version protocol + dedup</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Player API</td><td>GET /v2/play-schedules + /playlist-advertisements</td><td><strong>GET /v3/screen-schedule</strong> (new endpoint, new response format)</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Player scheduling</td><td>Loop rotation + guaranteed interrupt (3,500+ LOC)</td><td><strong>v2 Dumb Renderer:</strong> play <code>sequence[i++]</code></td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Player storage</td><td>localStorage (schedules + playlists)</td><td><strong>v2 Store:</strong> Tauri Store (3-tier playlist cache)</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Media download</td><td>Tauri plugin-upload (sequential, ไม่แยก SIM/BB)</td><td><strong>v2 Downloader:</strong> parallel download (network-aware: Broadband 5 / SIM 2-3 concurrent) + timeout + integrity check</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>PoP reporting</td><td>POST /v2/play-history + retry queue</td><td><strong>v2 Outbox:</strong> idempotency key + interrupt fields + guaranteed delivery</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td>Auth</td><td>x-device-code header</td><td><strong>v2 Auth:</strong> same concept (device code) แต่ new module + version header</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td><strong>Interrupt Controller</strong></td><td>N/A (ไม่มีใน v1)</td><td><strong>ใหม่:</strong> Lightweight IC สำหรับ P0/P1-TK/P1-ET</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td><strong>TK Booking API</strong></td><td>N/A</td><td><strong>ใหม่:</strong> Daypart Takeover booking + overlap check</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td><strong>Make-Good System</strong></td><td>N/A</td><td><strong>ใหม่:</strong> Compensation สำหรับ interrupted ads</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '<tr><td><strong>DB Schema</strong></td><td>v1 tables (PlaySchedule, etc.)</td><td><strong>v2 tables ใหม่ทั้งหมด</strong> (ScreenSchedule, TakeoverSchedule, etc.)</td><td>' + status_macro("NEW v2", "Blue") + '</td></tr>'
        '</table>'
    )

    sections.append("<h3>Shared Infrastructure (v1/v2 ใช้ร่วมกัน)</h3>")
    sections.append(info_panel(
        "<p><strong>Infrastructure layer</strong> ใช้ร่วมกันระหว่าง v1 และ v2 &mdash; "
        "แต่ <strong>application code ที่เรียกใช้ infra เป็น new modules ทั้งหมด</strong> (ไม่ reuse v1 code).</p>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Infrastructure</th><th>v1 ใช้อย่างไร</th><th>v2 ใช้อย่างไร</th><th>Sharing</th></tr>'
        '<tr><td><strong>BullMQ + Redis</strong></td><td>v1 cron job queues</td><td>v2 new job queues (แยก queue name)</td><td>' + status_macro("SHARED INFRA", "Green") + '</td></tr>'
        '<tr><td><strong>MySQL</strong></td><td>v1 tables (PlaySchedule, etc.)</td><td><strong>v2 new tables แยก</strong> (ScreenSchedule, etc.) &mdash; ไม่ share data กับ v1</td><td>' + status_macro("SEPARATE SCHEMA", "Yellow") + '</td></tr>'
        '<tr><td><strong>Redis (cache)</strong></td><td>v1 cache keys</td><td>v2 cache keys (แยก namespace/prefix)</td><td>' + status_macro("SHARED INFRA", "Green") + '</td></tr>'
        '<tr><td><strong>Pusher</strong></td><td>v1 event types</td><td>v2 new event types (typed + versioned)</td><td>' + status_macro("SHARED INFRA", "Green") + '</td></tr>'
        '<tr><td><strong>AdonisJS</strong></td><td>v1/v2 routes (/play-schedules)</td><td>v3 routes (/v3/screen-schedule) &mdash; new controllers + services</td><td>' + status_macro("SAME FRAMEWORK", "Green") + '</td></tr>'
        '<tr><td><strong>S3 + CDN</strong></td><td>media storage + delivery</td><td>media storage + delivery (เดิม)</td><td>' + status_macro("SHARED", "Green") + '</td></tr>'
        '<tr><td><strong>Video Processing</strong></td><td>tathep-video-processing</td><td>tathep-video-processing (เดิม)</td><td>' + status_macro("SHARED", "Green") + '</td></tr>'
        '<tr><td><strong>Tauri runtime</strong></td><td>v1 player app</td><td>v2 player app (new entry point)</td><td>' + status_macro("SAME RUNTIME", "Green") + '</td></tr>'
        '<tr><td><strong>ECS / Deploy</strong></td><td>v1 containers</td><td>v2 containers (อาจ feature flag หรือ separate service)</td><td>' + status_macro("SHARED INFRA", "Green") + '</td></tr>'
        '</table>'
    )

    return "\n".join(sections)


def build_page_3(page_id: str) -> str:
    """Page 3: Key Flows (6 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Flow หลัก (Key Flows)</h2>")

    sections.append("<h3>Flow A: เล่นปกติ Online (Happy Path)</h3>")
    sections.append(mermaid_diagram(
        load_diagram("05-1-flow-normal.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>Flow B: เน็ตหลุด &rarr; Offline &rarr; เชื่อมต่อใหม่</h3>")
    sections.append(mermaid_diagram(
        load_diagram("05-2-flow-network-drop.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>Flow C: Interrupt แบบ Guaranteed Spot (Online)</h3>")
    sections.append(warning_panel(
        "<p><strong>ระบบเดิมมี 2 เส้นทางสำหรับ guaranteed spots (เดิมเรียก exclusive):</strong></p>"
        "<ul>"
        "<li><strong>เส้นทาง 1 (ตอน approve):</strong> Owner approve &rarr; BullMQ <code>PlayScheduleCreateByExclusive</code> job &rarr; "
        "สร้าง PlaySchedule rows (type=EXCLUSIVE, createdBy=EXCLUSIVE_APPROVED) &rarr; "
        "Pusher <code>approved-advertisement-exclusive</code> พร้อม payload เต็ม &rarr; Player inject ทันที</li>"
        "<li><strong>เส้นทาง 2 (ระหว่าง loop):</strong> <code>PlayScheduleExclusiveService</code> เช็ค <code>AdGroupDisplayTimeExclusive</code> "
        "ที่ overlap กับ loop window ปัจจุบัน &rarr; สร้าง PlaySchedule rows (createdBy=PLAYER_REQUEST)</li>"
        "</ul>"
        "<p><strong>ที่เสนอให้ปรับ:</strong> Ad Decisioning Engine จัดการทั้ง 2 เส้นทาง &mdash; "
        "guaranteed spots ถูก inject เข้า ordered sequence ที่ตำแหน่ง <code>play_at</code> ที่แน่นอนตั้งแต่แรก. "
        "Player ไม่ต้องมี guaranteed interrupt logic อีกต่อไป.</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("05-3-flow-exclusive.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>Flow D: เปิดเครื่องใหม่ ไม่มี Cache (Fresh Boot)</h3>")
    sections.append(mermaid_diagram(
        load_diagram("05-4-flow-fresh-boot.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>Flow E: เหมาช่วงเวลา (Daypart Takeover)</h3>")
    sections.append(info_panel(
        "<p><strong>Daypart Takeover (เหมา time block):</strong> ลูกค้าซื้อช่วงเวลาทั้งหมด (เช่น 08:00-09:00) "
        "วน ad เดียวไม่หยุด ไม่มี ad อื่นแทรกได้ยกเว้น P0 Emergency. "
        "Billing: <strong>CPT (Cost Per Time)</strong> — flat rate ต่อ time block. "
        'ใช้แนวคิดจาก <a href="https://docs.broadsign.com/broadsign-control/latest/en/settings-section.html">'
        "Broadsign Day Part Switch Behavior</a> (configurable interrupt at boundaries).</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("05-5-flow-takeover.mmd"),
        page_id=page_id,
    ))

    sections.append("<h3>Flow F: เล่นตรงเวลา (Exact-Time Spot)</h3>")
    sections.append(info_panel(
        "<p><strong>Exact-Time Spot:</strong> Ad ต้องเล่นตรงเวลาที่กำหนด (±5 วินาที). "
        "Interrupt Controller จะหยุด creative ที่กำลังเล่น (P2-P4 เท่านั้น) แล้วเล่น ET spot ทันที. "
        "Billing: <strong>Flat per spot</strong>. "
        "Ad ที่โดน interrupt จะได้ <strong>make-good</strong> compensation ใน cycle ถัดไป.</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("05-6-flow-exact-time.mmd"),
        page_id=page_id,
    ))

    return "\n".join(sections)


def build_page_4(page_id: str) -> str:
    """Page 4: Technical Design — Algorithm & Models (0 mermaid, 4 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Technical Design: Algorithm และ Models</h2>")

    # Ad Decisioning Algorithm
    sections.append("<h3>Ad Decisioning Algorithm (ขั้นตอนจัดลำดับ Ad)</h3>")
    sections.append(note_panel(
        "<p><strong>Version Isolation:</strong> ทุก model และ service ในหน้านี้เป็น <strong>v2 new modules</strong> &mdash; "
        "ไม่ reuse code จาก v1. v1 references (เช่น <code>PlayScheduleCalculatePerScreen</code>) "
        "แสดงไว้เพื่ออ้างอิงแนวคิดเดิม ไม่ใช่ code ที่จะ extend.</p>"
    ))
    sections.append(note_panel(
        "<p><strong>หลักการสำคัญ:</strong> v2 Ad Decisioning Engine ทำหน้าที่เดียวกับ v1 <code>PlayScheduleCalculatePerScreen</code> "
        "แต่เขียนใหม่ทั้งหมด &mdash; รับ campaign data แล้วสร้าง <strong>ordered loop sequence</strong> โดยตรง.</p>"
        "<p><strong>Guaranteed spots (เดิมเรียก exclusive):</strong> v1 จัดการด้วย 2 เส้นทางแยกกัน "
        "(<code>PlayScheduleCreateByExclusive</code> ตอน approve + <code>PlayScheduleExclusiveService</code> ระหว่าง loop). "
        "v2 Ad Decisioning Engine <strong>รวมทั้ง 2 เส้นทาง</strong> &mdash; guaranteed spots ถูก inject ที่ตำแหน่ง <code>play_at</code> "
        "ตรงจุดใน sequence. v1 concept <code>checkIsBillboardsReserved</code> ถูก reimplemented ใน v2 overlap checker. "
        "Billing ใช้ <code>exclusiveMultiplier</code> (env: <code>ADVERTISEMENT_EXCLUSIVE_MULTIPLIER</code>).</p>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Priority</th><th>DOOH Type</th><th>Interrupt?</th><th>Scheduling</th><th>Billing</th></tr>'
        '<tr><td><strong>P0</strong></td><td>Emergency</td><td>' + status_macro("YES — all", "Red") + '</td><td>แจ้งเตือนระบบ, unpair, maintenance</td><td>N/A</td></tr>'
        '<tr><td><strong>P1-TK</strong></td><td>Daypart Takeover</td><td>' + status_macro("YES — boundaries", "Red") + '</td><td>เหมา time block วน ad เดียว (TK_START → loop → TK_END)</td><td>CPT (flat/time block)</td></tr>'
        '<tr><td><strong>P1-ET</strong></td><td>Exact-Time Spot</td><td>' + status_macro("YES — P2-P4", "Red") + '</td><td>เล่นตรงเวลา ±5s tolerance</td><td>Flat per spot</td></tr>'
        '<tr><td><strong>P1-G</strong></td><td>Guaranteed Spot</td><td>' + status_macro("NO — pre-positioned", "Green") + '</td><td>จอง time slot เล่นตรงตำแหน่ง <code>play_at</code> ใน sequence</td><td><code>exclusiveMultiplier</code></td></tr>'
        '<tr><td><strong>P1-DG</strong></td><td>Dayparted Guaranteed</td><td>' + status_macro("NO — pre-positioned", "Green") + '</td><td>Guaranteed N plays กระจายใน <code>DaypartWindow</code> ที่กำหนด (center-offset distribution)</td><td><code>exclusiveMultiplier</code></td></tr>'
        '<tr><td><strong>P2</strong></td><td>Direct-Sold ROS</td><td>' + status_macro("NO", "Green") + '</td><td>Campaign creatives ตาม date-range (run-of-schedule) รองรับ <code>daypartWindows</code> (เล่นเฉพาะใน windows)</td><td>Standard rate</td></tr>'
        '<tr><td><strong>P3</strong></td><td>Spot Buy / Programmatic</td><td>' + status_macro("NO", "Green") + '</td><td>Campaign ตาม impression target (อนาคต: RTB ผ่าน SSP)</td><td>Standard / CPM</td></tr>'
        '<tr><td><strong>P4</strong></td><td>House / Filler</td><td>' + status_macro("NO", "Green") + '</td><td>Content default ของเจ้าของจอ (house loop)</td><td>N/A</td></tr>'
        '</table>'
    )
    sections.append(note_panel(
        "<p><strong>กฎการ Interrupt:</strong></p>"
        "<ul>"
        "<li><strong>P0/P1-TK/P1-ET:</strong> Interrupt creative ปัจจุบันทันที → <strong>stop</strong> (ไม่ pause/resume) "
        '— แนวคิดจาก <a href="https://xibosignage.com/manual/en/layouts_interrupt">Xibo Interrupt Layout</a></li>'
        "<li><strong>P1-G/P2/P3/P4:</strong> รอ creative ปัจจุบันจบก่อน (no interrupt)</li>"
        "<li>หลัง interrupt: resume จาก <strong>next item</strong> ใน schedule (ไม่ restart creative ที่โดน interrupt)</li>"
        "<li>Ad ที่โดน interrupt ได้ <strong>make-good</strong> compensation ใน cycle ถัดไป (partial play ไม่นับ impression)</li>"
        "<li>Takeover ซ้อนกันไม่ได้ (1 time block = 1 owner)</li>"
        "</ul>"
    ))

    sections.append(tracked_code_block(
        "// Ad Decisioning Algorithm v3 (Timeline-Based + Interrupt-Capable)\n"
        "// Inspired by: SMIL <excl> + Broadsign Day Part Switch + Xibo Interrupt Layout\n"
        "// Addresses: BEP-2998 under-delivery + Daypart Takeover + Exact-Time Spot + Make-Good\n\n"
        "Input:\n"
        "  - playSchedules[]: from PerScreen calc (direct-sold ROS + spot buy)\n"
        "  - guaranteedSchedules[]: from AdGroupDisplayTimeExclusive (overlapping this loop)\n"
        "  - takeoverSchedules[]: from TakeoverSchedule (overlapping this loop)\n"
        "  - exactTimeSpots[]: from ExactTimeSpot (overlapping this loop)\n"
        "  - pendingMakeGoods[]: from MakeGoodRecord where compensated=false\n"
        "  - housePlaylist[]: from PlaylistAdvertisement (owner/filler content)\n"
        "  - screen: { ownerTime, platformTime }  // SOV budget (seconds/hour)\n"
        "  - loopDuration: 300  // seconds (5 min cron window)\n\n"
        "Step 0 (NEW): Reserve Exact-Time Spots (P1-ET)\n"
        "  for (const et of exactTimeSpots.sortBy('play_at')) {\n"
        "    timeline.reserveExact(et.play_at, et.tolerance_seconds, {\n"
        "      priority: 'P1-ET', interruptIfNeeded: true\n"
        "    })\n"
        "  }\n\n"
        "Step 1: Reserve Guaranteed Slots FIRST (P1-G)\n"
        "  timeline = createTimeline(loopStart, loopDuration)  // 300s\n"
        "  for (const g of guaranteedSchedules.sortBy('startDateTime')) {\n"
        "    if (!g.media?.file_url) { alertAdmin(g); continue }\n"
        "    timeline.reserve(g.play_at, g.duration, { priority: 'P1-G', ...g })\n"
        "  }\n\n"
        "Step 1.2 (NEW): Daypart-Aware Distribution (P1-DG + P2 with daypartWindows)\n"
        "  function distributeEvenlyInWindow(plays, window, creativeLength):\n"
        "    windowDuration = toSeconds(window.endTime) - toSeconds(window.startTime)\n"
        "    interval = windowDuration / plays           // gap between plays\n"
        "    offset   = interval / 2                     // center-offset (not front-loaded)\n"
        "    return Array.from({ length: plays }, (_, i) =>\n"
        "      window.startTime + offset + (interval * i)\n"
        "    )\n"
        "  // Example: window 10:00-10:30 (1800s), 4 plays, creative 30s\n"
        "  //   interval=450s, offset=225s → plays at 10:03:45, 10:11:15, 10:18:45, 10:26:15\n"
        "  for (const dg of daypartGuaranteedSchedules) {\n"
        "    activeWindows = dg.daypartWindows.filter(w => w.isActiveOn(loopDate))\n"
        "    playTimes = activeWindows.flatMap(w =>\n"
        "      distributeEvenlyInWindow(dg.playsPerWindow(w), w, dg.creative_duration)\n"
        "    )\n"
        "    playTimes.forEach(t => timeline.reserve(t, dg.creative_duration, { priority: 'P1-DG' }))\n"
        "  }\n\n"
        "Step 1.5 (NEW): Reserve Takeover Blocks (P1-TK)\n"
        "  for (const tk of takeoverSchedules.sortBy('start_time')) {\n"
        "    validate: no overlap with other TK (checkIsBillboardsReserved extended)\n"
        "    timeline.reserveTakeover(tk.start_time, tk.end_time, {\n"
        "      priority: 'P1-TK', loop: true, billing: 'CPT',\n"
        "      creative_code: tk.creative_code\n"
        "    })\n"
        "  }\n\n"
        "Step 2: Calculate SOV (Share of Voice) ratio for remaining avails\n"
        "  houseSOV = screen.ownerTime / (ownerTime + platformTime)\n"
        "  interleaveEvery = Math.round(1 / houseSOV)\n\n"
        "Step 2.5: Campaign Pacing (addresses BEP-2998 under-delivery)\n"
        "  for (const campaign of [...directSold, ...spotBuy]) {\n"
        "    target = campaign.impression_target\n"
        "    delivered = campaign.delivered_today\n"
        "    remaining = target - delivered\n"
        "    pacing_rate = remaining / remaining_loops_today\n"
        "  }\n\n"
        "Step 3: Fill unreserved avails with campaign + house creatives\n"
        "  availableAvails = timeline.getUnreservedSlots()\n"
        "  campaignAds = [...directSold, ...spotBuy]  // P2 before P3\n"
        "  houseIndex = 0\n\n"
        "  for (const avail of availableAvails) {\n"
        "    while (avail.hasCapacity() && campaignAds.length > 0) {\n"
        "      avail.push(campaignAds.shift())  // campaign creative\n"
        "      if (avail.count % interleaveEvery === 0) {\n"
        "        avail.push(housePlaylist[houseIndex++ % housePlaylist.length])\n"
        "      }\n"
        "    }\n"
        "  }\n\n"
        "Step 4: Fill remaining gaps with house content (P4 filler)\n"
        "  for (const emptyAvail of timeline.getEmptySlots()) {\n"
        "    emptyAvail.push(housePlaylist[houseIndex++ % housePlaylist.length])\n"
        "  }\n\n"
        "Step 5: Flatten timeline → ordered loop sequence\n"
        "  sequence = timeline.flatten()  // chronological order\n"
        "  sequence.forEach((item, i) => item.sequence_no = i + 1)\n\n"
        "Step 5.5 (NEW): Insert Make-Good Items\n"
        "  for (const mg of pendingMakeGoods) {\n"
        "    if (!mg.campaign.isValid()) { mg.skip(); continue }  // expired → log for reconcile\n"
        "    // Insert as first item after guaranteed/takeover slots\n"
        "    sequence.insertAfterReserved(mg.toScheduleItem())\n"
        "    mg.markCompensated()\n"
        "  }\n\n"
        "Step 6: Version + persist\n"
        "  version = (lastVersion for this device) + 1\n"
        "  Save ScreenSchedule { version, tier: 'live', items: sequence }\n"
        "  Mark previous 'live' schedule as 'replaced'\n\n"
        "Output:\n"
        "  ScreenSchedule v42 with ordered items[]\n"
        "  Player plays: items[0] → items[1] → items[2] → ...\n"
        "  P1-G items are pre-positioned in sequence (no interrupt needed)\n"
        "  P1-TK/P1-ET items trigger Interrupt Controller (real-time interrupt)\n"
        "  Make-good items compensate interrupted ads",
        "typescript", "Ad Decisioning Algorithm v3",
        collapse=True,
    ))

    # New Data Models
    sections.append("<h3>v2 Data Models (New DB Schema — ไม่ share กับ v1)</h3>")
    sections.append(tracked_code_block(
        "// NEW: ScreenSchedule model (app/Models/ScreenSchedule.ts)\n"
        "interface ScreenSchedule {\n"
        "  id: number\n"
        "  device_code: string\n"
        "  tier: 'live' | 'buffer' | 'fallback'\n"
        "  version: number          // monotonically increasing per device\n"
        "  valid_from: DateTime\n"
        "  valid_until: DateTime\n"
        "  status: 'active' | 'expired' | 'replaced'\n"
        "  created_at: DateTime\n"
        "}\n\n"
        "// NEW: ScreenScheduleItem model (app/Models/ScreenScheduleItem.ts)\n"
        "interface ScreenScheduleItem {\n"
        "  id: number\n"
        "  screen_schedule_id: number\n"
        "  sequence_no: number      // ordered by backend\n"
        "  play_schedule_code: string | null  // link to existing PlaySchedule\n"
        "  advertisement_code: string\n"
        "  creative_code: string    // creative asset identifier\n"
        "  duration_seconds: number\n"
        "  type: 'campaign' | 'house'  // campaign = sold inventory, house = filler\n"
        "  priority: 'guaranteed' | 'direct' | 'spot' | 'house'\n"
        "  play_at: DateTime | null  // for guaranteed/exact-time: exact time\n"
        "  interrupt_capable: boolean  // P1-TK/P1-ET = true, others = false\n"
        "}\n\n"
        "// NEW: TakeoverSchedule model (app/Models/TakeoverSchedule.ts)\n"
        "interface TakeoverSchedule {\n"
        "  id: number\n"
        "  device_code: string\n"
        "  advertisement_code: string\n"
        "  creative_code: string\n"
        "  start_time: DateTime      // e.g. 08:00:00\n"
        "  end_time: DateTime        // e.g. 09:00:00\n"
        "  status: 'booked' | 'active' | 'completed' | 'cancelled'\n"
        "  billing_type: 'CPT'       // Cost Per Time — flat rate per block\n"
        "  created_at: DateTime\n"
        "}\n\n"
        "// NEW: ExactTimeSpot model (app/Models/ExactTimeSpot.ts)\n"
        "interface ExactTimeSpot {\n"
        "  id: number\n"
        "  device_code: string\n"
        "  play_schedule_code: string\n"
        "  play_at: DateTime          // exact time to play\n"
        "  tolerance_seconds: number  // default: 5\n"
        "  billing_type: 'flat'       // flat per spot\n"
        "}\n\n"
        "// NEW: MakeGoodRecord model (app/Models/MakeGoodRecord.ts)\n"
        "interface MakeGoodRecord {\n"
        "  id: number\n"
        "  device_code: string\n"
        "  advertisement_code: string\n"
        "  interrupted_at: DateTime\n"
        "  play_duration_seconds: number  // how much played before interrupt\n"
        "  interrupt_reason: 'P0_emergency' | 'TK_start' | 'TK_end' | 'P1_exact_time'\n"
        "  compensated: boolean\n"
        "  compensated_at: DateTime | null\n"
        "}\n\n"
        "// NEW: DaypartWindow model (app/Models/DaypartWindow.ts)\n"
        "interface DaypartWindow {\n"
        "  id: number\n"
        "  ad_group_code: string\n"
        "  start_time: string           // HH:mm e.g. '08:00'\n"
        "  end_time:   string           // HH:mm e.g. '12:00' (must > start_time)\n"
        "  days_of_week: number[]       // 0=Sun..6=Sat, empty=ทุกวัน\n"
        "  makegood_preference: 'same_window_only' | 'same_day_flexible' | 'credit_preferred'\n"
        "  // Validation: end_time > start_time, within billboard operating_hours\n"
        "  // Production range: 06:00–22:00 (no overnight)\n"
        "}",
        "typescript", "New Models",
        collapse=True,
    ))

    sections.append(tracked_code_block(
        "// NEW: Ad Decisioning Engine (app/Services/AdDecisioningService.ts)\n"
        "// Called AFTER PlayScheduleCalculatePerScreen generates PlaySchedule rows\n\n"
        "class AdDecisioningService {\n"
        "  async buildSchedule(\n"
        "    screenCode: string,\n"
        "    playSchedules: PlaySchedule[],   // from cron calculation\n"
        "    housePlaylist: PlaylistAdvertisement[],  // house/filler content\n"
        "    screen: Billboard\n"
        "  ): Promise<ScreenSchedule> {\n"
        "    // 1. Sort campaign creatives by priority/time (P1 > P2 > P3)\n"
        "    // 2. Interleave house content based on SOV ratio (ownerTime/platformTime)\n"
        "    // 3. Insert guaranteed spots at their exact play_at position\n"
        "    // 4. Apply campaign pacing (BEP-2998: even impression distribution)\n"
        "    // 5. Assign sequence_no (1, 2, 3, ...)\n"
        "    // 6. Set valid_from/valid_until from loop window\n"
        "    // 7. Increment version (per device)\n"
        "    // 8. Create ScreenSchedule + ScreenScheduleItem rows\n"
        "    // 9. Mark previous 'live' schedule as 'replaced'\n"
        "  }\n\n"
        "  async buildBufferSchedule(\n"
        "    screenCode: string,\n"
        "    hoursAhead: number = 4\n"
        "  ): Promise<ScreenSchedule> {\n"
        "    // Pre-generate next N hours of schedule for offline buffer\n"
        "  }\n\n"
        "  async buildFallbackSchedule(\n"
        "    screenCode: string\n"
        "  ): Promise<ScreenSchedule> {\n"
        "    // House content only, loopable, rarely changes\n"
        "  }\n"
        "}",
        "typescript", "Ad Decisioning Engine Service",
        collapse=True,
    ))

    # New API Endpoint
    sections.append("<h3>v2 API Endpoint (New Routes — แยกจาก v1)</h3>")
    sections.append(tracked_code_block(
        "// GET /v3/screen-schedule?tier=live&since_version=41\n"
        "// Response:\n"
        "{\n"
        '  "version": 42,\n'
        '  "tier": "live",\n'
        '  "full": false,             // true if gap > 3 versions (full replace)\n'
        '  "valid_from": "2026-02-20T14:00:00+07:00",\n'
        '  "valid_until": "2026-02-20T14:10:00+07:00",\n'
        '  "items": [\n'
        "    {\n"
        '      "sequence_no": 1,\n'
        '      "advertisement_code": "AD-xxx",\n'
        '      "creative_code": "CR-xxx",\n'
        '      "creative_url": "https://cdn.../video.mp4",\n'
        '      "creative_checksum": "a1b2c3d4...",  // MD5 for validation\n'
        '      "duration_seconds": 15,\n'
        '      "type": "campaign",\n'
        '      "priority": "direct",\n'
        '      "interrupt_capable": false\n'
        "    },\n"
        "    {\n"
        '      "sequence_no": 5,\n'
        '      "advertisement_code": "AD-tk-001",\n'
        '      "creative_code": "CR-tk-001",\n'
        '      "creative_url": "https://cdn.../takeover.mp4",\n'
        '      "duration_seconds": 30,\n'
        '      "type": "takeover",\n'
        '      "priority": "P1-TK",\n'
        '      "interrupt_capable": true,\n'
        '      "takeover_id": 42,\n'
        '      "takeover_start": "2026-02-20T08:00:00+07:00",\n'
        '      "takeover_end": "2026-02-20T09:00:00+07:00"\n'
        "    },\n"
        "    ...\n"
        "  ],\n"
        '  "creative_manifest": [\n'
        '    {\n'
        '      "creative_code": "CR-xxx",\n'
        '      "url": "https://cdn.../vp/{videoId}/{width}x{height}.mp4",\n'
        '      "checksum": "a1b2c3d4...",\n'
        '      "size_bytes": 734003,\n'
        '      "width": 352,            // billboard actual resolution\n'
        '      "height": 672\n'
        '    }\n'
        "  ],\n"
        '  "pending_takeovers": [\n'
        '    { "takeover_id": 42, "start": "08:00:00", "end": "09:00:00", "creative_code": "CR-tk-001" }\n'
        "  ],\n"
        '  "exact_time_spots": [\n'
        '    { "play_at": "2026-02-20T14:30:00+07:00", "tolerance_seconds": 5, "creative_code": "CR-et-001" }\n'
        "  ]\n"
        "}",
        "json", "API Response Format",
        collapse=True,
    ))

    return "\n".join(sections)


def build_page_5(page_id: str) -> str:
    """Page 5: Technical Design — Player Components (5 mermaid, 4 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Technical Design: Player Components</h2>")
    sections.append(note_panel(
        "<p><strong>Version Isolation:</strong> ทุก component ในหน้านี้เป็น <strong>v2 player new modules</strong> &mdash; "
        "เขียนใหม่ทั้งหมดใน <code>bd-vision-player</code> repo เดิม ไม่ reuse code จาก v1. "
        "v2 player ใช้ <strong>DB schema ใหม่แยก</strong> ทั้งฝั่ง local store และ API.</p>"
    ))

    # 3-Tier Playlist Cache
    sections.append("<h3>ระบบ Cache 3 ชั้น (3-Tier Playlist Cache)</h3>")
    sections.append(mermaid_diagram(
        load_diagram("06-4-three-tier-cache.mmd"),
        page_id=page_id,
    ))

    # Player State Machine
    sections.append("<h3>Player State Machine</h3>")
    sections.append(mermaid_diagram(
        load_diagram("06-5-state-machine.mmd"),
        page_id=page_id,
    ))
    sections.append(warning_panel(
        "<p><strong>กฎสำคัญ:</strong></p>"
        "<ul>"
        "<li>ทุก state ต้องมีอะไรแสดงเสมอ. <strong>จอดำ (black screen) ยอมรับไม่ได้เด็ดขาด.</strong></li>"
        "<li><strong>INTERRUPTED</strong> เป็น transient state — หยุด creative ปัจจุบัน → เล่น interrupt content → resume item ถัดไป. "
        "Trigger: P0 emergency, P1-TK boundary, P1-ET ±5s. ดู §6.10 Interrupt Controller</li>"
        "</ul>"
    ))

    # PoP Reporting (Outbox/Inbox)
    sections.append("<h3>ระบบรายงาน PoP (Outbox/Inbox)</h3>")
    sections.append(error_panel(
        "<p><strong>ปัญหา 1 (Player &rarr; Backend): Duplicate PoP (Proof of Play)</strong><br/>"
        "Player POST <code>/v2/play-history</code> &rarr; timeout &rarr; retry &rarr; backend ได้ 2 รายการ สำหรับ creative เดียวกัน</p>"
        "<p><strong>ปัญหา 2 (Backend &rarr; Player): Missed Pusher Events</strong><br/>"
        "Pusher disconnect 30 วิ &rarr; reconnect &rarr; events ระหว่างนั้นหายไป &rarr; Player ไม่รู้ว่ามี schedule ใหม่</p>"
        "<p><strong>ปัญหา 3 (Backend &rarr; Player): Duplicate Pusher Events</strong><br/>"
        "Pusher ส่ง event ซ้ำ (at-least-once) &rarr; player process ซ้ำ &rarr; fetch ซ้ำ &rarr; เสีย bandwidth</p>"
    ))
    sections.append(info_panel(
        "<p><strong>แนวทางแก้:</strong> Outbox (Player&rarr;Backend) + Inbox (Backend&rarr;Player)</p>"
    ))

    sections.append("<h4>Player Outbox (PoP Reporting)</h4>")
    sections.append(mermaid_diagram(
        load_diagram("06-6a-outbox.mmd"),
        page_id=page_id,
    ))
    sections.append(tracked_code_block(
        "// TypeScript interface\n"
        "interface OutboxItem {\n"
        "  id: string              // UUID — idempotency key\n"
        "  type: 'play_history' | 'diagnostic'\n"
        "  payload: PlayHistoryPayload | DiagnosticPayload\n"
        "  status: 'pending' | 'sent' | 'acked'\n"
        "  retry_count: number\n"
        "  created_at: string      // ISO 8601\n"
        "}\n\n"
        "// Flush cycle (existing 1-min interval):\n"
        "// 1. Read all 'pending' items from Tauri Store\n"
        "// 2. Batch POST /v2/play-history with X-Idempotency-Key header\n"
        "// 3. On 200 OK → mark 'acked', store ack_id\n"
        "// 4. On timeout/error → keep 'pending', retry_count++\n"
        "// 5. retry_count > 10 → mark 'failed', log diagnostic (increased from current 3)\n"
        "// 6. Cleanup: remove 'acked' items older than 24h",
        "typescript", "Outbox Interface",
        collapse=True,
    ))

    sections.append("<h4>Player Inbox (Schedule Sync)</h4>")
    sections.append(mermaid_diagram(
        load_diagram("06-6b-inbox.mmd"),
        page_id=page_id,
    ))
    sections.append(tracked_code_block(
        "// TypeScript implementation\n"
        "function handlePlaylistUpdated(event: PusherEvent) {\n"
        "  const { event_id, version } = event\n\n"
        "  // Dedup: check if already processed\n"
        "  if (inbox.has(event_id) || version <= localVersion) {\n"
        "    return // skip duplicate\n"
        "  }\n\n"
        "  // Gap detection\n"
        "  if (version > localVersion + 3) {\n"
        "    // Too many missed events → full re-fetch\n"
        "    fetchFullPlaylist()\n"
        "  } else if (version > localVersion + 1) {\n"
        "    // Small gap → delta fetch\n"
        "    fetchDeltaPlaylist(localVersion)\n"
        "  } else {\n"
        "    // Normal: version = localVersion + 1\n"
        "    fetchDeltaPlaylist(localVersion)\n"
        "  }\n\n"
        "  inbox.add(event_id) // keep last 100\n"
        "}",
        "typescript", "Inbox Deduplication Code",
        collapse=True,
    ))

    # Version Protocol
    sections.append("<h3>Version Protocol</h3>")
    sections.append(mermaid_diagram(
        load_diagram("06-7-version-protocol.mmd"),
        page_id=page_id,
    ))

    # PoP Deduplication
    sections.append("<h3>PoP Deduplication (Idempotency ฝั่ง Backend)</h3>")
    sections.append(tracked_code_block(
        "// Backend: PlayHistoryController\n"
        "async store({ request }: HttpContextContract) {\n"
        "  const idempotencyKey = request.header('X-Idempotency-Key')\n\n"
        "  if (idempotencyKey) {\n"
        "    // Check Redis first (fast path, TTL 24h)\n"
        "    const existing = await Redis.get(`play_history:idem:${idempotencyKey}`)\n"
        "    if (existing) {\n"
        "      return { status: 'already_processed', ack_id: existing }\n"
        "    }\n"
        "  }\n\n"
        "  const history = await PlayHistory.create(payload)\n\n"
        "  if (idempotencyKey) {\n"
        "    await Redis.setex(`play_history:idem:${idempotencyKey}`, 86400, history.code)\n"
        "  }\n\n"
        "  return { status: 'created', ack_id: history.code }\n"
        "}",
        "typescript", "Backend Idempotency Check",
        collapse=True,
    ))

    # Media Cache Lifecycle
    sections.append("<h3>Media Cache Lifecycle (v2 Downloader — แก้ bottleneck จาก v1)</h3>")
    sections.append(info_panel(
        "<p><strong>หลักการ:</strong> Player download creative <strong>ครั้งเดียว</strong> แล้วเล่นจาก local cache ตลอด "
        "&mdash; ไม่ download ซ้ำทุกรอบ ประหยัด bandwidth &gt; 98%</p>"
    ))
    sections.append(warning_panel(
        "<p><strong>v1 Bottleneck ที่ v2 ต้องแก้:</strong></p>"
        "<ul>"
        "<li><strong>Sequential download:</strong> v1 ดาวน์โหลดทีละไฟล์ (<code>for...of</code> + <code>await</code>) "
        "&rarr; v2 ต้องรองรับ <strong>parallel download (3-5 concurrent)</strong></li>"
        "<li><strong>ไม่มี timeout:</strong> v1 Tauri <code>download()</code> ไม่มี timeout &mdash; download ค้าง = block ทุกอย่าง "
        "&rarr; v2 ต้องมี <strong>timeout 30s + retry 3 ครั้ง</strong></li>"
        "<li><strong>ไม่มี integrity check:</strong> v1 ใช้ <code>exists(filePath)</code> เช็คว่ามีไฟล์ &mdash; partial download นับว่ามี "
        "&rarr; v2 ต้องมี <strong>MD5 checksum validation</strong></li>"
        "<li><strong>ไม่มี download retry:</strong> v1 download ล้มเหลว = ข้ามเลย รอ schedule refresh "
        "&rarr; v2 ต้องมี <strong>retry queue ระดับ download</strong></li>"
        "<li><strong>ไม่รู้จักประเภท network:</strong> v1 ไม่แยก SIM กับ Broadband &mdash; ใช้ strategy เดียวกันทุกสถานที่ "
        "&rarr; v2 ต้อง <strong>ปรับ concurrency + timeout ตามประเภท internet</strong></li>"
        "</ul>"
        "<p><strong>ข้อมูล file size จาก production (Feb 2026):</strong> video avg = <strong>10.1 MB</strong>, "
        "74% อยู่ในช่วง 0-10 MB, max 99.7 MB</p>"
    ))

    # Parallel Download & Network Strategy
    sections.append("<h4>v2 Parallel Download Strategy</h4>")
    sections.append(info_panel(
        "<p><strong>หลักการ:</strong> v2 downloader ดาวน์โหลด <strong>หลายไฟล์พร้อมกัน (parallel)</strong> "
        "แทนที่จะรอทีละไฟล์แบบ v1. จำนวน concurrent downloads ปรับตาม <strong>ประเภท internet ของสถานที่</strong>.</p>"
    ))
    sections.append("""<table>
<tr><th>Network Type</th><th>Bandwidth (ประมาณ)</th><th>Concurrent Downloads</th><th>Timeout/file</th><th>Use Case</th></tr>
<tr><td><strong>Broadband</strong> (Fiber/Cable)</td><td>50-100+ Mbps</td><td><strong>5 concurrent</strong></td><td>30s</td><td>ป้ายในอาคาร, ห้าง, สำนักงาน</td></tr>
<tr><td><strong>Net SIM</strong> (4G/5G cellular)</td><td>5-30 Mbps (แปรผัน)</td><td><strong>2-3 concurrent</strong></td><td>60s</td><td>ป้ายริมถนน, จุดที่ไม่มี fixed line</td></tr>
</table>""")

    sections.append('<h4>Download Time Estimate (ตัวอย่าง 10 ads, avg 10 MB/file)</h4>')
    sections.append("""<table>
<tr><th>Scenario</th><th>v1 Sequential</th><th>v2 Parallel (Broadband)</th><th>v2 Parallel (SIM)</th></tr>
<tr><td>Download 10 files (100 MB total)</td><td>~16s <em>(100Mbps)</em></td><td><strong>~4s</strong> (5 concurrent)</td><td><strong>~12s</strong> (3 concurrent, 20Mbps)</td></tr>
<tr><td>Download 10 files (100 MB total)</td><td>~80s <em>(10Mbps SIM)</em></td><td>&mdash;</td><td><strong>~28s</strong> (3 concurrent, 10Mbps)</td></tr>
<tr><td>Fresh boot (ทุกไฟล์ใหม่)</td><td>ต้องรอจนครบ → จอดำนาน</td><td><strong>เล่นได้เร็วกว่า 3-5x</strong></td><td><strong>เล่นได้เร็วกว่า 2-3x</strong></td></tr>
</table>""")
    sections.append(note_panel(
        "<p><strong>Network detection:</strong> Billboard แต่ละตัวจะมี <code>network_type</code> field "
        "(<code>&apos;broadband&apos;</code> | <code>&apos;sim&apos;</code>) ใน config &mdash; "
        "v2 downloader อ่านค่านี้ตอน boot แล้วปรับ concurrency + timeout อัตโนมัติ. "
        "สำหรับ SIM จะใช้ <strong>conservative strategy</strong> เพื่อไม่ให้ saturate link จนกระทบ PoP reporting และ Pusher events.</p>"
    ))

    sections.append(
        '<p>เมื่อ Player ได้รับ schedule ใหม่ จะสแกน <code>creative_manifest</code> '
        'แล้วทำตามขั้นตอนนี้:</p>'
    )
    sections.append("""<table>
<tr><th>ขั้นตอน</th><th>ทำอะไร</th><th>เงื่อนไข</th></tr>
<tr><td><strong>1. Diff</strong></td><td>เทียบ <code>creative_manifest</code> กับไฟล์ใน local cache</td><td>ทุกครั้งที่ได้ schedule ใหม่</td></tr>
<tr><td><strong>2. Download</strong></td><td>ดาวน์โหลด <strong>parallel</strong> เฉพาะ creative ที่ยังไม่มีหรือ checksum ไม่ตรง</td><td>concurrency ตาม network type (Broadband: 5, SIM: 2-3)</td></tr>
<tr><td><strong>3. Verify</strong></td><td>เทียบ MD5 checksum กับ <code>creative_checksum</code> จาก manifest</td><td>ถ้าไม่ตรง &rarr; re-download (retry max 3 ครั้ง)</td></tr>
<tr><td><strong>4. Play</strong></td><td>เล่นจาก local cache ทุก loop</td><td>ไม่ download ซ้ำ &mdash; เล่นได้ทันทีที่มี file ครบ</td></tr>
<tr><td><strong>5. Evict</strong></td><td>ลบ creative ที่ไม่อยู่ใน schedule ปัจจุบัน + buffer</td><td>Disk &gt; threshold หรือ cleanup cron 24h</td></tr>
</table>""")

    sections.append('<h4>กรณีที่ต้อง download ใหม่</h4>')
    sections.append("""<table>
<tr><th>กรณี</th><th>เหตุผล</th><th>การทำงาน</th></tr>
<tr><td>Creative ถูกแก้ไข</td><td>Checksum ไม่ตรงกับ cache</td><td>Download version ใหม่ ลบ version เก่า</td></tr>
<tr><td>Player boot ใหม่ + cache ถูกลบ</td><td>ไม่มีไฟล์ใน local</td><td>Download ทุกไฟล์ใน manifest</td></tr>
<tr><td>Disk เต็ม &rarr; eviction ลบไปแล้ว</td><td>Emergency cleanup ลบไฟล์เก่า</td><td>Download ใหม่เมื่อ schedule ต้องการ</td></tr>
<tr><td>ไฟล์ corrupt (checksum fail)</td><td>Download ไม่สมบูรณ์</td><td>Mark dirty &rarr; re-download next sync</td></tr>
</table>""")

    sections.append('<h4>Bandwidth Savings</h4>')
    sections.append(
        '<p>สมมติ 10 ads เฉลี่ย 10 MB ต่อไฟล์ (production avg), เล่น 75 loops/วัน:</p>'
    )
    sections.append("""<table>
<tr><th>Mode</th><th>คำนวณ</th><th>Bandwidth/วัน</th></tr>
<tr><td>ไม่มี cache (download ทุกรอบ)</td><td>10 ads &times; 75 loops &times; 10MB</td><td><strong>7.5 GB</strong></td></tr>
<tr><td><strong>มี cache (download ครั้งเดียว)</strong></td><td>10 ads &times; 1 ครั้ง &times; 10MB</td><td><strong>100 MB</strong></td></tr>
<tr><td colspan="2"><strong>ประหยัด</strong></td><td><strong>98.7%</strong></td></tr>
</table>""")
    sections.append(warning_panel(
        "<p><strong>ความสำคัญสำหรับ Net SIM:</strong> SIM data plan มีค่าใช้จ่ายต่อ GB สูงกว่า Broadband มาก. "
        "Cache strategy ช่วยลดจาก 7.5 GB/วัน เหลือ 100 MB/วัน &mdash; "
        "<strong>ลดค่า data ต่อป้าย ~98%</strong>. "
        "สำหรับป้ายที่ใช้ SIM เรื่อง bandwidth savings ยิ่งมีค่ามาก เพราะลดต้นทุน operational โดยตรง.</p>"
    ))
    sections.append(note_panel(
        "<p><strong>หมายเหตุ:</strong> ตัวเลขจริงจะต่ำกว่า 100 MB เพราะวันถัดไป creative ส่วนใหญ่ยังอยู่ใน cache "
        "(checksum เดิม &rarr; ไม่ download ใหม่) จะ download เฉพาะ creative ใหม่ที่เพิ่มเข้ามาเท่านั้น</p>"
    ))

    # Programmatic Integration Points
    sections.append("<h3>จุดเชื่อมต่อ Programmatic (pDOOH Roadmap)</h3>")
    sections.append(info_panel(
        "<p><strong>Scale 100-500 จอ:</strong> ยังไม่ต้อง SSP/DSP เต็มรูปแบบ แต่เตรียม integration points ไว้ "
        "ให้ pluggable เมื่อขยาย scale ในอนาคต. ไม่เพิ่ม tech stack ใหม่ &mdash; ใช้ AdonisJS + Redis + BullMQ เดิม.</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("06-9-pdooh-integration.mmd"),
        page_id=page_id,
    ))
    sections.append(
        '<table>'
        '<tr><th>Integration Point</th><th>Current</th><th>pDOOH Extension (Future)</th></tr>'
        '<tr><td><strong>P3 slot fill</strong></td><td>หมุนเวียน spot ภายใน (count-based)</td><td>SSP ad request &rarr; RTB auction &rarr; winning creative หรือ fallback</td></tr>'
        '<tr><td><strong>PoP reporting</strong></td><td>POST /v2/play-history</td><td>เพิ่ม: <code>impression_id</code>, <code>campaign_id</code>, <code>creative_id</code>, <code>viewability_score</code></td></tr>'
        '<tr><td><strong>Inventory avails</strong></td><td>N/A</td><td><code>GET /v2/avails?screen_id=X&amp;daypart=Y</code> &mdash; เปิด slot ว่างให้ SSP เห็น</td></tr>'
        '<tr><td><strong>Campaign pacing</strong></td><td>BEP-2998 fix (proportional พื้นฐาน)</td><td>กระจาย impression ให้สม่ำเสมอตลอด flight + จัดสรรตาม SOV</td></tr>'
        '<tr><td><strong>Fill rate tracking</strong></td><td>N/A</td><td>% ของ P3 avails ที่เติมด้วย programmatic vs house content</td></tr>'
        '<tr><td><strong>Audience estimation</strong></td><td>N/A</td><td>ส่ง <code>audience_est</code> (foot traffic / ช่วงเวลา) ใน ad request</td></tr>'
        '</table>'
    )

    # Creative Delivery Pipeline
    sections.append("<h3>Creative Delivery Pipeline (End-to-End Optimization)</h3>")
    sections.append(info_panel(
        "<p><strong>เป้าหมาย:</strong> ส่ง creative ที่ <strong>ขนาดเล็กที่สุดแต่คุณภาพตรงกับจอจริง</strong> ของแต่ละป้าย "
        "&mdash; ไม่ encode เกินความจำเป็น ไม่ download เกินจำเป็น ไม่เปลือง data โดยเฉพาะป้ายที่ใช้ SIM 4G/5G</p>"
        "<p><strong>3 layers ทำงานร่วมกัน:</strong></p>"
        "<ol>"
        "<li><strong>Resolution-Aware Encoding</strong> &mdash; encode ตาม resolution จริงของป้าย (ไม่ใช่ fixed 1080p เสมอ)</li>"
        "<li><strong>Encoding Optimization</strong> &mdash; strip audio, slow preset, codec upgrade</li>"
        "<li><strong>Network-Aware Download</strong> &mdash; parallel + concurrency ตามประเภท internet (อยู่ section ด้านบน)</li>"
        "</ol>"
    ))

    # Current pipeline analysis
    sections.append('<h4>สถานะปัจจุบัน (v1 Video Processing Pipeline)</h4>')
    sections.append("""<table>
<tr><th>Parameter</th><th>ค่าปัจจุบัน (runtime)</th><th>Config Source</th><th>v2 เปลี่ยน?</th></tr>
<tr><td>Codec</td><td>H.264 (<code>libx264</code>), profile high, level 4.1</td><td>Hardcoded</td><td>เหมือนเดิม (P3: ทดสอบ H.265)</td></tr>
<tr><td>CRF</td><td><strong>28</strong></td><td><code>FFMPEG_CRF</code> env var</td><td>เหมือนเดิม</td></tr>
<tr><td>Preset</td><td><strong><code>fast</code></strong></td><td><code>FFMPEG_PRESET</code> env var</td><td><strong>เปลี่ยนเป็น <code>slow</code></strong> (-5-10%)</td></tr>
<tr><td>Audio</td><td>AAC 128kbps <strong>ทุกไฟล์</strong></td><td><code>FFMPEG_AUDIO_BITRATE</code></td><td><strong>Strip (<code>-an</code>)</strong> (-10-20%)</td></tr>
<tr><td>Resolution</td><td><strong>Fixed per aspect ratio</strong> (16:9 &rarr; 1920&times;1080 เสมอ)</td><td><code>ASPECT_RATIO_RESOLUTIONS</code></td><td><strong>Per-billboard resolution</strong></td></tr>
<tr><td>FPS</td><td>Cap 30fps (input &gt; 60fps)</td><td><code>OUTPUT_FPS_CAP</code></td><td>เหมือนเดิม</td></tr>
<tr><td>Variant strategy</td><td>1 variant per aspect ratio (max 5)</td><td><code>requestedAspectRatios</code></td><td><strong>1 variant per unique resolution</strong></td></tr>
</table>""")
    sections.append(note_panel(
        "<p><strong>Key finding:</strong> v1 encode variant ตาม <strong>aspect ratio</strong> (16:9, 9:16, etc.) "
        "ที่ <strong>fixed resolution</strong> (เช่น 9:16 = 1080&times;1920 เสมอ). "
        "แต่ป้ายจริง 9:16 อาจจะแค่ 352&times;672 &mdash; ได้ไฟล์ใหญ่เกิน <strong>9 เท่า</strong> "
        "(1080&times;1920 = ~8 MB vs 352&times;672 = ~0.8 MB) โดยจอจะ downscale อยู่ดี ไม่ได้คุณภาพเพิ่ม.</p>"
        "<p><strong>S3 path ปัจจุบัน:</strong> <code>s3://bucket/vp/{videoId}/{aspectRatio}.mp4</code> "
        "(เช่น <code>vp/ADV20251114ABC123/16-9.mp4</code>)</p>"
    ))

    # Resolution-Aware Encoding
    sections.append('<h4>v2 Resolution-Aware Encoding (Per-Billboard Variant)</h4>')
    sections.append(warning_panel(
        "<p><strong>Architectural Change:</strong> แทนที่จะ encode <strong>fixed resolution per aspect ratio</strong>, "
        "v2 encode ตาม <strong>resolution จริงของ billboard ที่ active</strong>. "
        "ป้ายที่ resolution เหมือนกัน share variant เดียวกัน.</p>"
    ))
    sections.append("""<table>
<tr><th>ขั้นตอน</th><th>v1 (ปัจจุบัน)</th><th>v2 (เสนอ)</th></tr>
<tr><td><strong>1. Upload Creative</strong></td><td>User upload video &rarr; <code>UploadVideo</code> use case</td><td>เหมือนเดิม</td></tr>
<tr><td><strong>2. Determine Variants</strong></td><td>ใช้ <code>advertisement_aspect_ratios</code> &rarr; fixed resolution map<br/>(16:9 &rarr; 1920&times;1080 เสมอ)</td><td>Query <strong>billboard actual resolutions</strong> จาก <code>billboards</code> table<br/>group by unique resolution &rarr; encode เฉพาะที่ต้องใช้จริง</td></tr>
<tr><td><strong>3. Encode</strong></td><td>FFmpeg encode 1 file per aspect ratio</td><td>FFmpeg encode <strong>1 file per unique resolution</strong><br/>(strip audio + slow preset)</td></tr>
<tr><td><strong>4. Store</strong></td><td><code>vp/{videoId}/{ratio}.mp4</code><br/>(e.g. <code>16-9.mp4</code>)</td><td><code>vp/{videoId}/{width}x{height}.mp4</code><br/>(e.g. <code>1920x1080.mp4</code>, <code>352x672.mp4</code>)</td></tr>
<tr><td><strong>5. Serve</strong></td><td>API ส่ง URL ตาม aspect ratio</td><td>API ส่ง URL <strong>ตาม billboard resolution</strong> ใน <code>creative_manifest</code></td></tr>
</table>""")

    # Billboard resolution data
    sections.append('<h4>ข้อมูลป้ายจาก Production DB (Feb 2026)</h4>')
    sections.append("""<table>
<tr><th>ป้าย</th><th>Aspect Ratio</th><th>Resolution จริง</th><th>v1 Encode Size</th><th>v2 Encode Size</th><th>ลดได้</th></tr>
<tr><td>แยกเทพประสิทธิ์, ถ.เทพคุณากร, แลนด์มาร์คราชพฤกษ์, แยกพัทยาเหนือ, สี่แยกชะอำ</td><td>16:9</td><td>1920&times;1080</td><td>~8 MB</td><td>~5.8 MB</td><td><strong>-28%</strong> (audio+preset)</td></tr>
<tr><td><strong>แยกพงษ์เพชร</strong></td><td>3:2</td><td><strong>1080&times;720</strong></td><td>~8 MB</td><td><strong>~2.5 MB</strong></td><td><strong>-69%</strong></td></tr>
<tr><td><strong>แยกเดชาติวงศ์</strong></td><td>9:8</td><td><strong>1080&times;960</strong></td><td>~8 MB</td><td><strong>~5.0 MB</strong></td><td><strong>-38%</strong></td></tr>
<tr><td><strong>แลนด์มาร์คมหาชัย</strong></td><td>9:16 (portrait)</td><td><strong>352&times;672</strong></td><td>~8 MB</td><td><strong>~0.8 MB</strong></td><td><strong>-90%</strong></td></tr>
<tr><td>ป้าย inactive (4 ตัว)</td><td>ต่างกัน</td><td>null</td><td>ใช้ default</td><td>ใช้ default (aspect ratio map)</td><td>&mdash;</td></tr>
</table>""")
    sections.append(note_panel(
        "<p><strong>Unique resolutions ปัจจุบัน:</strong> 4 resolutions จาก 8 ป้าย active &mdash; "
        "creative 1 ตัว encode แค่ 4 variants (ไม่ใช่ 5 ตาม aspect ratio map). "
        "ป้าย 16:9 ทั้ง 5 ตัว <strong>share variant เดียวกัน</strong> (1920&times;1080).</p>"
    ))

    # Encoding trigger strategy
    sections.append('<h4>Encoding Trigger Strategy</h4>')
    sections.append("""<table>
<tr><th>Event</th><th>Action</th><th>ตัวอย่าง</th></tr>
<tr><td><strong>Creative Upload</strong></td><td>Encode variants สำหรับทุก unique resolution ของป้ายที่ active + ใช้ creative นี้</td><td>Upload video &rarr; encode 1920x1080, 1080x720, 1080x960, 352x672</td></tr>
<tr><td><strong>Billboard เปิดใหม่</strong> (resolution ใหม่)</td><td>Queue re-encode ของ creative ที่ยังไม่มี variant สำหรับ resolution นี้</td><td>เพิ่มป้าย 800x600 &rarr; re-encode creative ที่ assign ให้ป้ายนี้</td></tr>
<tr><td><strong>Billboard เปลี่ยน resolution</strong></td><td>Queue re-encode ถ้า variant ใหม่ยังไม่มี + evict variant เก่า (ถ้าไม่มีป้ายอื่นใช้)</td><td>ป้ายอัพเกรดจอ 720p &rarr; 1080p</td></tr>
<tr><td><strong>Fallback</strong></td><td>ถ้า exact variant ยังไม่พร้อม &rarr; ใช้ variant ที่ใกล้เคียง (resolution สูงกว่า)</td><td>ป้าย 352x672 variant ยัง encode ไม่เสร็จ &rarr; ใช้ 1080x1920 ชั่วคราว</td></tr>
</table>""")

    # Combined impact
    sections.append('<h4>Combined Impact: Resolution + Encoding + Network</h4>')
    sections.append(
        '<p>ตัวอย่าง <strong>ป้ายมหาชัย</strong> (352&times;672, SIM 4G, 10 ads):</p>'
    )
    sections.append("""<table>
<tr><th>Layer</th><th>ก่อน</th><th>หลัง</th><th>ลดได้</th></tr>
<tr><td><strong>1. Resolution-Aware</strong></td><td>1080&times;1920 (~8 MB)</td><td>352&times;672 (~1.0 MB)</td><td><strong>-87%</strong></td></tr>
<tr><td><strong>2. Strip Audio + Slow Preset</strong></td><td>~1.0 MB</td><td>~0.7 MB</td><td><strong>-30%</strong></td></tr>
<tr><td><strong>3. 10 ads total download</strong></td><td>80 MB (v1)</td><td><strong>7 MB</strong> (v2)</td><td><strong>-91%</strong></td></tr>
<tr><td><strong>4. Download time (SIM 10 Mbps, parallel)</strong></td><td>~64s (sequential)</td><td><strong>~2s</strong> (3 concurrent)</td><td><strong>-97%</strong></td></tr>
<tr><td><strong>5. Data cost/เดือน</strong></td><td>~80 MB &times; 30 = 2.4 GB</td><td>~7 MB &times; 30 = <strong>210 MB</strong></td><td><strong>-91%</strong></td></tr>
</table>""")
    sections.append(success_panel(
        "<p><strong>ผลลัพธ์รวม (มหาชัย):</strong> จาก 8 MB/file &rarr; 0.7 MB/file, "
        "download 10 ads บน SIM 4G จาก 64 วินาที เหลือ 2 วินาที, "
        "ค่า data ต่อเดือนจาก 2.4 GB เหลือ 210 MB</p>"
    ))

    sections.append(
        '<p>ตัวอย่าง <strong>ป้าย 1080p</strong> (16:9, Broadband, 10 ads) &mdash; ไม่ได้ประโยชน์จาก resolution-aware แต่ได้จาก encoding optimization:</p>'
    )
    sections.append("""<table>
<tr><th>Layer</th><th>ก่อน</th><th>หลัง</th><th>ลดได้</th></tr>
<tr><td><strong>1. Resolution-Aware</strong></td><td>1920&times;1080 (~8 MB)</td><td>1920&times;1080 (~8 MB)</td><td>ไม่เปลี่ยน</td></tr>
<tr><td><strong>2. Strip Audio + Slow Preset</strong></td><td>~8 MB</td><td>~5.8 MB</td><td><strong>-28%</strong></td></tr>
<tr><td><strong>3. 10 ads total download</strong></td><td>80 MB (v1)</td><td><strong>58 MB</strong> (v2)</td><td><strong>-28%</strong></td></tr>
<tr><td><strong>4. Download time (BB 100 Mbps, parallel)</strong></td><td>~6.4s (sequential)</td><td><strong>~1s</strong> (5 concurrent)</td><td><strong>-84%</strong></td></tr>
</table>""")

    # API Response integration
    sections.append('<h4>API Response: creative_manifest (v2)</h4>')
    sections.append(info_panel(
        "<p>v2 API ส่ง <code>creative_manifest</code> ที่มี URL ตรงกับ resolution ของป้ายที่ request &mdash; "
        "Player ไม่ต้องรู้ว่ามี variant อื่น แค่ download URL ที่ได้มา.</p>"
    ))
    sections.append(tracked_code_block(
        '// creative_manifest ใน GET /v3/screen-schedule response\n'
        '// Billboard: แลนด์มาร์คมหาชัย (352x672)\n'
        '"creative_manifest": [\n'
        '  {\n'
        '    "creative_code": "CR-xxx",\n'
        '    "url": "https://cdn.../vp/ADV20251114ABC123/352x672.mp4",\n'
        '    "checksum": "a1b2c3d4...",\n'
        '    "size_bytes": 734003,      // ~0.7 MB (resolution-aware)\n'
        '    "width": 352,\n'
        '    "height": 672\n'
        '  },\n'
        '  {\n'
        '    "creative_code": "CR-yyy",\n'
        '    "url": "https://cdn.../vp/ADV20251115DEF456/352x672.mp4",\n'
        '    "checksum": "e5f6g7h8...",\n'
        '    "size_bytes": 891204,\n'
        '    "width": 352,\n'
        '    "height": 672\n'
        '  }\n'
        ']\n'
        '\n'
        '// เทียบกับ Billboard 1080p (แยกเทพประสิทธิ์):\n'
        '// "url": "https://cdn.../vp/ADV20251114ABC123/1920x1080.mp4"\n'
        '// "size_bytes": 5800000  // ~5.8 MB\n'
        '// Creative เดียวกัน (CR-xxx) แต่คนละ variant ตาม billboard',
        "json", "creative_manifest per Billboard Resolution",
        collapse=True,
    ))

    # Edge cases
    sections.append('<h4>Edge Cases และข้อจำกัด</h4>')
    sections.append(warning_panel(
        "<p><strong>Edge Cases:</strong></p>"
        "<ul>"
        "<li><strong>ป้ายทดสอบ (id=23):</strong> <code>resolution_width=0, resolution_height=0</code> "
        "&rarr; treat เหมือน null (ใช้ default aspect ratio map)</li>"
        "<li><strong>ป้าย inactive ไม่มี resolution:</strong> ไม่ encode variant &mdash; "
        "encode เมื่อป้าย activate และกรอก resolution</li>"
        "<li><strong>ไม่มี <code>hasAudio</code> flag:</strong> ปัจจุบันทุกป้ายไม่มีลำโพง "
        "&rarr; strip audio ทุกไฟล์ ถ้าอนาคตบางป้ายมีลำโพง ต้องเพิ่ม flag + encode with audio variant</li>"
        "<li><strong>H.265 (อนาคต):</strong> ลดได้ 40-60% เพิ่ม แต่ต้อง test กับ Tauri player (Chromium รองรับตั้งแต่ Chrome 107)</li>"
        "<li><strong>Variant ยัง encode ไม่เสร็จ:</strong> Fallback ใช้ variant resolution สูงกว่าที่มี &mdash; "
        "Player download ไฟล์ใหญ่กว่าชั่วคราว จน exact variant พร้อม (re-download ครั้งเดียว)</li>"
        "<li><strong>Storage cost:</strong> เพิ่ม variant = เพิ่ม S3 storage แต่ file เล็กลง &mdash; "
        "4 unique resolutions &times; 4,190 videos = ~16K files (ปัจจุบัน ~4K files)</li>"
        "</ul>"
    ))

    sections.append(success_panel(
        "<p><strong>Quick Win (ไม่ต้องแก้ player):</strong> Strip audio + preset <code>slow</code> "
        "= ลด file size <strong>~28%</strong> ทุก creative ทุกป้าย &mdash; แก้แค่ video processing config</p>"
        "<p><strong>Biggest Impact (ต้องแก้ API + video processing):</strong> "
        "Resolution-Aware encoding สำหรับ แลนด์มาร์คมหาชัย จาก ~8 MB &rarr; ~0.7 MB ต่อ creative (<strong>-91%</strong>)</p>"
        "<p><strong>Combined (ทุก layer):</strong> ป้าย SIM + resolution ต่ำ ได้ประโยชน์สูงสุด &mdash; "
        "download เร็วขึ้น 30x, ค่า data ลด 91%</p>"
    ))

    return "\n".join(sections)


def build_page_6(page_id: str) -> str:
    """Page 6: Interrupt Controller & Make-Good (2 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Interrupt Controller และระบบ Make-Good</h2>")

    # Interrupt Controller
    sections.append("<h3>Interrupt Controller (ตัวควบคุมการ Interrupt)</h3>")
    sections.append(warning_panel(
        "<p><strong>การตัดสินใจออกแบบ: Selective Interrupt.</strong> "
        "Player ยังเป็น Dumb Renderer สำหรับ P1-G/P2/P3/P4 (รอ creative จบก่อน). "
        "แต่มี <strong>lightweight Interrupt Controller (IC)</strong> สำหรับ P0/P1-TK/P1-ET เท่านั้น.</p>"
        "<p><strong>อ้างอิงจาก Industry:</strong></p>"
        "<ul>"
        '<li><a href="https://docs.broadsign.com/broadsign-control/latest/en/settings-section.html">'
        "Broadsign Day Part Switch</a>: configurable interrupt vs wait-for-completion — "
        "เรา map priority level เป็นตัวตัดสิน (P0/P1 = interrupt, P2-P4 = wait)</li>"
        '<li><a href="https://xibosignage.com/manual/en/layouts_interrupt">'
        "Xibo Interrupt Layout</a>: priority system + Share of Voice — "
        "เรา adopt priority concept แต่ใช้ timeline reservation แทน SOV %</li>"
        "</ul>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("06-10-interrupt-controller.mmd"),
        page_id=page_id,
    ))
    sections.append(
        '<table>'
        '<tr><th>Trigger</th><th>Action</th><th>Resume</th></tr>'
        '<tr><td><strong>P0 Emergency</strong><br/>(Pusher: p0-emergency)</td>'
        '<td>หยุดทันที → เล่น emergency creative</td>'
        '<td>Resume item ถัดไปหลัง emergency จบ. เวลา TK ที่เสียไป log ไว้สำหรับ billing manual</td></tr>'
        '<tr><td><strong>P1-TK Start</strong><br/>(Pusher: takeover-start หรือ local clock)</td>'
        '<td>หยุด creative ปัจจุบัน → สลับไป TK creative → วน loop จนถึง TK_END</td>'
        '<td>TK_END → resume item ถัดไปใน schedule ปกติ + make-good สำหรับ ad ที่โดน interrupt</td></tr>'
        '<tr><td><strong>P1-ET Trigger</strong><br/>(local clock ±5s)</td>'
        '<td>หยุด P2-P4 ปัจจุบัน → เล่น ET spot (เล่นครั้งเดียว)</td>'
        '<td>ET เสร็จ → resume item ถัดไป + make-good สำหรับ ad ที่โดน interrupt</td></tr>'
        '</table>'
    )

    # Make-Good System
    sections.append("<h3>ระบบ Make-Good (ชดเชย Ad ที่โดน Interrupt)</h3>")
    sections.append(info_panel(
        "<p><strong>Make-Good</strong> คือ industry standard สำหรับชดเชย ad ที่โดน interrupt "
        '(<a href="https://www.cjadvertising.com/blog/industry-trends/preempts-makegoods-money-move/">'
        "CJ Advertising: Preempts, Make-Goods, and the Money Move</a>). "
        "Ad ที่เล่นไม่จบ (partial play) <strong>ไม่นับเป็น impression</strong> — "
        "ระบบจะชดเชยด้วย slot ฟรีใน cycle ถัดไป.</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("06-11-make-good.mmd"),
        page_id=page_id,
    ))
    sections.append(
        '<table>'
        '<tr><th>Field</th><th>Description</th></tr>'
        '<tr><td><code>interrupted</code></td><td>boolean — PoP flag: ad ถูก interrupt กลางคัน</td></tr>'
        '<tr><td><code>play_duration_seconds</code></td><td>เวลาที่เล่นจริงก่อนถูก interrupt (เช่น 8s จาก 15s)</td></tr>'
        '<tr><td><code>interrupt_reason</code></td><td><code>P0_emergency</code> / <code>TK_start</code> / <code>TK_end</code> / <code>P1_exact_time</code></td></tr>'
        '<tr><td><code>make_good</code></td><td>boolean — PoP flag: ad นี้เป็น make-good compensation (เล่นซ้ำเพื่อชดเชย)</td></tr>'
        '<tr><td><code>compensated</code></td><td>MakeGoodRecord: ชดเชยแล้วหรือยัง</td></tr>'
        '<tr><td><code>compensated_at</code></td><td>เวลาที่ชดเชยสำเร็จ</td></tr>'
        '</table>'
    )

    sections.append("<h3>Make-Good Policy: 3-Level (สำหรับ Dayparted Campaigns)</h3>")
    sections.append(note_panel(
        "<p>เมื่อ Takeover (P1-TK) preempt Dayparted Guaranteed window ระบบ make-good ทำงาน 3 levels "
        "(อิงจาก broadcast TV precedent — same daypart &rarr; equivalent &rarr; credit):</p>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Level</th><th>เงื่อนไข</th><th>ระบบทำ</th></tr>'
        '<tr><td><strong>Level 1</strong></td><td>Window ยังมีเวลาเหลือหลัง TK จบ</td><td>Repack missed plays ใน window เดิม (center-offset เหมือนเดิม)</td></tr>'
        '<tr><td><strong>Level 2</strong></td><td>Window หมดแล้ว, วันเดิม</td><td>ย้าย plays ไป equivalent slot ใน operating hours วันเดิม (ต้องอยู่นอก TK blocks)</td></tr>'
        '<tr><td><strong>Level 3</strong></td><td>Level 2 ทำไม่ได้ (TK ยึดทั้งวัน)</td><td>ออก credit ต่อ campaign — log <code>compensated: false, makegood_tier: 3</code></td></tr>'
        '</table>'
    )
    sections.append(info_panel(
        "<p><strong>Advertiser เลือก preemption class ตอน booking:</strong></p>"
        "<ul>"
        "<li><code>same_window_only</code> — make-good ใน window เดิมเท่านั้น (ถ้าทำไม่ได้ &rarr; Level 3 credit โดยตรง)</li>"
        "<li><code>same_day_flexible</code> (default) — Level 1 &rarr; 2 &rarr; 3 ตามลำดับ</li>"
        "<li><code>credit_preferred</code> — ข้าม Level 1/2 ไป Level 3 เลย</li>"
        "</ul>"
        "<p><strong>Production operating hours (confirmed):</strong> 06:00–22:00 ทุกป้าย (ไม่มี overnight) "
        "&mdash; Level 2 always feasible ถ้ายังอยู่ในวันเดียวกัน</p>"
    ))

    return "\n".join(sections)


def build_page_7(page_id: str) -> str:
    """Page 7: Event-Driven Architecture (1 mermaid, 2 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>สถาปัตยกรรม Event-Driven</h2>")
    sections.append(info_panel(
        "<p><strong>การตัดสินใจ:</strong> ทำให้ event-driven patterns ที่มีอยู่ (Pusher + BullMQ) ชัดเจนขึ้นด้วย typed contracts, "
        "domain events, และ ownership ที่ชัดเจน. <strong>ไม่ใช่</strong> Event-Sourcing &mdash; scale + ทีมยังไม่จำเป็นต้อง complex ขนาดนั้น.</p>"
    ))

    sections.append("<h3>สิ่งที่มีอยู่แล้ว (De Facto Event-Driven)</h3>")

    sections.append(
        '<table>'
        '<tr><th>Component</th><th>Pattern</th><th>Status</th></tr>'
        '<tr><td>BullMQ cron &rarr; per-screen jobs</td><td>Job queue เป็น event bus</td><td>' + status_macro("EXISTS", "Green") + '</td></tr>'
        '<tr><td>Pusher events &rarr; Player</td><td>ส่ง event แบบ real-time</td><td>' + status_macro("EXISTS", "Green") + '</td></tr>'
        '<tr><td>PoP retry queue</td><td>คล้าย Outbox (player.history.json)</td><td>' + status_macro("EXISTS", "Green") + '</td></tr>'
        '<tr><td>Typed event contracts</td><td>Interface ชัดเจนต่อ event</td><td>' + status_macro("MISSING", "Red") + '</td></tr>'
        '<tr><td>Domain events ใน code</td><td>ตั้งชื่อ event เพื่อ traceability</td><td>' + status_macro("MISSING", "Red") + '</td></tr>'
        '<tr><td>Idempotency keys</td><td>ป้องกัน duplicate ตอน retry</td><td>' + status_macro("MISSING", "Red") + '</td></tr>'
        '<tr><td>Version protocol</td><td>เลข version เพิ่มขึ้นเรื่อยๆ ต่อ device</td><td>' + status_macro("MISSING", "Red") + '</td></tr>'
        '</table>'
    )

    sections.append("<h3>Typed Pusher Event Contracts</h3>")
    sections.append(note_panel(
        "<p><strong>เป้าหมาย:</strong> ทุก Pusher event มี TypeScript interface ที่ใช้ร่วมกันระหว่าง backend และ player. "
        "ไม่มี <code>any</code> types หรือ implicit contracts อีกต่อไป.</p>"
    ))

    sections.append(tracked_code_block(
        "// ─── Shared Event Types ───\n"
        "// File: packages/shared/events/pusher-events.ts\n"
        "// (or inline in both projects until monorepo)\n\n"
        "/** Base for all Pusher events */\n"
        "interface PusherEventBase {\n"
        "  event_id: string       // UUID, for inbox dedup\n"
        "  timestamp: string      // ISO 8601\n"
        "  device_code: string\n"
        "}\n\n"
        "// ─── Existing Events (formalized) ───\n\n"
        "interface UpdatePlayScheduleEvent extends PusherEventBase {\n"
        "  type: 'update-play-schedule'\n"
        "  version: number        // NEW: monotonic per-device\n"
        "  round_id: string\n"
        "  schedule_count: number\n"
        "}\n\n"
        "interface CreatedPlayScheduleEvent extends PusherEventBase {\n"
        "  type: 'created-play-schedule'\n"
        "  version: number\n"
        "  round_id: string\n"
        "  source: 'cron' | 'player-pull'\n"
        "}\n\n"
        "/** @deprecated Phase 1+ — absorbed into schedule-updated\n"
        " *  ADE pre-positions guaranteed spots in ordered sequence,\n"
        " *  so direct inject via this event is no longer needed.\n"
        " *  Kept during migration (Phase 0-3) for backward compat. */\n"
        "interface ApprovedExclusiveEvent extends PusherEventBase {\n"
        "  type: 'approved-advertisement-exclusive'\n"
        "  version: number\n"
        "  advertisement_code: string\n"
        "  play_at: string        // ISO 8601\n"
        "  duration_seconds: number\n"
        "  media_url: string\n"
        "  media_checksum: string\n"
        "}\n\n"
        "interface StopAdvertisementEvent extends PusherEventBase {\n"
        "  type: 'stop-advertisement'\n"
        "  version: number\n"
        "  advertisement_code: string\n"
        "  reason: 'cancelled' | 'budget_exhausted' | 'expired'\n"
        "}\n\n"
        "interface UnPairScreenEvent extends PusherEventBase {\n"
        "  type: 'un-pair-screen'\n"
        "  reason: 'admin' | 'replaced'\n"
        "}\n\n"
        "// ─── New Events (Proposed) ───\n\n"
        "interface ScheduleUpdatedEvent extends PusherEventBase {\n"
        "  type: 'schedule-updated'\n"
        "  version: number\n"
        "  tier: 'live' | 'buffer' | 'fallback'\n"
        "  item_count: number\n"
        "  valid_from: string\n"
        "  valid_until: string\n"
        "  /** Media codes that player should pre-download */\n"
        "  new_media_codes: string[]\n"
        "}\n\n"
        "interface DeviceConfigUpdatedEvent extends PusherEventBase {\n"
        "  type: 'device-config-updated'\n"
        "  changes: ('operating_hours' | 'player_mode' | 'fallback_playlist')[]\n"
        "}\n\n"
        "// ─── New Events: Interrupt/Takeover (v24) ───\n\n"
        "interface TakeoverStartEvent extends PusherEventBase {\n"
        "  type: 'takeover-start'\n"
        "  version: number\n"
        "  takeover_id: number\n"
        "  creative_code: string\n"
        "  end_time: string          // ISO 8601 — when TK ends\n"
        "}\n\n"
        "interface TakeoverEndEvent extends PusherEventBase {\n"
        "  type: 'takeover-end'\n"
        "  version: number\n"
        "  takeover_id: number\n"
        "}\n\n"
        "interface P0EmergencyEvent extends PusherEventBase {\n"
        "  type: 'p0-emergency'\n"
        "  version: number\n"
        "  message: string\n"
        "  creative_url: string\n"
        "  duration_seconds: number\n"
        "}\n\n"
        "// ─── New Events: Daypart Targeting ───\n\n"
        "interface DaypartWindowConflictEvent extends PusherEventBase {\n"
        "  type: 'daypart-window-conflict'\n"
        "  version: number\n"
        "  ad_group_code: string\n"
        "  window_id: number\n"
        "  conflict_reason: 'takeover_overlap' | 'billboard_offline'\n"
        "  missed_plays: number         // plays ที่ไม่ได้เล่น\n"
        "  makegood_tier: 1 | 2 | 3    // make-good level ที่ระบบจะใช้ชดเชย\n"
        "}\n\n"
        "interface DaypartMakeGoodTriggeredEvent extends PusherEventBase {\n"
        "  type: 'daypart-makegood-triggered'\n"
        "  version: number\n"
        "  ad_group_code: string\n"
        "  makegood_tier: 1 | 2 | 3\n"
        "  rescheduled_at: string | null  // null = Level 3 credit (no reschedule)\n"
        "}\n\n"
        "// ─── Union Type ───\n"
        "type PusherEvent =\n"
        "  | UpdatePlayScheduleEvent\n"
        "  | CreatedPlayScheduleEvent\n"
        "  | ApprovedExclusiveEvent   // @deprecated — migration only\n"
        "  | StopAdvertisementEvent\n"
        "  | UnPairScreenEvent\n"
        "  | ScheduleUpdatedEvent\n"
        "  | DeviceConfigUpdatedEvent\n"
        "  | TakeoverStartEvent               // v24\n"
        "  | TakeoverEndEvent                 // v24\n"
        "  | P0EmergencyEvent                 // v24\n"
        "  | DaypartWindowConflictEvent       // v2 Daypart\n"
        "  | DaypartMakeGoodTriggeredEvent    // v2 Daypart",
        "typescript", "Typed Pusher Event Contracts",
        collapse=True,
    ))

    sections.append("<h3>Domain Events (ระดับ Code ภายใน)</h3>")
    sections.append(note_panel(
        "<p><strong>เป้าหมาย:</strong> ตั้งชื่อ domain events ใน backend code เพื่อ traceability. "
        "ไม่ได้เก็บเป็น event-sourcing log &mdash; แค่ typed objects ที่ส่งระหว่าง services.</p>"
    ))

    sections.append(tracked_code_block(
        "// File: app/Events/PlaySchedule/PlayScheduleEvents.ts\n\n"
        "/** Emitted: PlayScheduleCalculatePerScreen completes */\n"
        "interface PlayScheduleCalculated {\n"
        "  type: 'PlayScheduleCalculated'\n"
        "  screen_code: string\n"
        "  round_id: string\n"
        "  schedule_codes: string[]\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: AdDecisioningService completes */\n"
        "interface ScreenScheduleBuilt {\n"
        "  type: 'ScreenScheduleBuilt'\n"
        "  device_code: string\n"
        "  schedule_id: number\n"
        "  version: number\n"
        "  tier: 'live' | 'buffer' | 'fallback'\n"
        "  item_count: number\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Player confirms creative assets downloaded */\n"
        "interface CreativeDownloadConfirmed {\n"
        "  type: 'CreativeDownloadConfirmed'\n"
        "  device_code: string\n"
        "  creative_codes: string[]\n"
        "  total_bytes: number\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Player sends PoP (Proof of Play) batch */\n"
        "interface PoPReceived {\n"
        "  type: 'PoPReceived'\n"
        "  device_code: string\n"
        "  batch_size: number\n"
        "  idempotency_keys: string[]\n"
        "  new_entries: number  // after dedup\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Device reconnects after gap */\n"
        "interface DeviceResynced {\n"
        "  type: 'DeviceResynced'\n"
        "  device_code: string\n"
        "  from_version: number\n"
        "  to_version: number\n"
        "  sync_type: 'delta' | 'full'\n"
        "  gap_duration_seconds: number\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "// ─── New Domain Events (v24: Interrupt/Takeover) ───\n\n"
        "/** Emitted: Ad interrupted by P0/P1-TK/P1-ET */\n"
        "interface AdInterrupted {\n"
        "  type: 'AdInterrupted'\n"
        "  device_code: string\n"
        "  advertisement_code: string\n"
        "  play_duration_seconds: number\n"
        "  interrupt_reason: 'P0_emergency' | 'TK_start' | 'TK_end' | 'P1_exact_time'\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Make-good compensation scheduled for next cycle */\n"
        "interface MakeGoodScheduled {\n"
        "  type: 'MakeGoodScheduled'\n"
        "  device_code: string\n"
        "  advertisement_code: string\n"
        "  make_good_id: number\n"
        "  original_interrupt_reason: string\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Takeover block starts/ends */\n"
        "interface TakeoverStateChanged {\n"
        "  type: 'TakeoverStateChanged'\n"
        "  device_code: string\n"
        "  takeover_id: number\n"
        "  state: 'active' | 'completed'\n"
        "  timestamp: DateTime\n"
        "}\n\n"
        "/** Emitted: Daypart window conflict detected (TK preempts guaranteed window) */\n"
        "interface DaypartWindowConflict {\n"
        "  type: 'DaypartWindowConflict'\n"
        "  device_code: string\n"
        "  ad_group_code: string\n"
        "  window_id: number\n"
        "  missed_plays: number\n"
        "  makegood_tier: 1 | 2 | 3\n"
        "  timestamp: DateTime\n"
        "}",
        "typescript", "Domain Events",
        collapse=True,
    ))

    sections.append("<h3>แผนภาพ Event Flow</h3>")
    sections.append(mermaid_diagram(
        load_diagram("07-4-event-flow.mmd"),
        page_id=page_id,
    ))

    # ─── Architectural Decision Record ───
    sections.append("<h2>Architectural Decision Record</h2>")
    sections.append(note_panel(
        "<p><strong>คำแนะนำเรื่อง Protocol:</strong> ใช้ Pusher ต่อ (มีอยู่แล้ว) สำหรับ real-time push. เพิ่ม <strong>version-based checkpoint</strong> ตอน reconnect ผ่าน REST. "
        "อย่าพึ่ง push สำหรับ playback &mdash; push แค่ trigger sync ให้เร็วขึ้น.</p>"
        "<p><strong>หลักการสำคัญ (จาก RxDB):</strong> Client อาจพลาด event ตอน disconnect. "
        "วิธีแก้: checkpoint mode ตอน reconnect (เทียบ schedule ทั้งหมดผ่าน REST) + event mode หลัง sync แล้ว (Pusher สำหรับ incremental).</p>"
    ))
    sections.append(expand_section("ADR-002: Why Event-Driven, NOT Event-Sourcing",
        warning_panel(
            "<p><strong>ADR-002:</strong> Event-Driven Architecture (NOT Event-Sourcing)</p>"
        ) +
        '<table>'
        '<tr><th>Aspect</th><th>Details</th></tr>'
        '<tr><td><strong>Context</strong></td><td>'
        'ระบบใช้ Pusher + BullMQ + Play history retry ซึ่งเป็น event-driven pattern อยู่แล้ว '
        'แต่ไม่มี typed contracts, domain events, หรือ idempotency &mdash; ต้อง formalize</td></tr>'
        '<tr><td><strong>Options Considered</strong></td><td>'
        '<strong>A) Formalize Event-Driven</strong> &mdash; typed contracts, domain events (in-memory), outbox/inbox dedup<br/>'
        '<strong>B) Full Event-Sourcing</strong> &mdash; event store (Kafka/EventStoreDB), projections, snapshots, CQRS</td></tr>'
        '<tr><td><strong>Decision</strong></td><td><strong>Option A: Formalize Event-Driven</strong></td></tr>'
        '<tr><td><strong>Rationale</strong></td><td>'
        '<ul>'
        '<li><strong>Scale:</strong> ~100-500 billboards, ไม่ใช่ millions of events/sec</li>'
        '<li><strong>Team:</strong> Junior devs 3 คน (fix-heavy, need review) &mdash; event store + projections ซับซ้อนเกินไป</li>'
        '<li><strong>PlaySchedule model:</strong> CRUD + status (WAITING&rarr;PLAYING&rarr;PLAYED) ใช้งานได้ดี ไม่จำเป็นต้อง replay</li>'
        '<li><strong>No business need:</strong> ไม่ต้อง replay events ย้อนหลัง, ไม่ต้อง audit trail ระดับ event</li>'
        '<li><strong>Operational cost:</strong> Event store (Kafka/EventStoreDB) + schema versioning + eventual consistency debugging</li>'
        '</ul></td></tr>'
        '<tr><td><strong>Consequences</strong></td><td>'
        '<ul>'
        '<li>+ ง่ายต่อ team ในการ maintain</li>'
        '<li>+ ไม่ต้องเพิ่ม infrastructure (ใช้ Redis + Pusher + BullMQ เดิม)</li>'
        '<li>+ Typed contracts ป้องกัน runtime error</li>'
        '<li>+ Domain events เพิ่ม traceability ใน code</li>'
        '<li>- ไม่สามารถ replay events ได้ (ต้องมี backup/restore แบบ traditional)</li>'
        '<li>- ถ้า scale ถึง 5,000+ จอ อาจต้อง revisit</li>'
        '</ul></td></tr>'
        '<tr><td><strong>Review Date</strong></td><td>Revisit เมื่อ scale &ge; 2,000 billboards หรือ team &ge; 8 devs</td></tr>'
        '</table>'
    ))

    sections.append("<h3>Checklist การ Implement</h3>")
    sections.append(success_panel(
        "<p><strong>สิ่งที่ต้อง formalize (เรียงตาม priority):</strong></p>"
        "<ol>"
        "<li><strong>Typed Pusher event contracts</strong> &mdash; shared interfaces (backend + player)</li>"
        "<li><strong>Version protocol</strong> &mdash; monotonic <code>version</code> per device on every Pusher event</li>"
        "<li><strong>PoP Outbox pattern</strong> &mdash; Tauri Store with UUID idempotency key + flush cycle</li>"
        "<li><strong>Inbox dedup</strong> &mdash; <code>event_id</code> tracking (last 100) + version gap detection</li>"
        "<li><strong>PoP deduplication</strong> &mdash; Redis <code>idem:{uuid}</code> check on PoP endpoint</li>"
        "<li><strong>Domain events (in-code)</strong> &mdash; named typed objects, passed between services, logged for observability</li>"
        "</ol>"
    ))

    return "\n".join(sections)


def build_page_8(page_id: str) -> str:
    """Page 8: Edge Cases, Migration & Appendix (2 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Edge Cases และความทนทาน (Resilience)</h2>")

    sections.append("<h3>ปัญหาเครือข่าย (Network Issues)</h3>")
    sections.append(expand_section("E1-E6: Network Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น</th><th>Solution</th></tr>'
        '<tr><td>E1</td><td><strong>Network flapping</strong> (on/off ทุก 30 วิ)</td>'
        '<td>Player fetch ค้าง, Pusher reconnect วนซ้ำ, media download incomplete</td>'
        '<td><strong>Debounce reconnect:</strong> ต้อง online ต่อเนื่อง 10 วิ ก่อน trigger sync. Media download ต้อง resume-able (Tauri download รองรับอยู่แล้ว)</td></tr>'
        '<tr><td>E2</td><td><strong>Pusher disconnect 5 นาที</strong> &rarr; missed events</td>'
        '<td>Player ไม่รู้ว่ามี playlist ใหม่</td>'
        '<td><strong>Version check on reconnect:</strong> Player เก็บ <code>last_version</code>. Reconnect &rarr; <code>GET /v2/screen-schedule?since_version=N</code> &rarr; ได้ delta</td></tr>'
        '<tr><td>E3</td><td><strong>Pusher duplicate events</strong></td>'
        '<td>Player process playlist update ซ้ำ 2 ครั้ง</td>'
        '<td><strong>Inbox dedup:</strong> เก็บ <code>event_id</code> ล่าสุด 100 รายการ. ถ้าซ้ำ &rarr; skip</td></tr>'
        '<tr><td>E4</td><td><strong>API timeout &rarr; player retry &rarr; duplicate play history</strong></td>'
        '<td>Backend บันทึก 2 records สำหรับ ad เดียวกัน</td>'
        '<td><strong>Outbox + Idempotency Key:</strong> Player สร้าง UUID per play event. Backend check Redis <code>idem:{uuid}</code> ก่อน insert</td></tr>'
        '<tr><td>E5</td><td><strong>Partial media download</strong> (internet หลุดกลาง download)</td>'
        '<td>ไฟล์ media ไม่สมบูรณ์</td>'
        '<td>เดิมมีอยู่แล้ว: <code>fileCleanupService.markDownloading()</code> ป้องกัน cleanup. เพิ่ม: <strong>checksum validation</strong> &mdash; backend ส่ง <code>media.checksum</code> &rarr; ตรวจสอบ + re-download ถ้าไม่ตรง</td></tr>'
        '<tr><td>E6</td><td><strong>SSL certificate expired / DNS failure</strong></td>'
        '<td>fetch fail แต่ internet ยังใช้ได้</td>'
        '<td>Treat เหมือน offline. Player มี Tier 2/3 รองรับ. เพิ่ม <strong>diagnostic log</strong> แยก SSL error จาก network error</td></tr>'
        '</table>'
    ))

    sections.append("<h3>ปัญหา Schedule/Playlist</h3>")
    sections.append(expand_section("E7-E13: Schedule/Playlist Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น</th><th>Solution</th></tr>'
        '<tr><td>E7</td><td><strong>Schedule gap</strong> &mdash; ไม่มี ad สำหรับช่วงเวลานี้</td>'
        '<td>Tier 1 ว่างเปล่า</td>'
        '<td>Auto-switch Tier 3 (owner fallback). <strong>ห้ามจอดำเด็ดขาด</strong></td></tr>'
        '<tr><td>E8</td><td><strong>Guaranteed spot ขณะ offline</strong></td>'
        '<td>Backend approve guaranteed แต่ push ไม่ถึง player</td>'
        '<td><strong>Buffer tier:</strong> Guaranteed ที่ approved ล่วงหน้า ถูกใส่ใน Tier 2 ด้วย <code>priority: guaranteed</code> + <code>play_at: exact_time</code>. Player check Tier 2 ทุก 1 วิ ว่ามี guaranteed <code>CalculatePlaySchedules</code> query ทำอยู่แล้ว)</td></tr>'
        '<tr><td>E9</td><td><strong>Tier 1 หมด แต่ Tier 2 ยังไม่พร้อม</strong> (media กำลัง download)</td>'
        '<td>ช่วงว่างระหว่าง tier</td>'
        '<td>Play Tier 3 ขณะรอ. เมื่อ Tier 2 media download ครบ &rarr; switch ขึ้นไป</td></tr>'
        '<tr><td>E10</td><td><strong>Screen time budget overflow</strong> &mdash; creatives มากกว่า avails</td>'
        '<td>Ad Decisioning Engine สร้าง schedule ยาวเกิน loop</td>'
        '<td>Backend cap ที่ <code>loopDuration</code>. ส่วนที่เกิน &rarr; ไม่ใส่ schedule (เหมือนเดิมที่ cron ทำ). Player ไม่ต้องคิด</td></tr>'
        '<tr><td>E11</td><td><strong>House content ว่าง</strong> &mdash; screen owner ไม่ได้ตั้งค่า</td>'
        '<td>Tier 3 ไม่มี content</td>'
        '<td><strong>First boot check:</strong> ถ้า Tier 3 ว่าง &rarr; แสดง <strong>system splash</strong> (logo + "กำลังเตรียมระบบ"). Admin UI แจ้งเตือน owner ให้ upload content. บังคับ: Device register สำเร็จต่อเมื่อ screen มีอย่างน้อย 1 house creative</td></tr>'
        '<tr><td>E12</td><td><strong>Stale schedule</strong> &mdash; offline นานจน Tier 2 expired</td>'
        '<td><code>valid_until</code> ผ่านไปแล้ว</td>'
        '<td>Player check <code>valid_until</code> ก่อนเล่น. ถ้า expired &rarr; switch Tier 3. <strong>ไม่เล่น ad expired</strong> เพราะอาจเป็น campaign ที่หมดแล้ว (billing issue)</td></tr>'
        '<tr><td>E13</td><td><strong>Concurrent Pusher events</strong> &mdash; 3 events มาพร้อมกัน</td>'
        '<td>Race condition ใน playlist update</td>'
        '<td><strong>Version monotonic:</strong> Player เก็บ <code>current_version</code>. ถ้า <code>event.version</code> &le; current &rarr; skip. ถ้า &gt; current &rarr; process. ถ้า &gt; current+1 (gap) &rarr; full re-fetch</td></tr>'
        '</table>'
    ))

    sections.append("<h3>ปัญหา Device/Storage</h3>")
    sections.append(expand_section("E14-E19: Device/Storage Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น</th><th>Solution</th></tr>'
        '<tr><td>E14</td><td><strong>Player restart ขณะ offline</strong></td>'
        '<td>App crash &rarr; relaunch ไม่มี internet</td>'
        '<td>localStorage persist ข้าม restart (เดิมทำอยู่แล้ว). Boot &rarr; read localStorage &rarr; resume from last <code>sequence_no</code>. ถ้า Tier 1/2 expired &rarr; Tier 3</td></tr>'
        '<tr><td>E15</td><td><strong>First boot ไม่มี internet</strong></td>'
        '<td>Device ใหม่ ยังไม่เคย pair</td>'
        '<td>ไม่สามารถ pair ได้ (ต้องมี internet สำหรับ register). แสดง splash + "กรุณาเชื่อมต่อ internet". Poll ทุก 5 วิ (เดิม)</td></tr>'
        '<tr><td>E16</td><td><strong>Clock drift</strong> &mdash; offline นาน, NTP ไม่ sync</td>'
        '<td><code>valid_until</code> check ผิดพลาด</td>'
        '<td>Tauri บน Windows/macOS/Linux มี RTC ที่แม่นยำกว่า RPi. เก็บ <code>last_ntp_sync</code> timestamp. ถ้า drift &gt; 1 ชม. &rarr; log warning แต่ยังเล่นต่อ (เล่นผิดเวลาดีกว่าจอดำ)</td></tr>'
        '<tr><td>E17</td><td><strong>Disk full</strong> &mdash; media เต็ม storage</td>'
        '<td>Download ใหม่ไม่ได้</td>'
        '<td>เดิมมี cleanup อยู่แล้ว (file-cleanup.service.ts ทุก 24h). เพิ่ม: check disk ก่อน download. ถ้า &lt; 500MB &rarr; trigger emergency cleanup (ลบ media ที่ไม่อยู่ใน Tier 1+2+3). ถ้ายังไม่พอ &rarr; skip download, เล่น ad ถัดไป (ไม่หยุด)</td></tr>'
        '<tr><td>E18</td><td><strong>Media file corrupt</strong></td>'
        '<td>Video file เสีย &rarr; playback error</td>'
        '<td>เดิมมี <strong>retry queue</strong> (max 3 attempts). เพิ่ม: ถ้า retry ครบ 3 ครั้ง &rarr; mark file dirty &rarr; re-download next sync. Player skip ไป ad ถัดไป (ไม่หยุด)</td></tr>'
        '<tr><td>E19</td><td><strong>localStorage quota exceeded</strong> (5-10MB limit)</td>'
        '<td>เก็บ playlist data ไม่พอ</td>'
        '<td>Migrate heavy data &rarr; <strong>Tauri Store</strong> (JSON file, ไม่มี quota). เก็บเฉพาะ small state ใน localStorage. Playlist data &rarr; Tauri Store</td></tr>'
        '</table>'
    ))

    sections.append("<h3>ปัญหา Business Logic</h3>")
    sections.append(expand_section("E20-E24: Business Logic Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น</th><th>Solution</th></tr>'
        '<tr><td>E20</td><td><strong>Ad cancelled ขณะ offline</strong></td>'
        '<td>Backend cancel ad แต่ player ยังเล่นอยู่</td>'
        '<td><strong>Acceptable tradeoff:</strong> player จะเล่น creative ต่อจน reconnect. เมื่อ reconnect &rarr; sync schedule ใหม่ &rarr; creative หายไป. PoP records ยังถูกต้อง (ส่งทีหลัง reconnect)</td></tr>'
        '<tr><td>E21</td><td><strong>Campaign budget exhausted ขณะเล่น</strong></td>'
        '<td>Player กำลังเล่น ad ของ campaign ที่หมด budget</td>'
        '<td>Backend ไม่ใส่ ad นี้ใน round ถัดไป. Player round ปัจจุบันเล่นจบปกติ (ยอมรับได้ &mdash; เป็น 1 round = 5 นาที max)</td></tr>'
        '<tr><td>E22</td><td><strong>PoP ส่งไม่ได้</strong> &rarr; billing คลาดเคลื่อน</td>'
        '<td>Offline นาน &rarr; PoP outbox queue สะสม</td>'
        '<td><strong>Outbox guarantee:</strong> ไม่มี PoP event หาย (persisted ใน Tauri Store). เมื่อ reconnect &rarr; flush ทั้งหมดตามลำดับ. Backend reconcile by timestamp</td></tr>'
        '<tr><td>E23</td><td><strong>Billboard unpair ขณะ offline</strong></td>'
        '<td>Admin unpair device แต่ player ไม่รู้</td>'
        '<td>Player ยังเล่นต่อจาก cache. เมื่อ reconnect &rarr; Pusher <code>un-pair-screen</code> &rarr; clear all + back to pair screen. หรือ: API call fail &rarr; 401 &rarr; trigger unpair locally</td></tr>'
        '<tr><td>E24</td><td><strong>Multiple devices ใช้ device code เดียวกัน</strong></td>'
        '<td>Clone device &rarr; 2 players same code</td>'
        '<td>Backend: POST <code>/v2/play-history</code> ส่ง <code>device_fingerprint</code> (MAC + hostname). ถ้าไม่ตรง &rarr; reject + alert</td></tr>'
        '</table>'
    ))

    sections.append("<h3>Edge Cases ของ Guaranteed Spot (P1-G — ไม่ Interrupt)</h3>")
    sections.append(warning_panel(
        "<p><strong>Edge cases เฉพาะ P1-G guaranteed spots</strong> (เดิมเรียก exclusive). "
        "P1-G ยังคง <strong>ไม่ interrupt</strong> — pre-positioned ใน sequence โดย Ad Decisioning Engine. "
        "สำหรับ edge cases ของ P1-TK (Takeover) และ P1-ET (Exact-Time) ที่มี interrupt ดู §8.6</p>"
    ))
    sections.append(expand_section("EX1-EX7: Guaranteed Spot Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น (ปัจจุบัน)</th><th>Proposed Solution</th></tr>'
        '<tr><td>EX1</td><td><strong>Overlapping guaranteed spots</strong> &mdash; 2 guaranteed spots ที่เวลาทับกัน</td>'
        '<td>ปัจจุบัน: <code>find()</code> picks first match, ไม่มี priority logic ระหว่าง guaranteed spots</td>'
        '<td><strong>Priority queue:</strong> Guaranteed ที่ <code>play_at</code> ตรงกัน &rarr; sort by <code>created_at</code> (FIFO). '
        'Ad Decisioning Engine ตรวจ overlap ตอน build &rarr; reject ตัวหลังที่ทับ (SMIL <code>peers=&quot;stop&quot;</code> semantic). '
        'Admin UI: แสดง warning ก่อน approve ถ้าช่วงเวลาซ้อน</td></tr>'
        '<tr><td>EX2</td><td><strong>Guaranteed creative asset missing/corrupt</strong></td>'
        '<td>ปัจจุบัน: <strong>silent failure</strong> &mdash; interrupted creative stays paused, ไม่มี recovery</td>'
        '<td><strong>Creative validation at booking:</strong> Ad Decisioning Engine checks creative existence + checksum ตอน build. '
        'ถ้า creative ไม่พร้อม &rarr; mark <code>status=PENDING_CREATIVE</code>, alert admin. '
        'Player-side: ถ้า creative download fail &rarr; skip guaranteed, resume normal sequence (ไม่ pause ค้าง)</td></tr>'
        '<tr><td>EX3</td><td><strong>Guaranteed spot approved while player offline</strong></td>'
        '<td>ปัจจุบัน: Pusher push lost, no buffer mechanism &rarr; guaranteed spot ไม่เล่น</td>'
        '<td><strong>Tier 2 pre-staging:</strong> Guaranteed ที่ approved ล่วงหน้า &rarr; ใส่ใน Tier 2 (buffer) ด้วย <code>play_at</code> exact time. '
        'Player check Tier 2 locally ทุก sync cycle. Reconnect &rarr; version-based full sync จะ include guaranteed</td></tr>'
        '<tr><td>EX4</td><td><strong>Guaranteed spot cancelled after schedule built</strong></td>'
        '<td>ปัจจุบัน: ไม่มี cancel mechanism สำหรับ guaranteed ที่ถูก push ไปแล้ว</td>'
        '<td><strong>Cancel event:</strong> Backend push <code>guaranteed-cancelled {ad_code, version++}</code>. '
        'Player receives &rarr; remove from Tier 1/2 + version bump. ถ้า offline &rarr; ยอมรับ tradeoff (เล่นจบแล้ว cancel ตอน sync)</td></tr>'
        '<tr><td>EX5</td><td><strong>Clock drift + guaranteed timing</strong> &mdash; player clock off by &gt;5s</td>'
        '<td>ปัจจุบัน: <code>dayjs().isBetween(start, end)</code> ±2s precision &mdash; clock drift ทำให้ miss window</td>'
        '<td><strong>Server-relative timing:</strong> Guaranteed <code>play_at</code> stored as <code>sequence_no</code> position (not wall-clock). '
        'Player plays by sequence order, ไม่ต้องพึ่ง local clock. '
        'Fallback: NTP sync on reconnect, <code>last_ntp_offset</code> adjustment</td></tr>'
        '<tr><td>EX6</td><td><strong>Nested guaranteed interrupts</strong></td>'
        '<td>ปัจจุบัน: <code>pausePlayData</code> is <strong>single variable</strong> &mdash; nested interrupt loses original paused creative</td>'
        '<td><strong>Eliminated by design:</strong> Ad Decisioning Engine resolves all guaranteed positions at build time. '
        'Player sees flat sequence &mdash; guaranteed spot is just another item at the right position. '
        'No interrupt/pause mechanism needed (SMIL <code>pauseQueue</code> approach unnecessary)</td></tr>'
        '<tr><td>EX7</td><td><strong>Guaranteed spans loop boundary</strong> &mdash; 30s guaranteed at minute 9:50 of 10-min loop</td>'
        '<td>ปัจจุบัน: loop boundary cuts off guaranteed mid-play</td>'
        '<td><strong>Loop extension:</strong> Ad Decisioning Engine extends loop duration to fit guaranteed completely. '
        'Or: guaranteed <code>play_at</code> adjusted to start earlier so it fits within loop. '
        'Config: <code>guaranteed_loop_policy: &quot;extend&quot; | &quot;shift_earlier&quot;</code></td></tr>'
        '</table>'
    ))

    sections.append("<h4>Edge Cases ของ Flow ผสม (Regular + Exclusive)</h4>")
    sections.append(expand_section("CF1-CF5: Combined Flow Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>สิ่งที่เกิดขึ้น</th><th>Solution</th></tr>'
        '<tr><td>CF1</td><td><strong>Guaranteed during Tier 2/3 fallback</strong></td>'
        '<td>Player offline, playing house content &rarr; guaranteed <code>play_at</code> time arrives</td>'
        '<td>Tier 2 pre-staged guaranteed: Player checks Tier 2 locally. ถ้า guaranteed อยู่ใน Tier 2 + creative cached &rarr; play at position. '
        'ถ้าไม่มี (approved after last sync) &rarr; miss (acceptable &mdash; offline = degraded mode)</td></tr>'
        '<tr><td>CF2</td><td><strong>Budget exhausted mid-guaranteed</strong></td>'
        '<td>Guaranteed spot ราคาสูง, campaign budget หมดขณะ guaranteed ยังไม่ถึงเวลา</td>'
        '<td>Guaranteed = <strong>pre-paid delivery commitment</strong>. Budget check at booking time, not play time. '
        'ถ้า budget deplete after booking &rarr; ยังเล่นตาม contract (billing reconcile separately)</td></tr>'
        '<tr><td>CF3</td><td><strong>Multiple guaranteed + campaign creatives &rarr; time overflow</strong></td>'
        '<td>Guaranteed avails กิน time budget เกือบหมด &rarr; campaign creatives ไม่มีที่เล่น</td>'
        '<td>Ad Decisioning Engine: reserve guaranteed FIRST &rarr; remaining time for campaigns. '
        'ถ้า remaining &lt; min_avail_duration &rarr; skip lowest-priority campaigns. '
        'Admin UI: show time utilization preview before approve</td></tr>'
        '<tr><td>CF4</td><td><strong>Hot-swap guaranteed</strong> &mdash; owner cancels guaranteed A, immediately books guaranteed B at same avail</td>'
        '<td>Race condition: cancel event + new booking event may arrive out of order</td>'
        '<td><strong>Version monotonic:</strong> Both cancel and new booking increment version. '
        'Player applies in version order. Ad Decisioning Engine atomic: cancel A + insert B in single build cycle</td></tr>'
        '<tr><td>CF5</td><td><strong>Guaranteed + house content conflict</strong> &mdash; guaranteed books time where only house content was playing</td>'
        '<td>House loop interrupted by guaranteed</td>'
        '<td><strong>Priority model:</strong> P1 (Guaranteed) &gt; P4 (House). Ad Decisioning Engine replaces house avail with guaranteed. '
        'House content resumes after guaranteed completes (next sequence item)</td></tr>'
        '</table>'
    ))

    sections.append("<h3>Edge Cases ของ Takeover และ Exact-Time (P1-TK / P1-ET)</h3>")
    sections.append(mermaid_diagram(
        load_diagram("08-2-takeover-timeline.mmd"),
        page_id=page_id,
    ))
    sections.append("<h4>Timeline การ Interrupt ของ Takeover (Gantt View)</h4>")
    sections.append(info_panel(
        "<p>มุมมองเวลาจริง — เห็นสัดส่วนว่า <strong>TK block 60 นาที</strong> กว้างกว่า normal schedule มาก. "
        "<strong>TK_START/TK_END</strong> = เส้นขอบเขตสีส้ม (:vert). "
        "<strong>Make-good</strong> (ฟ้า :active) เล่นชดเชย Ad A ที่โดน interrupt ทันทีหลัง TK จบ</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("08-3-takeover-gantt.mmd"),
        page_id=page_id,
    ))
    sections.append(_gantt_legend_mini())
    sections.append(expand_section("TK1-TK8: Takeover & Exact-Time Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>Solution</th></tr>'
        '<tr><td>TK1</td><td><strong>TK booking ทับกัน</strong> &mdash; 2 เจ้าของจองช่วงเวลาเดียวกัน</td>'
        '<td>Reject ตอนจอง — <code>checkIsBillboardsReserved</code> ขยายรองรับ TK. 1 time block = 1 เจ้าของเท่านั้น</td></tr>'
        '<tr><td>TK2</td><td><strong>TK creative ยังไม่ cache ตอน TK_START</strong></td>'
        '<td>ข้าม TK → resume schedule ปกติ → แจ้ง admin. Pre-stage creative ผ่าน <code>device-config-updated</code> event ตอนจอง</td></tr>'
        '<tr><td>TK3</td><td><strong>P0 Emergency ระหว่าง TK</strong></td>'
        '<td>P0 ชนะเสมอ (priority สูงสุด). เวลา TK ที่เสียไป — log สำหรับ billing reconcile manual</td></tr>'
        '<tr><td>TK4</td><td><strong>Player offline ตอน TK_START</strong></td>'
        '<td>ใช้ local clock: TK schedule อยู่ใน Tier 2 พร้อม <code>takeover_id</code>. IC เช็ค local clock กับ TK boundary ที่รอ</td></tr>'
        '<tr><td>TK5</td><td><strong>จอง TK กระชั้นเกินไป (lead time ไม่พอ)</strong></td>'
        '<td>Reject — ใช้ lead time เดียวกับ guaranteed spots (exclusive validation เดิม)</td></tr>'
        '<tr><td>TK6</td><td><strong>TK creative เปลี่ยนหลังจอง</strong></td>'
        '<td>Push <code>device-config-updated</code> ใหม่พร้อม <code>creative_code</code> ใหม่. Player download ก่อน TK_START</td></tr>'
        '<tr><td>TK7</td><td><strong>หลาย ET spots ในวินาทีเดียวกัน</strong></td>'
        '<td>FIFO ตาม <code>created_at</code> — ตัวแรกได้เล่น, ตัวถัดไปขยับ <code>+duration</code> (เรียงต่อกัน ไม่พร้อมกัน)</td></tr>'
        '<tr><td>TK8</td><td><strong>Make-good creative หมดอายุ</strong></td>'
        '<td>ข้ามการชดเชย — log สำหรับ reconcile manual. ตรวจ <code>valid_until</code> ป้องกันเล่น ad ที่หมดอายุ</td></tr>'
        '<tr><td>TK9</td><td><strong>TK ทับ Dayparted Guaranteed window ทั้งหมด</strong></td>'
        '<td>Daypart plays ในช่วงนั้นถูก block → 3-level make-good: Level 1 (repack ใน window ที่เหลือ) → Level 2 (ย้ายไป equivalent slot วันเดิม) → Level 3 (credit)</td></tr>'
        '<tr><td>TK10</td><td><strong>TK ทับ Daypart window บางส่วน</strong></td>'
        '<td>เล่น plays ก่อน TK ตามปกติ → plays ที่อยู่ใน TK block → Level 1 repack ใน window ที่เหลือหลัง TK</td></tr>'
        '<tr><td>TK11</td><td><strong>Billboard offline ระหว่าง Daypart window</strong></td>'
        '<td>Repack missed plays ใน window ที่เหลือ (center-offset ปรับใหม่) → ถ้า window หมดก่อน → Level 2 → Level 3 ตาม makegood_preference</td></tr>'
        '<tr><td>TK12</td><td><strong>Daypart window นอก operating hours</strong></td>'
        '<td>Reject at booking — validate <code>startTime &ge; billboard.opening_time</code> AND <code>endTime &le; billboard.closing_time</code>. Production range: 06:00–22:00</td></tr>'
        '</table>'
    ))

    sections.append("<hr/>")
    sections.append("<h2>แผนการ Migration (Parallel Operation Strategy)</h2>")
    sections.append(warning_panel(
        "<p><strong>Version Isolation:</strong> v2 เป็น <strong>new modules ทั้งหมด</strong> (ไม่ reuse v1 code) &mdash; "
        "ทั้ง Player และ API อยู่ใน repo เดิมแต่ modules แยกกัน, DB schema แยก. "
        "v1 และ v2 ทำงาน <strong>พร้อมกันได้</strong> &mdash; rollout ทีละป้าย (canary), rollback ทันทีถ้ามีปัญหา.</p>"
    ))
    sections.append(info_panel(
        "<p><strong>Rollout strategy:</strong></p>"
        "<ul>"
        "<li><code>billboard.player_version: 'v1' | 'v2'</code> &mdash; สลับ version per billboard (ไม่ใช่ big bang)</li>"
        "<li>v1 ป้ายยังทำงานปกติขณะ v2 rollout &mdash; ไม่กระทบกัน</li>"
        "<li>เมื่อทุกป้ายอยู่บน v2 แล้ว → sunset v1 (Phase 5)</li>"
        "</ul>"
    ))
    sections.append(
        '<table>'
        '<tr><th>Phase</th><th>Backend (tathep-platform-api)</th><th>Player (bd-vision-player)</th><th>Risk</th></tr>'
        '<tr><td><strong>Phase 1</strong></td>'
        '<td>v2 modules: Ad Decisioning Engine + v2 DB schema (ScreenSchedule, etc.) + <code>GET /v3/screen-schedule</code></td>'
        '<td>v2 modules: Dumb Renderer + v2 Store + v2 Downloader (parallel, timeout, integrity)</td>'
        '<td>' + status_macro("v1 untouched", "Green") + '</td></tr>'
        '<tr><td><strong>Phase 2</strong></td>'
        '<td>v2 PoP endpoint (idempotency key) + v2 Pusher events (typed + versioned)</td>'
        '<td>v2 Outbox + Inbox handler</td>'
        '<td>' + status_macro("v1 untouched", "Green") + '</td></tr>'
        '<tr><td><strong>Phase 3</strong></td>'
        '<td>&mdash;</td>'
        '<td><strong>Canary rollout:</strong> สลับป้ายแรกไป v2. v1 ป้ายอื่นยังทำงานปกติ</td>'
        '<td>' + status_macro("1 billboard risk", "Yellow") + '</td></tr>'
        '<tr><td><strong>Phase 3.5</strong></td>'
        '<td>v2 TakeoverSchedule + ExactTimeSpot + MakeGoodRecord + TK Booking API</td>'
        '<td>v2 Interrupt Controller + local clock TK boundary + PoP interrupt fields</td>'
        '<td>' + status_macro("Medium risk", "Yellow") + '</td></tr>'
        '<tr><td><strong>Phase 4</strong></td>'
        '<td>&mdash;</td>'
        '<td><strong>Full rollout:</strong> สลับทุกป้ายไป v2 ทีละตัว</td>'
        '<td>' + status_macro("Gradual rollout", "Yellow") + '</td></tr>'
        '<tr><td><strong>Phase 5</strong></td>'
        '<td><strong>Sunset v1:</strong> ลบ v1 modules + v1 DB tables + v1 endpoints</td>'
        '<td><strong>Sunset v1:</strong> ลบ v1 modules + v1 localStorage logic</td>'
        '<td>' + status_macro("Cleanup", "Grey") + '</td></tr>'
        '<tr><td><strong>Phase 6</strong></td>'
        '<td>pDOOH: SSP integration, impression tracking (IAB), <code>GET /v3/avails</code></td>'
        '<td>No change (backend-only pDOOH)</td>'
        '<td>' + status_macro("Backend only", "Yellow") + '</td></tr>'
        '<tr><td><strong>Phase 7</strong></td>'
        '<td>Mediation layer: multi-SSP, floor price, preferred deals</td>'
        '<td>PoP format upgrade (IAB DOOH standard)</td>'
        '<td>' + status_macro("Revenue impact", "Red") + '</td></tr>'
        '</table>'
    )
    sections.append(note_panel(
        "<p><strong>Rollback procedure:</strong> ถ้า v2 มีปัญหาบนป้ายใดก็ตาม &mdash; "
        "เปลี่ยน <code>billboard.player_version</code> กลับเป็น <code>'v1'</code> ทันที. "
        "v1 code + DB ยังอยู่ครบ ไม่มีอะไรถูกลบจนกว่า Phase 5 (sunset). "
        "ไม่ต้อง rollback deployment &mdash; แค่สลับ config.</p>"
    ))

    sections.append("<hr/>")

    # ─── Terminology Reference (Old System ↔ DOOH Industry) ───
    sections.append("<h2>Terminology Reference (Tathep &harr; DOOH)</h2>")
    sections.append("<h3>ตาราง Mapping คำศัพท์: Tathep &harr; DOOH Industry</h3>")

    # Build all terminology content, then wrap in a single Expand
    _term_content = (
        info_panel(
            "<p>ตารางด้านล่างเชื่อมโยง<strong>คำศัพท์เดิมในระบบ</strong> (codebase + Jira) กับ<strong>คำใหม่</strong> "
            "ที่ใช้ใน architecture proposal นี้ ซึ่ง align กับมาตรฐาน DOOH industry<br/>"
            "เพื่อให้คนที่ทำระบบเดิมอยู่ กับคนที่จะทำ version ใหม่ เข้าใจตรงกัน</p>"
        )
    )

    _term_content += "<h4>Core Concepts</h4>"
    _term_content += (
        '<table>'
        '<tr><th>หมวด</th><th>คำเดิม (Current System)</th><th>คำใหม่ (DOOH Standard)</th><th>หมายเหตุ</th></tr>'
        '<tr><td rowspan="3"><strong>Ad Types</strong></td>'
        '<td><code>exclusive</code></td><td><strong>Guaranteed Spot (P1-G)</strong></td>'
        '<td>ชื่อใน code: <code>schedule.constant.ts</code> ยังเป็น <code>exclusive</code></td></tr>'
        '<tr><td><code>continuous</code> (date-range)</td><td><strong>Direct-Sold ROS (P2)</strong></td>'
        '<td>Run-of-Schedule &mdash; campaign ที่ขายตรง</td></tr>'
        '<tr><td><code>frequency</code> (count-based)</td><td><strong>Spot Buy (P3)</strong></td>'
        '<td>อนาคต: Programmatic via SSP/RTB</td></tr>'
        '<tr><td rowspan="2"><strong>Content</strong></td>'
        '<td>owner ads / owner playlist</td><td><strong>House Content (P4)</strong></td>'
        '<td>เจ้าของจอเลือกเอง เล่นตอนว่าง</td></tr>'
        '<tr><td>ads / media</td><td><strong>Creative (asset)</strong></td>'
        '<td><code>media_code</code> &rarr; <code>creative_code</code></td></tr>'
        '<tr><td rowspan="2"><strong>Screen</strong></td>'
        '<td>billboard</td><td><strong>Screen</strong></td>'
        '<td>DOOH standard &mdash; model ยังชื่อ <code>Billboard.ts</code></td></tr>'
        '<tr><td><code>ownerTime</code> / <code>platformTime</code></td><td><strong>SOV (Share of Voice)</strong></td>'
        '<td>สัดส่วนเวลา owner vs platform &mdash; logic เดิม rename</td></tr>'
        '<tr><td rowspan="2"><strong>Scheduling</strong></td>'
        '<td>round (5 min)</td><td><strong>Loop</strong></td>'
        '<td>DOOH เรียก loop cycle</td></tr>'
        '<tr><td>round-robin</td><td><strong>Loop Rotation</strong></td>'
        '<td>การหมุนเวียน creative ใน loop</td></tr>'
        '<tr><td><strong>Reporting</strong></td>'
        '<td>play history</td><td><strong>Proof of Play (PoP)</strong></td>'
        '<td>DOOH standard &mdash; endpoint ยังเป็น <code>/v2/play-history</code></td></tr>'
        '</table>'
    )

    _term_content += "<h4>Backend Components</h4>"
    _term_content += (
        '<table>'
        '<tr><th>คำเดิม (Current Code)</th><th>คำใหม่ (Proposed)</th><th>File Path</th></tr>'
        '<tr><td><code>PlaylistBuilderService</code></td><td><strong>AdDecisioningService</strong> (Ad Decisioning Engine)</td>'
        '<td><code>app/Services/AdDecisioningService.ts</code> (NEW)</td></tr>'
        '<tr><td><code>DevicePlaylist</code> model</td><td><strong>ScreenSchedule</strong></td>'
        '<td><code>app/Models/ScreenSchedule.ts</code> (NEW)</td></tr>'
        '<tr><td><code>DevicePlaylistItem</code> model</td><td><strong>ScreenScheduleItem</strong></td>'
        '<td><code>app/Models/ScreenScheduleItem.ts</code> (NEW)</td></tr>'
        '<tr><td><code>PlayScheduleExclusiveService</code></td><td>Absorbed into <strong>AdDecisioningService</strong></td>'
        '<td><code>app/Services/v2/PlayScheduleExclusiveService.ts</code></td></tr>'
        '<tr><td><code>PlayScheduleCreateByExclusive</code> (job)</td><td>Absorbed into <strong>AdDecisioningService</strong></td>'
        '<td><code>app/Jobs/PlayScheduleCreateByExclusive.ts</code></td></tr>'
        '<tr><td><code>PlayScheduleFrequencyService</code></td><td><strong>House content rotation</strong> (input to ADE)</td>'
        '<td><code>app/Services/PlayScheduleFrequencyService.ts</code></td></tr>'
        '<tr><td><code>PlaySchedulePeriodService</code></td><td><strong>Campaign period</strong> (input to ADE)</td>'
        '<td><code>app/Services/PlaySchedulePeriodService.ts</code></td></tr>'
        '<tr><td><code>GET /v2/play-schedules</code> + <code>/playlist-advertisements</code></td>'
        '<td><strong><code>GET /v3/screen-schedule</code></strong> (v2 new endpoint)</td>'
        '<td>v2 endpoint แยกจาก v1 routes</td></tr>'
        '<tr><td><code>AdvertisementDisplayExclusive</code></td><td>Remains (data source for <strong>guaranteed spots</strong>)</td>'
        '<td><code>app/Models/AdvertisementDisplayExclusive.ts</code></td></tr>'
        '<tr><td><code>AdGroupDisplayTimeExclusive</code></td><td>Remains (data source for <strong>guaranteed time window</strong>)</td>'
        '<td><code>app/Models/AdGroupDisplayTimeExclusive.ts</code></td></tr>'
        '<tr><td colspan="3"><em>v1 references (ไม่ reuse code):</em> <code>PlayScheduleCalculate.ts</code>, '
        '<code>PlayScheduleCalculatePerScreen.ts</code>, <code>PlaySchedule.ts</code>, '
        '<code>checkIsBillboardsReserved.ts</code> &mdash; v2 จะเขียนใหม่ทั้งหมด</td></tr>'
        '</table>'
    )

    _term_content += "<h4>Player Components</h4>"
    _term_content += (
        '<table>'
        '<tr><th>คำเดิม (Current Code)</th><th>คำใหม่ (Proposed)</th><th>หมายเหตุ</th></tr>'
        '<tr><td>Smart Player (schedule + render)</td><td><strong>Dumb Renderer</strong> (play <code>sequence[i++]</code>)</td>'
        '<td>Feature flag: <code>billboard.player_mode</code></td></tr>'
        '<tr><td><code>SchedulePlayComponent</code><br/><code>TimeSlotComponent</code><br/><code>PlaylistComponent</code></td>'
        '<td>Absorbed into <strong>Dumb Renderer</strong></td>'
        '<td>3,500+ lines &rarr; simple sequence player</td></tr>'
        '<tr><td><code>calculatePlaySchedules</code> (1s poll)</td><td><strong>Eliminated</strong> &mdash; backend pre-positions</td>'
        '<td>ไม่ต้อง poll ทุก 1 วินาทีอีก</td></tr>'
        '<tr><td><code>pausePlayData</code> (single var)</td><td><strong>Eliminated</strong> &mdash; no nested interrupt</td>'
        '<td>ADE resolves ที่ backend แทน</td></tr>'
        '<tr><td>(no name)</td><td><strong>Interrupt Controller (IC)</strong></td>'
        '<td>NEW: P0/P1-TK/P1-ET interrupt only</td></tr>'
        '<tr><td>(no name)</td><td><strong>Inbox Handler</strong></td>'
        '<td>NEW: event_id dedup + version check</td></tr>'
        '<tr><td><code>player.history.json</code> (retry)</td><td><strong>PoP Outbox</strong></td>'
        '<td>pending &rarr; sent &rarr; acked cycle</td></tr>'
        '<tr><td><code>localStorage</code></td><td><strong>3-Tier Cache</strong> (Tauri Store)</td>'
        '<td>Tier 1: Live, Tier 2: Buffer, Tier 3: Fallback</td></tr>'
        '<tr><td>(implicit states)</td><td><strong>State Machine</strong> (10 explicit states)</td>'
        '<td>BOOT &rarr; SPLASH &rarr; SYNC &rarr; ONLINE/OFFLINE &rarr; FALLBACK</td></tr>'
        '</table>'
    )

    _term_content += "<h4>Pusher Events</h4>"
    _term_content += (
        '<table>'
        '<tr><th>Event เดิม</th><th>Event ใหม่ / เปลี่ยนแปลง</th><th>หมายเหตุ</th></tr>'
        '<tr><td><code>update-play-schedule</code></td><td><strong><code>schedule-updated</code></strong></td>'
        '<td>Renamed + typed contract</td></tr>'
        '<tr><td><code>created-play-schedule</code></td><td>Absorbed into <strong><code>schedule-updated</code></strong></td>'
        '<td>ไม่แยก create/update อีก</td></tr>'
        '<tr><td><code>approved-advertisement-exclusive</code></td><td>Absorbed into <strong><code>schedule-updated</code></strong></td>'
        '<td>ADE pre-positions guaranteed &mdash; ไม่ inject ตรง</td></tr>'
        '<tr><td><code>stop-advertisement</code></td><td>Unchanged (+ typed contract)</td>'
        '<td>Creative cancelled</td></tr>'
        '<tr><td><code>un-pair-screen</code></td><td>Unchanged (+ typed contract)</td>'
        '<td>Device unpaired</td></tr>'
        '<tr><td>(ไม่มี)</td><td><strong><code>takeover-start</code></strong></td><td>NEW: P1-TK boundary</td></tr>'
        '<tr><td>(ไม่มี)</td><td><strong><code>takeover-end</code></strong></td><td>NEW: P1-TK boundary</td></tr>'
        '<tr><td>(ไม่มี)</td><td><strong><code>p0-emergency</code></strong></td><td>NEW: system alert</td></tr>'
        '<tr><td>(ไม่มี)</td><td><strong><code>device-config-updated</code></strong></td><td>NEW: pre-stage creative</td></tr>'
        '</table>'
    )

    _term_content += "<h4>API &amp; Data Fields</h4>"
    _term_content += (
        '<table>'
        '<tr><th>Field / API เดิม</th><th>ใหม่</th><th>หมายเหตุ</th></tr>'
        '<tr><td><code>media_code</code></td><td><strong><code>creative_code</code></strong></td>'
        '<td>DOOH: creative = ชิ้นงานโฆษณา</td></tr>'
        '<tr><td><code>media_url</code></td><td><strong><code>creative_url</code></strong></td><td></td></tr>'
        '<tr><td><code>media_checksum</code></td><td><strong><code>creative_checksum</code></strong></td><td></td></tr>'
        '<tr><td><code>media_manifest</code></td><td><strong><code>creative_manifest</code></strong></td><td></td></tr>'
        '<tr><td><code>type: "paid" | "owner"</code></td>'
        '<td><strong><code>type: "campaign" | "house"</code></strong></td>'
        '<td>campaign = sold inventory</td></tr>'
        '<tr><td><code>priority: "normal" | "exclusive"</code></td>'
        '<td><strong><code>priority: "guaranteed" | "direct" | "spot" | "house"</code></strong></td>'
        '<td>4-level แทน 2-level</td></tr>'
        '<tr><td><code>ad_display_count</code></td><td><strong><code>impression_target</code></strong></td>'
        '<td>DOOH: impression = 1 play ที่นับได้</td></tr>'
        '<tr><td><code>PlaylistUpdatedEvent</code></td><td><strong><code>ScheduleUpdatedEvent</code></strong></td>'
        '<td>Interface ใหม่</td></tr>'
        '</table>'
    )

    _term_content += note_panel(
        "<p><strong>Version Isolation:</strong> v2 จะสร้าง modules ใหม่ทั้งหมด &mdash; "
        "ไม่ rename หรือ refactor v1 code. v1 models (<code>PlaySchedule</code>, <code>AdvertisementDisplayExclusive</code>, etc.) "
        "ยังคงอยู่ใน codebase เดิมและทำงานปกติจนกว่า v1 จะถูก sunset (Phase 5). "
        "Mapping นี้แสดง <em>terminology</em> ที่จะใช้ใน v2 modules ใหม่.</p>"
    )

    sections.append(expand_section(
        "Terminology Mapping: 5 tables (Core, Backend, Player, Pusher, API)",
        _term_content
    ))

    sections.append("<hr/>")
    sections.append("<h2>Edge Cases ของ Daypart Targeting (DP1-DP7)</h2>")
    sections.append(expand_section("DP1-DP7: Daypart Window Edge Cases",
        '<table>'
        '<tr><th>#</th><th>Edge Case</th><th>Solution</th></tr>'
        '<tr><td>DP1</td><td><strong>Daypart windows ทับซ้อนกัน</strong></td>'
        '<td>Reject at booking — "windows must not overlap". UI แนะนำให้ merge windows ที่อยู่ติดกัน</td></tr>'
        '<tr><td>DP2</td><td><strong>Window ข้ามเที่ยงคืน</strong></td>'
        '<td>Phase 1: ไม่ support — validate <code>endTime &gt; startTime</code>. Production data ยืนยัน: ไม่มีป้ายที่เปิดข้ามคืน (max close: 22:00)</td></tr>'
        '<tr><td>DP3</td><td><strong>plays × creative_length &gt; window_duration</strong></td>'
        '<td>Warning (ไม่ reject) — plays ถูก pack แน่นใน window. โฆษณา P2/P3 อื่นอาจถูก squeeze. แจ้ง advertiser ที่ booking confirmation</td></tr>'
        '<tr><td>DP4</td><td><strong>playsPerHour คำนวณ plays ได้ 0 ใน window</strong></td>'
        '<td>ตัวอย่าง: 1 play/hr, window 20 นาที → round(1 × 20/60) = 0. Validation: plays_in_window ต้อง &ge; 1 ไม่อนุญาต booking ที่ไม่มี play เลย</td></tr>'
        '<tr><td>DP5</td><td><strong>ต้องการเปลี่ยน window order/time หลัง approve</strong></td>'
        '<td>ไม่อนุญาต — ต้อง cancel + rebook. UI แสดง "window locked after approval" warning ก่อน approve</td></tr>'
        '<tr><td>DP6</td><td><strong>Multi-billboard campaign, window ต่างกันต่อป้าย</strong></td>'
        '<td>Phase 1: แยก AdGroup ต่อ billboard (industry standard — Broadsign/Xibo/Doohly ทุกเจ้าใช้ pattern นี้). Parent Campaign container สำหรับ aggregate reporting</td></tr>'
        '<tr><td>DP7</td><td><strong>playsPerHour เปลี่ยนหลังจาก windows ถูก configure</strong></td>'
        '<td>plays_in_window คำนวณใหม่ทุกครั้ง: <code>round(playsPerHour × windowHours)</code> → แสดง recalculated value ที่ confirm screen ก่อน approve</td></tr>'
        '</table>'
    ))

    return "\n".join(sections)


# ─── Gantt Legend (shared across pages with Gantt diagrams: 1, 8, 14) ───


def _gantt_legend_mini() -> str:
    """Compact inline Gantt legend — plain text with emoji."""
    return (
        "<p><strong>Legend:</strong> "
        "🔴 แดง = P1 Priority (TK/ET/G/DG) &nbsp;&middot;&nbsp; "
        "🔵 ฟ้า = Make-good &nbsp;&middot;&nbsp; "
        "⬜ เทา = Normal ROS &nbsp;&middot;&nbsp; "
        "🟦 น้ำเงินเข้ม = เส้นขอบเขต &nbsp;&middot;&nbsp; "
        "◆ = Milestone</p>"
    )


def _gantt_legend() -> str:
    """Gantt chart legend — bullet list with emoji."""
    return (
        "<p><strong>Legend:</strong></p>"
        "<ul>"
        "<li>🔴 แดง = P1 Priority: TK Takeover / ET Exact Time / G Guaranteed / DG Daypart</li>"
        "<li>🔵 ฟ้า = Make-good compensation</li>"
        "<li>⬜ เทา = โฆษณาปกติที่ผ่านมาแล้ว (Normal ROS)</li>"
        "<li>🟢 เขียว = Normal fills (default)</li>"
        "<li>🟦 น้ำเงินเข้ม = เส้นขอบเขต (TK_START/END, ET Window, DG Window)</li>"
        "<li>◆ = จุดเหตุการณ์ (Milestone)</li>"
        "</ul>"
    )


# ─── Event Storming Legend (shared across pages 9-11) ───


def _es_legend() -> str:
    """Event Storming notation legend table (shape-based)."""
    return (
        '<table>'
        '<tr><th>Element</th><th>Shape</th><th>Meaning</th></tr>'
        '<tr><td><strong>Domain Event</strong></td>'
        '<td><code>[text]</code> rectangle</td><td>สิ่งที่เกิดขึ้นแล้ว (past tense) &mdash; state change ใน domain</td></tr>'
        '<tr><td><strong>Command</strong></td>'
        '<td><code>[text]</code> rectangle</td><td>Action ที่ trigger event (imperative verb)</td></tr>'
        '<tr><td><strong>Aggregate</strong></td>'
        '<td><code>[text]</code> rectangle</td><td>Entity/service ที่ประมวลผล command แล้วสร้าง event</td></tr>'
        '<tr><td><strong>Policy</strong></td>'
        '<td><code>{{text}}</code> hexagon</td><td>Business rule: &ldquo;เมื่อ X เกิดขึ้น ให้ทำ Y&rdquo;</td></tr>'
        '<tr><td><strong>Actor</strong></td>'
        '<td><code>([text])</code> stadium</td><td>คนหรือ role ในระบบที่เริ่มต้น command</td></tr>'
        '<tr><td><strong>External System</strong></td>'
        '<td><code>[(text)]</code> cylinder</td><td>ระบบภายนอกที่เราควบคุมไม่ได้ (Pusher, CDN, etc.)</td></tr>'
        '<tr><td><strong>Read Model</strong></td>'
        '<td><code>[/text/]</code> parallelogram</td><td>ข้อมูลที่ต้องดูก่อนตัดสินใจ ก่อน issue command</td></tr>'
        '</table>'
    )


def build_page_9(page_id: str) -> str:
    """Page 9: Event Storming — Big Picture (1 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Event Storming: ภาพรวม (Big Picture)</h2>")
    sections.append(info_panel(
        "<p><strong>Event Storming Level 1 &mdash; Big Picture</strong><br/>"
        "ภาพรวม domain events ทั้งระบบ Backend-Driven Player &mdash; "
        "จัดตาม swimlane (Scheduling, Playback, Interrupt, Device Lifecycle)<br/>"
        "อ้างอิง methodology ของ Alberto Brandolini &mdash; "
        "ใช้ shape-coded nodes แทน sticky notes</p>"
    ))

    # Legend
    sections.append("<h3>สัญลักษณ์ที่ใช้ (Notation Legend)</h3>")
    sections.append(expand_section("ES Notation Legend (8 elements)", _es_legend()))

    # Big Picture Timeline
    sections.append("<h3>Timeline ของ Domain Events</h3>")
    sections.append(note_panel(
        "<p>อ่านจาก <strong>ซ้ายไปขวา</strong> ตาม timeline &mdash; "
        "แต่ละ swimlane แสดง flow ของ domain events ที่เกี่ยวข้องกัน<br/>"
        "<strong>เส้นประ</strong> = cross-swimlane event flow (Pusher/API)</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("09-1-big-picture.mmd"),
        page_id=page_id,
    ))

    # Actors
    sections.append("<h3>ผู้กระทำ (Actors)</h3>")
    sections.append(
        '<table>'
        '<tr><th>Actor</th><th>Type</th><th>Description</th></tr>'
        '<tr><td><strong>Cron</strong></td><td>System</td>'
        '<td>BullMQ scheduled job &mdash; trigger คำนวณ schedule ทุก 5 นาที + event-driven trigger</td></tr>'
        '<tr><td><strong>Admin</strong></td><td>Human</td>'
        '<td>Admin ของ platform &mdash; approve takeover, trigger emergency, จัดการจอ</td></tr>'
        '<tr><td><strong>Player</strong></td><td>Device</td>'
        '<td>Tauri desktop app บนจอโฆษณา &mdash; รับ schedule, เล่น creative, รายงาน PoP</td></tr>'
        '</table>'
    )

    # External Systems
    sections.append("<h3>ระบบภายนอก (External Systems)</h3>")
    sections.append(
        '<table>'
        '<tr><th>System</th><th>Role</th><th>Protocol</th></tr>'
        '<tr><td><strong>Pusher</strong></td><td>ส่ง event แบบ real-time</td><td>WebSocket</td></tr>'
        '<tr><td><strong>BullMQ</strong></td><td>Job queue / cron scheduler</td><td>Redis-backed queue</td></tr>'
        '<tr><td><strong>Redis</strong></td><td>Caching + ป้องกัน duplicate</td><td>In-memory store</td></tr>'
        '<tr><td><strong>CDN</strong></td><td>ส่งไฟล์ creative</td><td>HTTPS</td></tr>'
        '<tr><td><strong>Tauri Store</strong></td><td>เก็บข้อมูลบน device</td><td>File-based (device)</td></tr>'
        '</table>'
    )

    # Hot Spots
    sections.append("<h3>จุดเสี่ยง (Hot Spots)</h3>")
    sections.append(warning_panel(
        "<p><strong>ความเสี่ยงและประเด็นที่ยังไม่ได้แก้:</strong></p>"
        "<ul>"
        "<li><s><strong>Version gap threshold</strong> &mdash; "
        "gap กี่ version ถึงจะส่ง full playlist แทน delta?</s> "
        "<strong>แก้แล้ว:</strong> gap &gt; 3 versions &rarr; full replace (ดู Section 4: Algorithm)</li>"
        "<li><strong>ระยะเวลา Offline สูงสุด</strong> &mdash; "
        "player ใช้ Tier 3 fallback ได้นานแค่ไหนก่อน content จะ stale? (วัน? สัปดาห์?)</li>"
        "<li><strong>Takeover ทับกัน</strong> &mdash; "
        "ถ้า 2 takeover จองช่วงเวลาทับกันบนจอเดียว? (ปัจจุบัน: block ตอนจอง)</li>"
        "<li><strong>การจัดลำดับ Make-good ให้เท่าเทียม</strong> &mdash; "
        "จัดลำดับ make-good ยังไงเมื่อหลาย ad โดน interrupt ใน TK block เดียว?</li>"
        "<li><strong>ความเสถียรของ Pusher</strong> &mdash; "
        "Pusher เป็น best-effort delivery &mdash; version protocol จัดการ gap ได้ แต่ latency ไม่แน่นอน</li>"
        "</ul>"
    ))

    return "\n".join(sections)


def build_page_10(page_id: str) -> str:
    """Page 10: Event Storming — Process Modelling (5 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Event Storming: Process Modelling</h2>")
    sections.append(info_panel(
        "<p><strong>Event Storming Level 2 &mdash; Process Modelling</strong><br/>"
        "แต่ละ process แสดง flow ตาม grammar: "
        "<strong>Actor &rarr; Command &rarr; Aggregate &rarr; Event &rarr; Policy &rarr; ...</strong><br/>"
        "Read Models (green) แสดงข้อมูลที่ต้องใช้ก่อนตัดสินใจ</p>"
    ))

    # Legend
    sections.append("<h3>สัญลักษณ์ที่ใช้ (Notation Legend)</h3>")
    sections.append(expand_section("ES Notation Legend (8 elements)", _es_legend()))

    # Process A: Schedule Calculation
    sections.append("<hr/>")
    sections.append("<h3>Process A: คำนวณ Schedule</h3>")
    sections.append(note_panel(
        "<p><strong>Trigger:</strong> Cron ทำงานทุก 5 นาที + event-driven trigger<br/>"
        "<strong>ผลลัพธ์:</strong> Ordered screen schedule ถูก push ไปยัง player ผ่าน Pusher<br/>"
        "<strong>Grammar:</strong> Cron &rarr; CalculateSchedule &rarr; PlaySchedule &rarr; "
        "ScheduleCalculated &rarr; <em>BuildScreenSchedule</em> &rarr; AdDecisioningService &rarr; "
        "ScreenScheduleBuilt &rarr; <em>PushToPlayer</em> &rarr; Pusher</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("10-1-process-schedule-calc.mmd"),
        page_id=page_id,
    ))

    # Process B: Normal Playback
    sections.append("<hr/>")
    sections.append("<h3>Process B: เล่นปกติ (Normal Playback)</h3>")
    sections.append(note_panel(
        "<p><strong>Trigger:</strong> Player ได้รับ schedule-updated event จาก Pusher<br/>"
        "<strong>ผลลัพธ์:</strong> Creative เล่นบนจอ + PoP (Proof of Play) รายงานกลับ backend<br/>"
        "<strong>Policy สำคัญ:</strong> Inbox dedup ด้วย event_id + ตรวจ version ก่อน fetch</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("10-2-process-normal-play.mmd"),
        page_id=page_id,
    ))

    # Process C: Takeover Interrupt
    sections.append("<hr/>")
    sections.append("<h3>Process C: Interrupt จาก Takeover (P1-TK)</h3>")
    sections.append(note_panel(
        "<p><strong>Trigger:</strong> Admin approve Takeover block (P1-TK: brand จอง exclusive slot เช่น 08:00-09:00)<br/>"
        "<strong>ผลลัพธ์:</strong> Ad ปัจจุบันโดน interrupt, takeover creative เล่นตลอด block, "
        "ad ที่โดน interrupt ได้ make-good compensation<br/>"
        "<strong>ข้ามขอบเขต:</strong> Backend (approve + schedule) &rarr; Pusher &rarr; Player (interrupt + เล่น)</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("10-3-process-takeover.mmd"),
        page_id=page_id,
    ))

    # Process D: Offline & Reconnect
    sections.append("<hr/>")
    sections.append("<h3>Process D: Offline และเชื่อมต่อใหม่</h3>")
    sections.append(note_panel(
        "<p><strong>Trigger:</strong> เน็ตหลุด (Pusher disconnect)<br/>"
        "<strong>ผลลัพธ์:</strong> ลดระดับอย่างค่อยเป็นค่อยไป (graceful degradation) ผ่าน 3-tier cache แล้ว delta sync ตอนกลับมา online<br/>"
        "<strong>Policy สำคัญ:</strong> State Machine transitions: ONLINE &rarr; OFFLINE &rarr; FALLBACK &rarr; ONLINE</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("10-4-process-offline.mmd"),
        page_id=page_id,
    ))

    # Process E: Emergency (P0)
    sections.append("<hr/>")
    sections.append("<h3>Process E: Emergency Override (P0)</h3>")
    sections.append(note_panel(
        "<p><strong>Trigger:</strong> Admin trigger P0 emergency (ประกาศราชการ, วิกฤต, ฯลฯ)<br/>"
        "<strong>ผลลัพธ์:</strong> Interrupt content ใดๆ ทันที, เล่น emergency creative, schedule make-good<br/>"
        "<strong>Priority:</strong> P0 ชนะทุกอย่าง &mdash; รวมถึง takeover ที่กำลังทำงานอยู่</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("10-5-process-emergency.mmd"),
        page_id=page_id,
    ))

    return "\n".join(sections)


def build_page_11(page_id: str) -> str:
    """Page 11: Event Storming — Software Design (2 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())
    sections.append("<h2>Event Storming: การออกแบบ Software</h2>")
    sections.append(info_panel(
        "<p><strong>Event Storming Level 3 &mdash; Software Design</strong><br/>"
        "Bounded Contexts, Aggregates, and Context Mapping &mdash; "
        "จาก Process Modelling (Level 2) มาจัดกลุ่มเป็น architectural boundaries</p>"
    ))

    # Legend
    sections.append("<h3>สัญลักษณ์ที่ใช้ (Notation Legend)</h3>")
    sections.append(expand_section("ES Notation Legend (8 elements)", _es_legend()))

    # Bounded Context Map
    sections.append("<hr/>")
    sections.append("<h3>แผนที่ Bounded Context</h3>")
    sections.append(note_panel(
        "<p>4 Bounded Contexts &mdash; แต่ละ context มี aggregates ที่ทำงานร่วมกัน<br/>"
        "ลูกศรระหว่าง context = event ที่ส่งข้ามขอบเขต (via Pusher หรือ API call)</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("11-1-context-map.mmd"),
        page_id=page_id,
    ))

    # Aggregates per Context
    sections.append("<h3>Aggregate แยกตาม Context</h3>")

    # Scheduling Context
    sections.append("<h4>Scheduling Context (Backend)</h4>")
    sections.append(
        '<table>'
        '<tr><th>Aggregate</th><th>Responsibility</th><th>Key Invariants</th><th>Events Owned</th></tr>'
        '<tr><td><strong>PlaySchedule</strong></td>'
        '<td>ผลลัพธ์จากการคำนวณ schedule (ต่อจอ ต่อรอบ cron)</td>'
        '<td>1 active schedule ต่อจอต่อรอบ</td>'
        '<td>ScheduleCalculated</td></tr>'
        '<tr><td><strong>AdDecisioningService</strong></td>'
        '<td>จัดลำดับตาม priority, สลับ house content, กำหนด sequence_no, version++</td>'
        '<td>P1-G pre-positioned, P1-DG center-offset กระจายใน window, P2/P3 ตาม SOV ratio, P4 เติมช่องว่าง</td>'
        '<td>ScreenScheduleBuilt</td></tr>'
        '<tr><td><strong>ScreenSchedule</strong></td>'
        '<td>Ordered playlist พร้อม versioning (เพิ่มขึ้นเรื่อยๆ ต่อ device)</td>'
        '<td>version เพิ่มขึ้นเสมอ, schedule เก่าถูก mark &ldquo;replaced&rdquo;</td>'
        '<td>(persisted state)</td></tr>'
        '</table>'
    )

    # Interrupt Context
    sections.append("<h4>Interrupt Context (Backend + Player)</h4>")
    sections.append(
        '<table>'
        '<tr><th>Aggregate</th><th>Responsibility</th><th>Key Invariants</th><th>Events Owned</th></tr>'
        '<tr><td><strong>TakeoverSchedule</strong></td>'
        '<td>จอง exclusive time block (P1-TK: brand ซื้อ time slot ทั้งหมดบนจอ)</td>'
        '<td>TK ซ้อนกันบนจอเดียวไม่ได้, lifecycle: booked &rarr; active &rarr; completed</td>'
        '<td>TakeoverApproved, TakeoverStateChanged</td></tr>'
        '<tr><td><strong>ExactTimeSpot</strong></td>'
        '<td>P1-ET: เล่นตรงเวลาพร้อม tolerance window</td>'
        '<td>tolerance default 5s, 1 spot ต่อ play_at ต่อจอ</td>'
        '<td>(triggers InterruptController)</td></tr>'
        '<tr><td><strong>InterruptController</strong></td>'
        '<td>หยุด ad ปัจจุบัน, เล่น interrupt creative, resume หลังจบ</td>'
        '<td>ลำดับ priority: P0 > P1-TK > P1-ET, nested interrupt เข้าคิว</td>'
        '<td>AdInterrupted</td></tr>'
        '<tr><td><strong>MakeGoodRecord</strong></td>'
        '<td>ชดเชย ad ที่โดน interrupt &mdash; ใส่คืนใน cycle ถัดไป</td>'
        '<td>1 make-good ต่อ 1 interruption, ข้ามถ้า campaign หมดอายุ</td>'
        '<td>MakeGoodScheduled</td></tr>'
        '</table>'
    )

    # Playback Context
    sections.append("<h4>Playback Context (Player)</h4>")
    sections.append(
        '<table>'
        '<tr><th>Aggregate</th><th>Responsibility</th><th>Key Invariants</th><th>Events Owned</th></tr>'
        '<tr><td><strong>InboxHandler</strong></td>'
        '<td>รับ Pusher event, dedup ด้วย event_id, ตรวจ version</td>'
        '<td>ประมวลผลเฉพาะ version > local_version และ event_id ใหม่</td>'
        '<td>ScheduleReceived</td></tr>'
        '<tr><td><strong>3-Tier Cache</strong></td>'
        '<td>เก็บบน device: Tier 1 (live) &rarr; Tier 2 (buffer) &rarr; Tier 3 (fallback/house)</td>'
        '<td>Tier 1 ต้องเป็น version ล่าสุด, Tier 3 พร้อมเสมอ (house loop)</td>'
        '<td>CacheUpdated</td></tr>'
        '<tr><td><strong>StateMachine</strong></td>'
        '<td>BOOT &rarr; CACHED &rarr; SYNC &rarr; ONLINE &rarr; OFFLINE &rarr; FALLBACK</td>'
        '<td>อยู่ได้ 1 state พร้อมกัน, log ทุก transition, กำหนดทาง recovery ไว้</td>'
        '<td>DeviceResynced</td></tr>'
        '<tr><td><strong>Renderer</strong></td>'
        '<td>Dumb Renderer: เล่น sequence[i++], ไม่มี logic จัดลำดับ</td>'
        '<td>เล่นตาม cache ให้มา, ไม่ข้าม, ไม่สลับลำดับ</td>'
        '<td>CreativePlayed</td></tr>'
        '</table>'
    )

    # Reporting Context
    sections.append("<h4>Reporting Context (Player &rarr; Backend)</h4>")
    sections.append(
        '<table>'
        '<tr><th>Aggregate</th><th>Responsibility</th><th>Key Invariants</th><th>Events Owned</th></tr>'
        '<tr><td><strong>PoP Outbox</strong></td>'
        '<td>เก็บ play event บน device, flush ไป backend ทุก 1 นาที</td>'
        '<td>lifecycle: pending &rarr; sent &rarr; acked, retry &lt; 10 ครั้ง</td>'
        '<td>PoPRecorded</td></tr>'
        '<tr><td><strong>PlayHistory</strong></td>'
        '<td>เก็บ PoP records ฝั่ง backend</td>'
        '<td>ป้องกัน duplicate ด้วย X-Idempotency-Key (UUID)</td>'
        '<td>PoPReceived</td></tr>'
        '<tr><td><strong>Idempotency</strong></td>'
        '<td>ป้องกัน duplicate ผ่าน Redis สำหรับ PoP endpoint</td>'
        '<td>Key หมดอายุ 24 ชม. (TTL-based), ป้องกันข้อมูลซ้ำ</td>'
        '<td>(guard, ไม่สร้าง event)</td></tr>'
        '</table>'
    )

    # Context Relationships
    sections.append("<hr/>")
    sections.append("<h3>ความสัมพันธ์ระหว่าง Context</h3>")
    sections.append(
        '<table>'
        '<tr><th>From</th><th>To</th><th>Event</th><th>Mechanism</th><th>Relationship Type</th></tr>'
        '<tr><td>Scheduling</td><td>Playback</td>'
        '<td>ScreenScheduleBuilt</td><td>Pusher WebSocket</td><td>Published Language</td></tr>'
        '<tr><td>Interrupt</td><td>Playback</td>'
        '<td>TakeoverStart / TakeoverEnd</td><td>Pusher WebSocket</td><td>Published Language</td></tr>'
        '<tr><td>Playback</td><td>Reporting</td>'
        '<td>PoPRecorded</td><td>HTTP (Outbox flush)</td><td>Conformist</td></tr>'
        '<tr><td>Interrupt</td><td>Scheduling</td>'
        '<td>MakeGoodScheduled</td><td>Internal (same backend)</td><td>Shared Kernel</td></tr>'
        '<tr><td>Reporting</td><td>Scheduling</td>'
        '<td>(future: analytics feedback)</td><td>TBD</td><td>TBD</td></tr>'
        '</table>'
    )

    # ACL Diagram
    sections.append("<hr/>")
    sections.append("<h3>Anti-Corruption Layer: ระบบเดิมสู่ระบบใหม่</h3>")
    sections.append(note_panel(
        "<p>ACL (Anti-Corruption Layer) &mdash; translation boundary ระหว่างระบบเดิมกับ architecture ใหม่<br/>"
        "Legacy code จะยังทำงานเหมือนเดิม แต่ output ถูก translate เป็น new domain model ผ่าน ACL<br/>"
        "เมื่อ migration เสร็จ ACL จะถูกถอดออก</p>"
    ))
    sections.append(mermaid_diagram(
        load_diagram("11-2-acl-translation.mmd"),
        page_id=page_id,
    ))

    return "\n".join(sections)


def build_page_12(page_id: str) -> str:
    """Page 12: Use Case — Ad Distribution & Scheduling Cycle (2 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())

    # ─── Intro ───
    sections.append(info_panel(
        "<p><strong>Use Case Reference:</strong> หน้านี้อธิบายการทำงานจริงของ Ad Scheduling System "
        "ผ่าน scenario ที่สมจริง — 10 ads ความยาวต่างกัน, เป้า 5 ครั้ง/hr, "
        "ป้ายเปิด 07:00-22:00 ทุกวัน</p>"
    ))

    # ─── Section 1: Ad Distribution ───
    sections.append('<h2>1. การกระจาย Ad บนป้าย (Ad Distribution)</h2>')

    sections.append('<h3>Scenario</h3>')
    sections.append(
        '<p>ป้าย 1 จอ, เปิด 07:00-22:00 (15 ชม.), เป้าหมายแต่ละ ad เล่น '
        '<strong>5 ครั้ง/hr</strong>, SOV ratio = owner 40% : platform 60%</p>'
    )

    sections.append('<h3>Ad Mix (10 ads)</h3>')
    sections.append("""<table>
<tr><th>Ad</th><th>ลูกค้า (สมมติ)</th><th>Duration</th><th>Priority</th><th>หมายเหตุ</th></tr>
<tr><td>Ad-A</td><td>แบรนด์ใหญ่ A</td><td><strong>30s</strong></td><td>P2 (Direct-Sold)</td><td>TVC repurpose</td></tr>
<tr><td>Ad-B</td><td>แบรนด์ใหญ่ B</td><td><strong>20s</strong></td><td>P2 (Direct-Sold)</td><td>Product launch</td></tr>
<tr><td>Ad-C</td><td>ร้านอาหารใกล้จอ</td><td><strong>15s</strong></td><td>P2 (Direct-Sold)</td><td>Local business</td></tr>
<tr><td>Ad-D</td><td>แบรนด์ C</td><td><strong>15s</strong></td><td>P2 (Direct-Sold)</td><td>Standard spot</td></tr>
<tr><td>Ad-E</td><td>Guaranteed client</td><td><strong>15s</strong></td><td><strong>P1-G</strong></td><td>จองตำแหน่งตรงเวลา</td></tr>
<tr><td>Ad-F</td><td>แบรนด์ D</td><td><strong>10s</strong></td><td>P3 (Spot Buy)</td><td>Short bumper</td></tr>
<tr><td>Ad-G</td><td>แบรนด์ E</td><td><strong>10s</strong></td><td>P3 (Spot Buy)</td><td>Short bumper</td></tr>
<tr><td>Ad-H</td><td>แบรนด์ F</td><td><strong>20s</strong></td><td>P2 (Direct-Sold)</td><td>Seasonal promo</td></tr>
<tr><td>Ad-I</td><td>แบรนด์ G</td><td><strong>15s</strong></td><td>P3 (Spot Buy)</td><td>Impression-based</td></tr>
<tr><td>Ad-J</td><td>เจ้าของป้าย</td><td><strong>10s</strong></td><td>P4 (House)</td><td>Self-promo filler</td></tr>
</table>""")

    sections.append('<h3>คำนวณ Loop Duration</h3>')
    sections.append("""<table>
<tr><th>Parameter</th><th>Value</th><th>สูตร</th></tr>
<tr><td>Campaign ads (A-I) รวม</td><td>150s</td><td>30+20+15+15+15+10+10+20+15</td></tr>
<tr><td>เป้า frequency</td><td>5 ครั้ง/hr</td><td>กำหนดโดยลูกค้า</td></tr>
<tr><td>Loop duration ที่ต้องการ</td><td><strong>720s (12 นาที)</strong></td><td>3,600 / 5 = 720</td></tr>
<tr><td>Filler time ต่อ loop</td><td><strong>570s</strong></td><td>720 - 150 = 570</td></tr>
<tr><td>Filler items ต่อ loop</td><td>~46 items</td><td>570 / avg 12.5s</td></tr>
<tr><td>Total items ต่อ loop</td><td>~55 items</td><td>9 campaign + 46 filler</td></tr>
</table>""")

    sections.append('<h3>SOV Interleave</h3>')
    sections.append(
        '<p><strong>SOV ratio:</strong> owner 40% : platform 60%</p>'
        '<p><code>interleaveEvery = Math.round(1 / 0.4) = 3</code> '
        '&rarr; ทุก 3 campaign ads ใส่ house filler 1 ตัว '
        '+ filler เพิ่มเติมเพื่อยืด loop ให้ครบ 720s</p>'
    )

    sections.append('<h3>ตัวอย่าง Ordered Sequence (1 Loop = 720s)</h3>')
    sections.append(expand_section("ดูตัวอย่าง Sequence เต็ม", """<table>
<tr><th>Seq</th><th>Ad</th><th>Duration</th><th>Type</th><th>Cumulative Time</th></tr>
<tr><td>1</td><td>Ad-E (P1-G)</td><td>15s</td><td>Guaranteed</td><td>0:00</td></tr>
<tr><td>2-4</td><td>Filler 1-3</td><td>10-15s</td><td>House</td><td>0:15-0:40</td></tr>
<tr><td>5</td><td>Ad-A</td><td>30s</td><td>Campaign</td><td>0:55</td></tr>
<tr><td>6-8</td><td>Filler 4-6</td><td>10-15s</td><td>House</td><td>1:25-1:50</td></tr>
<tr><td>9</td><td>Ad-B</td><td>20s</td><td>Campaign</td><td>2:05</td></tr>
<tr><td>10-12</td><td>Filler 7-9</td><td>10-15s</td><td>House</td><td>2:25-2:50</td></tr>
<tr><td>13</td><td>Ad-C</td><td>15s</td><td>Campaign</td><td>3:00</td></tr>
<tr><td>14-16</td><td>Filler 10-12</td><td>10-15s</td><td>House</td><td>3:15-3:40</td></tr>
<tr><td>17</td><td>Ad-D</td><td>15s</td><td>Campaign</td><td>3:50</td></tr>
<tr><td>18-20</td><td>Filler 13-15</td><td>10-15s</td><td>House</td><td>4:05-4:30</td></tr>
<tr><td>21</td><td>Ad-F</td><td>10s</td><td>Campaign</td><td>4:40</td></tr>
<tr><td>22-23</td><td>Filler 16-17</td><td>10s</td><td>House</td><td>4:50-5:00</td></tr>
<tr><td>24</td><td>Ad-G</td><td>10s</td><td>Campaign</td><td>5:10</td></tr>
<tr><td>25-27</td><td>Filler 18-20</td><td>10-15s</td><td>House</td><td>5:20-5:50</td></tr>
<tr><td>28</td><td>Ad-H</td><td>20s</td><td>Campaign</td><td>6:00</td></tr>
<tr><td>29-31</td><td>Filler 21-23</td><td>10-15s</td><td>House</td><td>6:20-6:45</td></tr>
<tr><td>32</td><td>Ad-I</td><td>15s</td><td>Campaign</td><td>6:55</td></tr>
<tr><td>33-55</td><td>Filler 24-46</td><td>10-15s</td><td>House</td><td>7:10-12:00</td></tr>
</table>
<p><strong>หมายเหตุ:</strong> Player เล่น <code>sequence[i++]</code> ตามลำดับ &rarr; วนซ้ำ 5 loops/hr</p>"""))

    sections.append('<h3>สรุปตัวเลขทั้งวัน</h3>')
    sections.append("""<table>
<tr><th>Metric</th><th>Per Loop</th><th>Per Hour (x5)</th><th>Per Day (x75)</th></tr>
<tr><td>Campaign plays</td><td>9</td><td>45</td><td><strong>675</strong></td></tr>
<tr><td>House/Filler plays</td><td>~46</td><td>~230</td><td><strong>~3,450</strong></td></tr>
<tr><td>Total plays</td><td>~55</td><td>~280</td><td><strong>~4,125</strong></td></tr>
<tr><td>Campaign airtime</td><td>150s</td><td>750s</td><td>11,250s (3.1 hr)</td></tr>
<tr><td>House airtime</td><td>570s</td><td>2,850s</td><td>42,750s (11.9 hr)</td></tr>
</table>""")

    sections.append(note_panel(
        "<p><strong>Insight:</strong> Campaign ใช้แค่ ~21% ของ airtime (750/3,600) &rarr; "
        "79% เป็น filler &mdash; สภาพปกติของป้ายที่ยังขาย inventory ไม่เต็ม "
        "ยิ่งขาย ads เพิ่ม filler จะลดลง loop สั้นลง frequency เพิ่มอัตโนมัติ</p>"
    ))

    # ─── Algorithm Diagram ───
    sections.append('<h3>Algorithm Overview</h3>')
    sections.append(mermaid_diagram(
        load_diagram("12-ad-decisioning-steps.mmd"),
        page_id=page_id,
    ))

    # ─── Section 2: Calculation Cycle ───
    sections.append('<h2>2. รอบการคำนวณ Schedule (Calculation Cycle)</h2>')

    sections.append('<h3>3-Tier Cache System</h3>')
    sections.append("""<table>
<tr><th>Tier</th><th>Method</th><th>เนื้อหา</th><th>อายุ</th><th>ใช้เมื่อ</th></tr>
<tr><td><strong>Tier 1 (Live)</strong></td><td><code>buildSchedule()</code></td><td>Campaign + House ตามจริง</td><td>5 นาที</td><td>Online ปกติ</td></tr>
<tr><td><strong>Tier 2 (Buffer)</strong></td><td><code>buildBufferSchedule(4)</code></td><td>Pre-calc ล่วงหน้า 4 ชม.</td><td>4 ชั่วโมง</td><td>เน็ตหลุด &gt; 5 นาที</td></tr>
<tr><td><strong>Tier 3 (Fallback)</strong></td><td><code>buildFallbackSchedule()</code></td><td>House content อย่างเดียว</td><td>เปลี่ยนน้อยมาก</td><td>เน็ตหลุด &gt; 4 ชม.</td></tr>
</table>""")

    sections.append('<h3>Timeline ทั้งวัน (07:00-22:00)</h3>')
    sections.append(expand_section("ดู Timeline เต็ม", """<table>
<tr><th>เวลา</th><th>Event</th><th>ทำอะไร</th></tr>
<tr><td>05:00</td><td>Daily Pre-calc Cron</td><td>Tier 2 (07:00-11:00) + Tier 3 ทั้งวัน + pre-download media</td></tr>
<tr><td>06:50</td><td>Warm-up</td><td>Player boot &rarr; ดึง Tier 1+2+3, download media</td></tr>
<tr><td>07:00</td><td>เปิดจอ + Cron Tier 1</td><td>Loop 07:00-07:05 (v1)</td></tr>
<tr><td>07:05</td><td>Cron Tier 1</td><td>Loop 07:05-07:10 (v2)</td></tr>
<tr><td>...</td><td>(ทุก 5 นาที)</td><td>Tier 1 update ต่อเนื่อง</td></tr>
<tr><td>09:00</td><td>Cron rebuild Tier 2</td><td>Buffer 09:00-13:00</td></tr>
<tr><td>11:00</td><td>Cron rebuild Tier 2</td><td>Buffer 11:00-15:00</td></tr>
<tr><td>13:00</td><td>Cron rebuild Tier 2</td><td>Buffer 13:00-17:00</td></tr>
<tr><td>15:00</td><td>Cron rebuild Tier 2</td><td>Buffer 15:00-19:00</td></tr>
<tr><td>17:00</td><td>Cron rebuild Tier 2</td><td>Buffer 17:00-21:00</td></tr>
<tr><td>19:00</td><td>Cron rebuild Tier 2</td><td>Buffer 19:00-22:00</td></tr>
<tr><td>21:55</td><td>Cron Tier 1 สุดท้าย</td><td>Loop 21:55-22:00</td></tr>
<tr><td>22:00</td><td>ปิดจอ</td><td>&mdash;</td></tr>
</table>"""))

    sections.append('<h3>สรุปจำนวน Cron Jobs ต่อวัน</h3>')
    sections.append("""<table>
<tr><th>Cron Job</th><th>ความถี่</th><th>จำนวน/วัน</th></tr>
<tr><td>Tier 1 (Live)</td><td>ทุก 5 นาที</td><td><strong>180 ครั้ง</strong></td></tr>
<tr><td>Tier 2 (Buffer)</td><td>ทุก 2 ชม.</td><td><strong>8 ครั้ง</strong></td></tr>
<tr><td>Tier 3 (Fallback)</td><td>วันละ 1 ครั้ง</td><td><strong>1 ครั้ง</strong></td></tr>
<tr><td>Daily Pre-calc</td><td>05:00</td><td><strong>1 ครั้ง</strong></td></tr>
<tr><td>Event-driven (avg)</td><td>เมื่อมี event</td><td><strong>~5-15 ครั้ง</strong></td></tr>
<tr><td><strong>รวม</strong></td><td></td><td><strong>~195-205 ครั้ง/วัน/ป้าย</strong></td></tr>
</table>""")

    sections.append('<h3>Event-Driven Re-calc Triggers</h3>')
    sections.append("""<table>
<tr><th>Event</th><th>Trigger</th><th>ความเร่งด่วน</th><th>Lead Time ขั้นต่ำ</th></tr>
<tr><td>Owner approve ad ใหม่</td><td><code>advertisement.approved</code></td><td>ทันที</td><td><strong>15 นาที</strong></td></tr>
<tr><td>Campaign แก้ไข creative</td><td><code>campaign.updated</code></td><td>ทันที</td><td>15 นาที</td></tr>
<tr><td>Guaranteed spot จอง/ยกเลิก</td><td><code>exclusive.approved</code></td><td>ทันที</td><td><strong>1 ชั่วโมง</strong></td></tr>
<tr><td>Takeover จอง</td><td><code>takeover.booked</code></td><td>ภายใน 5 นาที</td><td><strong>24 ชั่วโมง</strong></td></tr>
<tr><td>Campaign หมดอายุ/pause</td><td><code>campaign.expired</code></td><td>รอบ cron ถัดไป</td><td>&mdash;</td></tr>
<tr><td>House content เปลี่ยน</td><td><code>playlist.updated</code></td><td>รอบ cron ถัดไป</td><td>&mdash;</td></tr>
</table>""")

    sections.append(warning_panel(
        "<p><strong>Lead Time:</strong> คอขวดจริงไม่ใช่ calculation (~1 วินาที) "
        "แต่คือ <strong>creative download</strong> &mdash; ดู Distribution Time Breakdown ด้านล่าง</p>"
    ))

    sections.append('<h3>Distribution Time Breakdown</h3>')
    sections.append(
        '<p>เวลาจริงตั้งแต่ ad approved จนเล่นบนจอ:</p>'
    )
    sections.append("""<table>
<tr><th>ขั้นตอน</th><th>เวลา</th><th>หมายเหตุ</th></tr>
<tr><td>Calculate schedule</td><td>&lt; 1s</td><td>In-memory, per-screen</td></tr>
<tr><td>Save to DB</td><td>&lt; 500ms</td><td>ScreenSchedule v+1</td></tr>
<tr><td>Pusher notification</td><td>&lt; 1s</td><td>Push event ไป Player</td></tr>
<tr><td>Player receives push</td><td>1-3s</td><td>Network latency</td></tr>
<tr><td><strong>Player downloads creative</strong></td><td><strong>30s - 5 min</strong></td><td><strong>Bottleneck:</strong> ขึ้นกับ file size + network speed</td></tr>
<tr><td>Apply new schedule</td><td>&lt; 1s</td><td>Switch on next loop</td></tr>
<tr><td><strong>รวม end-to-end</strong></td><td><strong>~35s - 5 min</strong></td><td>ขึ้นกับ creative size</td></tr>
</table>""")
    sections.append(info_panel(
        "<p><strong>Creative Pre-download:</strong> Player สามารถดาวน์โหลด creative ล่วงหน้า "
        "ตอนได้รับ push notification ไม่ต้องรอจนถึง play time จริง &mdash; "
        "ลด latency จาก 5 นาที เหลือ &lt; 30 วินาที สำหรับ ad ที่ creative พร้อมแล้ว</p>"
    ))

    sections.append('<h3>ทำไมเลือก Cron 5 นาที (ไม่ใช่ 2 นาทีหรือ 10 นาที)?</h3>')
    sections.append("""<table>
<tr><th>Cycle</th><th>ข้อดี</th><th>ข้อเสีย</th></tr>
<tr><td>10 นาที</td><td>Server load ต่ำ, player stable</td><td>Response ช้า ลูกค้ารอนาน</td></tr>
<tr><td><strong>5 นาที (เลือก)</strong></td><td><strong>Balance ดี, ตรง industry standard</strong></td><td>+2x cron load (ยังรับได้สบาย)</td></tr>
<tr><td>2 นาที</td><td>เร็วมาก</td><td>+5x load, pacing accuracy ลดลง (sample size เล็ก)</td></tr>
<tr><td>1 นาที</td><td>Near real-time</td><td>Pacing แทบไม่ work, player เปลี่ยน playlist บ่อยเกินไป</td></tr>
</table>""")
    sections.append(note_panel(
        "<p><strong>Industry Benchmark:</strong> Xibo 5 นาที (default), Broadsign 15 นาที (SLA), "
        "Vistar Media 15 นาที (programmatic), Scala 5-15 นาที (configurable) &mdash; "
        "5 นาทีของเราอยู่ในกลุ่มเร็วของ industry</p>"
    ))

    # ─── Re-calc Sequence Diagram ───
    sections.append('<h3>Flow: Ad ใหม่เข้าระบบ</h3>')
    sections.append(mermaid_diagram(
        load_diagram("12-recalc-sequence.mmd"),
        page_id=page_id,
    ))

    # ─── Section 3: Campaign Pacing Filter ───
    sections.append('<h2>3. Campaign Pacing Filter</h2>')

    sections.append(
        '<p><strong>หลักการ:</strong> ป้องกัน over-delivery &mdash; '
        'ถ้า ad ตัวไหนเล่นเกินเป้าแล้ว ก็ถอดออกจาก loop ถัดไป เอา filler มาแทน</p>'
    )

    sections.append('<h3>ตัวอย่าง: Ad-A (30s) เป้า 40 impressions/day</h3>')
    sections.append("""<table>
<tr><th>เวลา</th><th>เล่นไปแล้ว</th><th>เป้า</th><th>เหลือ</th><th>Pacing Rate</th><th>สถานะ</th></tr>
<tr><td>08:00</td><td>0</td><td>40</td><td>40</td><td>1.0/loop</td><td>เล่นทุก loop</td></tr>
<tr><td>10:00</td><td>15</td><td>40</td><td>25</td><td>0.83/loop</td><td>เล่นทุก loop</td></tr>
<tr><td>12:00</td><td>28</td><td>40</td><td>12</td><td>0.6/loop</td><td><strong>ข้าม 2 ใน 5 loops/hr</strong></td></tr>
<tr><td>14:00</td><td>38</td><td>40</td><td>2</td><td>0.2/loop</td><td><strong>เล่นแค่ 1 ใน 5 loops/hr</strong></td></tr>
<tr><td>14:24</td><td>40</td><td>40</td><td>0</td><td>0</td><td><strong>ถอดออก &rarr; filler แทน</strong></td></tr>
</table>""")

    sections.append('<h3>ทำไมต้องมี Pacing Filter?</h3>')
    sections.append("""<table>
<tr><th>ปัญหา (ไม่มี filter)</th><th>ผลกระทบ</th></tr>
<tr><td>Ad เล่นเกินเป้าตอนเช้า</td><td>ช่วงบ่ายไม่มี ad เล่นเลย &rarr; ป้ายว่างเกินไป</td></tr>
<tr><td>ลูกค้าจ่าย 40 impressions แต่ได้ 60</td><td><strong>Over-delivery = เสียรายได้</strong> (ให้ฟรี 20 impressions)</td></tr>
<tr><td>Ad สั้น (10s) วนเร็วกว่า ad ยาว (30s)</td><td>Ad สั้น over-deliver ก่อน &rarr; ไม่สม่ำเสมอ</td></tr>
</table>""")

    sections.append(success_panel(
        "<p><strong>ผลลัพธ์:</strong> Pacing filter ทำหน้าที่เป็น <strong>throttle</strong> &mdash; "
        "กระจาย impressions ให้สม่ำเสมอทั้งวัน ไม่กระจุกช่วงเช้า "
        "ลูกค้าได้ตามเป้าพอดี ไม่มากไม่น้อย</p>"
    ))

    # ─── Section 4: Daypart Takeover Scenario ───
    sections.append('<h2>4. Scenario: Daypart Takeover (เหมาช่วงเวลา)</h2>')

    sections.append(info_panel(
        "<p><strong>Use Case:</strong> ลูกค้าต้องการให้ ad ของตัวเองเล่น <strong>ต่อเนื่องเป็นช่วง ห้ามมี ad อื่นแทรก</strong> "
        "&mdash; ระบบเรียกว่า <strong>Daypart Takeover (P1-TK)</strong></p>"
    ))

    sections.append('<h3>ตัวอย่าง Scenario</h3>')
    sections.append("""<table>
<tr><th>รายการ</th><th>รายละเอียด</th></tr>
<tr><td><strong>Spot ของลูกค้า</strong></td><td>30 วินาที</td></tr>
<tr><td><strong>ช่วงเวลาที่ต้องการ</strong></td><td>เล่นวนต่อเนื่อง <strong>10 นาที</strong> ห้ามมี ad อื่นแทรก</td></tr>
<tr><td><strong>จำนวนครั้ง/วัน</strong></td><td><strong>10 blocks</strong> กระจายตลอดเวลาเปิด-ปิดป้าย</td></tr>
<tr><td><strong>ป้าย</strong></td><td>เปิด 07:00-22:00 (15 ชม.)</td></tr>
<tr><td><strong>การเล่นภายใน block</strong></td><td>spot 30s &times; 20 รอบ = 600s (10 นาทีพอดี)</td></tr>
<tr><td><strong>เวลา TK รวม/วัน</strong></td><td>10 blocks &times; 10 นาที = <strong>100 นาที (1 ชม. 40 นาที)</strong></td></tr>
<tr><td><strong>เวลาเล่นปกติ</strong></td><td>15 ชม. - 100 นาที = <strong>13 ชม. 20 นาที</strong></td></tr>
</table>""")

    sections.append('<h3>การจัดวาง TK Blocks บน Timeline</h3>')
    sections.append(
        '<p>กระจาย 10 blocks ให้เท่าๆ กันตลอดวัน (ทุก ~90 นาที):</p>'
    )
    sections.append("""<table>
<tr><th>Block</th><th>เวลา TK</th><th>Spot plays</th><th>ช่วงก่อน TK ถัดไป</th></tr>
<tr><td>TK-1</td><td><strong>07:00 - 07:10</strong></td><td>20 plays</td><td>80 นาที (เล่นปกติ)</td></tr>
<tr><td>TK-2</td><td><strong>08:30 - 08:40</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-3</td><td><strong>10:00 - 10:10</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-4</td><td><strong>11:30 - 11:40</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-5</td><td><strong>13:00 - 13:10</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-6</td><td><strong>14:30 - 14:40</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-7</td><td><strong>16:00 - 16:10</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-8</td><td><strong>17:30 - 17:40</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-9</td><td><strong>19:00 - 19:10</strong></td><td>20 plays</td><td>80 นาที</td></tr>
<tr><td>TK-10</td><td><strong>20:30 - 20:40</strong></td><td>20 plays</td><td>80 นาทีจนปิดจอ</td></tr>
<tr><td colspan="2"><strong>รวม</strong></td><td><strong>200 plays/วัน</strong></td><td></td></tr>
</table>""")
    sections.append(note_panel(
        "<p><strong>การกระจาย:</strong> ตัวอย่างนี้กระจายทุก ~90 นาที แต่ลูกค้าสามารถเลือกเวลาเองได้ "
        "(เช่น เน้นช่วง prime time 17:00-21:00) &mdash; ขอแค่ <strong>TK blocks ไม่ซ้อนกัน</strong> "
        "กับ TK ของลูกค้าคนอื่นบนป้ายเดียวกัน</p>"
    ))

    sections.append('<h3>ระบบทำงานอย่างไร</h3>')
    sections.append("""<table>
<tr><th>ขั้นตอน</th><th>ใคร</th><th>ทำอะไร</th></tr>
<tr><td><strong>1. Booking</strong></td><td>Sales / Admin</td><td>จอง 10 time blocks ผ่าน <strong>TK Booking API</strong> (lead time 24 ชม.)</td></tr>
<tr><td><strong>2. Overlap Check</strong></td><td>Backend</td><td><code>checkIsBillboardsReserved()</code> &mdash; ตรวจว่าไม่ซ้อนกับ TK อื่น</td></tr>
<tr><td><strong>3. Schedule Calc</strong></td><td>Ad Decisioning</td><td>เห็น <code>takeoverSchedules[]</code> &rarr; <code>timeline.reserveTakeover(start, end, {loop: true})</code></td></tr>
<tr><td><strong>4. TK_START</strong></td><td>Interrupt Controller</td><td>ถึงเวลา TK &rarr; <strong>หยุด</strong> creative ปัจจุบันทันที &rarr; เล่น TK spot</td></tr>
<tr><td><strong>5. Loop within TK</strong></td><td>Player</td><td>Spot 30s วน <strong>ไม่หยุด</strong> &mdash; ห้ามแทรกยกเว้น P0 Emergency</td></tr>
<tr><td><strong>6. TK_END</strong></td><td>Interrupt Controller</td><td>ครบ 10 นาที &rarr; <code>TK_END</code> event &rarr; กลับเล่น schedule ปกติ</td></tr>
<tr><td><strong>7. Make-Good</strong></td><td>Backend</td><td>Ad ปกติที่โดน interrupt ตอน TK_START จะได้ <strong>make-good compensation</strong> ใน cycle ถัดไป</td></tr>
</table>""")

    sections.append('<h3>ผลกระทบต่อ Schedule ปกติ</h3>')
    sections.append("""<table>
<tr><th>Metric</th><th>ไม่มี TK</th><th>มี TK 10 blocks</th><th>ผลกระทบ</th></tr>
<tr><td>Available time สำหรับ campaign ปกติ</td><td>15 ชม. (900 นาที)</td><td><strong>13 ชม. 20 นาที (800 นาที)</strong></td><td>-11%</td></tr>
<tr><td>Campaign loops/วัน</td><td>75 loops (5/hr &times; 15hr)</td><td><strong>67 loops</strong> (5/hr &times; 13.3hr)</td><td>-11%</td></tr>
<tr><td>Campaign impressions/วัน (9 ads)</td><td>675</td><td><strong>~600</strong></td><td>-11%</td></tr>
<tr><td>TK impressions/วัน</td><td>0</td><td><strong>200</strong> (20/block &times; 10)</td><td>+200</td></tr>
<tr><td>Total impressions/วัน (ทั้งหมด)</td><td>4,125</td><td><strong>~3,875</strong></td><td>-6%</td></tr>
</table>""")
    sections.append(warning_panel(
        "<p><strong>Trade-off:</strong> TK blocks กิน airtime จาก campaign ปกติ ~11% &mdash; "
        "campaign ads จะถูก pacing ให้สม่ำเสมอในช่วงที่เหลือ (ไม่กระจุก). "
        "ถ้าลูกค้า campaign ซื้อ impression guarantee อาจต้อง <strong>ขยาย flight date</strong> "
        "ให้ชดเชย impressions ที่หายไป.</p>"
    ))

    sections.append('<h3>Billing</h3>')
    sections.append("""<table>
<tr><th>Ad Type</th><th>Billing Model</th><th>ตัวอย่าง</th></tr>
<tr><td><strong>Daypart Takeover (P1-TK)</strong></td><td><strong>CPT (Cost Per Time)</strong></td><td>10 blocks &times; 10 นาที = 100 นาที &times; rate/นาที</td></tr>
<tr><td>Campaign ปกติ (P2)</td><td>Standard rate / CPM</td><td>ต่อ impression หรือต่อช่วงเวลา</td></tr>
<tr><td>Guaranteed (P1-G)</td><td><code>exclusiveMultiplier</code></td><td>Premium rate ต่อ spot</td></tr>
</table>""")

    sections.append(success_panel(
        "<p><strong>สรุป:</strong> Daypart Takeover (P1-TK) รองรับ scenario นี้ครบ &mdash; "
        "block ขนาดใดก็ได้ (10 นาที, 30 นาที, 1 ชม.), จำนวน blocks ไม่จำกัด (แค่ไม่ซ้อนกัน), "
        "Player วน creative ตัวเดียวไม่หยุด, ห้ามแทรกยกเว้น P0, "
        "และ ad ที่โดน interrupt ได้ make-good อัตโนมัติ.</p>"
    ))

    # ─── Section 5: Daypart Targeting ─────────────────────────────────────────
    sections.append("<hr/>")
    sections.append("<h2>5. Daypart Targeting — กระจาย Ad เฉพาะช่วงเวลา Peak</h2>")
    sections.append(info_panel(
        "<p><strong>Daypart Targeting</strong> = กำหนด <code>DaypartWindow[]</code> บน AdGroup "
        "เพื่อจำกัดการเล่นเฉพาะช่วงเวลาที่เลือก (เช่น morning peak, evening rush). "
        "รองรับทั้ง P1-DG (Dayparted Guaranteed) และ P2 ROS with daypart filter.</p>"
        "<ul>"
        "<li><strong>P1-DG:</strong> รับประกัน N plays กระจาย <em>เฉพาะใน window</em> (center-offset distribution)</li>"
        "<li><strong>P2 + daypart:</strong> เล่น N plays/hr แต่เฉพาะช่วงที่กำหนด — ช่วงอื่น = 0</li>"
        "<li><strong>ไม่ใช่ Takeover:</strong> โฆษณาอื่นยังแทรกได้ใน window (ต่างจาก P1-TK)</li>"
        "</ul>"
    ))

    sections.append("<h3>Even Distribution Algorithm (Center-Offset)</h3>")
    sections.append(
        '<table>'
        '<tr><th>Parameter</th><th>Formula</th><th>ตัวอย่าง (4 plays, 10:00-10:30)</th></tr>'
        '<tr><td><code>windowDuration</code></td><td><code>toSeconds(end) - toSeconds(start)</code></td><td>1800s (30 นาที)</td></tr>'
        '<tr><td><code>interval</code></td><td><code>windowDuration / plays</code></td><td>450s (7.5 นาที)</td></tr>'
        '<tr><td><code>offset</code></td><td><code>interval / 2</code></td><td>225s (3.75 นาที)</td></tr>'
        '<tr><td>play times</td><td><code>start + offset + interval×i</code></td><td>10:03:45 · 10:11:15 · 10:18:45 · 10:26:15</td></tr>'
        '</table>'
    )
    sections.append(note_panel(
        "<p><strong>ทำไม center-offset?</strong> ถ้าเริ่มตรง 10:00:00 เลย &rarr; รู้สึก front-loaded. "
        "การ offset ด้วย interval/2 ทำให้การกระจายดูเป็นธรรมชาติและสม่ำเสมอกว่า</p>"
    ))

    sections.append("<h3>plays_in_window Calculation</h3>")
    sections.append(
        '<table>'
        '<tr><th>Input</th><th>Formula</th><th>ตัวอย่าง</th></tr>'
        '<tr><td><code>playsPerHour=8</code>, window=10:00-10:30</td><td><code>round(8 × 0.5hr)</code></td><td>4 plays</td></tr>'
        '<tr><td><code>playsPerHour=20</code>, window=08:00-12:00</td><td><code>round(20 × 4hr)</code></td><td>80 plays</td></tr>'
        '<tr><td><code>playsPerHour=20</code>, window=17:00-21:00</td><td><code>round(20 × 4hr)</code></td><td>80 plays</td></tr>'
        '</table>'
    )
    sections.append(warning_panel(
        "<p><strong>สิ่งที่ระบบแสดงที่ booking confirmation:</strong> "
        '"คุณจะได้ ~4 plays ใน window 10:00-10:30" &mdash; '
        "ลูกค้าไม่ต้องระบุ plays_per_window เองโดยตรง (rate-based model ตาม Broadsign/Vistar standard)</p>"
    ))

    sections.append("<h3>Scenario: P2 + Daypart (Peak Hours Only)</h3>")
    sections.append(
        '<table>'
        '<tr><th>Field</th><th>Value</th></tr>'
        '<tr><td>Ad type</td><td>P2 Direct-Sold ROS + daypartWindows</td></tr>'
        '<tr><td>playsPerHour</td><td>20 plays/hr</td></tr>'
        '<tr><td>daypartWindows</td><td>[08:00-12:00, 17:00-21:00]</td></tr>'
        '<tr><td>plays in Window 1</td><td>20 × 4 = 80 plays (distributed 08:00-12:00)</td></tr>'
        '<tr><td>plays in Window 2</td><td>20 × 4 = 80 plays (distributed 17:00-21:00)</td></tr>'
        '<tr><td>plays นอก window</td><td>0 (12:00-17:00 และ 21:00-22:00 ไม่เล่น)</td></tr>'
        '<tr><td>plays/day รวม</td><td>160 plays (8 ชั่วโมง peak)</td></tr>'
        '</table>'
    )

    return "\n".join(sections)


def build_page_13(page_id: str) -> str:
    """Page 13: Use Case — Industry Comparison (1 mermaid, 0 code blocks)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())

    sections.append(info_panel(
        "<p><strong>Use Case Reference:</strong> เปรียบเทียบสถาปัตยกรรม Ad Scheduling "
        "ของ Tathep กับ 3 models หลักที่ใช้ใน DOOH industry "
        "เพื่อเข้าใจว่าทำไมเราเลือก Hybrid approach</p>"
    ))

    # ─── Section 1: 3 Models ───
    sections.append('<h2>1. สาม Models ที่ Industry ใช้</h2>')

    sections.append('<h3>Model 1: Player-Side Rules (Broadsign, Xibo)</h3>')
    sections.append(
        '<p>Server ส่ง <strong>กฎ (loop policy)</strong> ให้ Player &rarr; '
        'Player สร้าง playlist เองแบบ real-time ทุก loop</p>'
    )
    sections.append("""<table>
<tr><th>ข้อดี</th><th>ข้อเสีย</th></tr>
<tr><td>Player ปรับตัวได้ทันที</td><td>Player ต้องฉลาด (logic เยอะ)</td></tr>
<tr><td>ไม่ต้องพึ่ง server ตลอด</td><td>Debug ยาก (playlist ไม่เหมือนกันทุกเครื่อง)</td></tr>
<tr><td>Offline ทำงานได้เลย</td><td>Pacing accuracy ต่ำ (player ไม่รู้ภาพรวม)</td></tr>
</table>""")
    sections.append(
        '<p><strong>Reference:</strong> '
        '<a href="https://docs.broadsign.com/broadsign-control/latest/loop-policies.html">'
        'Broadsign Loop Policies</a> | '
        '<a href="https://xibosignage.com/docs/developer/player-control/schedule-criteria">'
        'Xibo Schedule Criteria</a></p>'
    )

    sections.append('<h3>Model 2: Server-Side Pre-Generated (Signagelive, Scala)</h3>')
    sections.append(
        '<p>Server คำนวณ <strong>playlist สำเร็จรูป</strong> &rarr; '
        'Player แค่เล่นตามลำดับ (Dumb Renderer)</p>'
    )
    sections.append("""<table>
<tr><th>ข้อดี</th><th>ข้อเสีย</th></tr>
<tr><td>Player เรียบง่าย (แค่เล่น)</td><td>ต้องพึ่ง server สร้าง playlist</td></tr>
<tr><td>Pacing แม่นยำ (server เห็นภาพรวม)</td><td>Offline = เล่น playlist เดิมซ้ำ</td></tr>
<tr><td>Debug ง่าย (playlist เหมือนกันทุกที่)</td><td>ไม่ยืดหยุ่น (ต้องรอ server อัพเดท)</td></tr>
</table>""")
    sections.append(
        '<p><strong>Reference:</strong> '
        '<a href="https://support.signagelive.com/en/articles/137724-how-to-use-the-automatic-playlist-generator">'
        'Signagelive Playlist Generator</a> | '
        '<a href="https://scala.com/en/products/software/scala-content-manager/">'
        'Scala Content Manager</a></p>'
    )

    sections.append('<h3>Model 3: Hybrid (Tathep Proposed)</h3>')
    sections.append(
        '<p>Server สร้าง <strong>ordered sequence</strong> + Player มี '
        '<strong>Interrupt Controller</strong> สำหรับ premium (P1-TK, P1-ET) '
        '+ <strong>3-tier cache</strong> สำหรับ offline</p>'
    )
    sections.append("""<table>
<tr><th>ข้อดี</th><th>ข้อเสีย</th></tr>
<tr><td>Player เรียบง่าย + Interrupt เฉพาะ premium</td><td>Server ต้องคำนวณทุก 5 นาที + event-driven</td></tr>
<tr><td>Pacing แม่นยำ + offline 4+ ชม.</td><td>ซับซ้อนกว่า Model 2 เล็กน้อย (มี IC)</td></tr>
<tr><td>รองรับ premium products (Takeover, Exact-Time)</td><td>ต้อง maintain 3-tier cache</td></tr>
</table>""")

    # ─── Comparison Diagram ───
    sections.append('<h3>เปรียบเทียบ Data Flow</h3>')
    sections.append(mermaid_diagram(
        load_diagram("13-industry-comparison.mmd"),
        page_id=page_id,
    ))

    # ─── Section 2: Comparison Table ───
    sections.append('<h2>2. ตารางเปรียบเทียบ 7 เกณฑ์</h2>')

    sections.append("""<table>
<tr><th>เกณฑ์</th><th>Player-Side (Broadsign)</th><th>Server-Side (Signagelive)</th><th>Hybrid (Tathep)</th></tr>
<tr><td><strong>Player complexity</strong></td><td>สูง (สร้าง playlist เอง)</td><td>ต่ำ (เล่นอย่างเดียว)</td><td>ต่ำ + Interrupt Controller</td></tr>
<tr><td><strong>Pacing accuracy</strong></td><td>ปานกลาง</td><td>สูง</td><td><strong>สูง</strong> (server คำนวณ)</td></tr>
<tr><td><strong>Offline resilience</strong></td><td>ดี (มี rules อยู่)</td><td>แย่ (playlist เก่า)</td><td><strong>ดี</strong> (3-tier cache)</td></tr>
<tr><td><strong>Real-time flexibility</strong></td><td>ดี (re-evaluate ทุก loop)</td><td>แย่ (รอ server)</td><td><strong>ดี</strong> (Tier 1 + interrupt)</td></tr>
<tr><td><strong>Premium products</strong></td><td>ผ่าน rules/priority</td><td>ต้อง re-generate</td><td><strong>Interrupt real-time</strong></td></tr>
<tr><td><strong>Debug/Audit</strong></td><td>ยาก</td><td>ง่าย</td><td><strong>ง่าย</strong> (server log)</td></tr>
<tr><td><strong>Server load</strong></td><td>ต่ำ (ส่งแค่ rules)</td><td>สูง</td><td>ปานกลาง (~200/วัน)</td></tr>
</table>""")

    # ─── Section 3: Industry Trend ───
    sections.append('<h2>3. Industry Trend (2025-2026)</h2>')

    sections.append(
        '<p>Industry กำลังเปลี่ยนจาก <strong>loop-based</strong> (ขายรอบ/ชม.) '
        'ไปเป็น <strong>impression-based</strong> (ขายจำนวนคนเห็น):</p>'
    )

    sections.append("""<table>
<tr><th>เดิม (Loop-based)</th><th>ใหม่ (Impression-based)</th></tr>
<tr><td>ขาย "5 ครั้ง/hr"</td><td>ขาย "10,000 impressions"</td></tr>
<tr><td>วัดจาก playout count</td><td>วัดจาก audience measurement (กล้อง/sensor)</td></tr>
<tr><td>ราคาคงที่ต่อ slot</td><td>ราคาผันตาม traffic (programmatic)</td></tr>
<tr><td>Pre-schedule ล่วงหน้า</td><td>Real-time bidding (RTB)</td></tr>
</table>""")

    sections.append(success_panel(
        "<p><strong>Tathep รองรับทั้ง 2 แบบ:</strong> P2 (Direct-Sold) = loop-based ขายรอบ/ชม. | "
        "P3 (Spot Buy) = impression-based รองรับ programmatic ในอนาคต</p>"
    ))

    sections.append('<h3>Sources</h3>')
    sections.append(
        '<ul>'
        '<li><a href="https://docs.broadsign.com/broadsign-control/latest/loop-policies.html">'
        'Broadsign Loop Policies</a></li>'
        '<li><a href="https://docs.broadsign.com/broadsign-direct/screen-availability-fill-rate.html">'
        'Broadsign Fill Rate Calculation</a></li>'
        '<li><a href="https://support.signagelive.com/en/articles/137724-how-to-use-the-automatic-playlist-generator">'
        'Signagelive Automatic Playlist Generator</a></li>'
        '<li><a href="https://xibosignage.com/docs/developer/player-control/schedule-criteria">'
        'Xibo Schedule Criteria</a></li>'
        '<li><a href="https://help.vistarmedia.com/hc/en-us/articles/360032923692-Integration-health-assessment-guide">'
        'Vistar Media Integration (15 min SLA)</a></li>'
        '<li><a href="https://blog.bidswitch.com/whats-new-with-dooh-a-view-of-digital-out-of-home-in-2025">'
        'DOOH Trends 2025</a></li>'
        '</ul>'
    )

    # ─── Section 4: Industry Standards and Design Rationale ───
    sections.append('<h2>4. มาตรฐาน Industry และ Design Rationale</h2>')
    sections.append(info_panel(
        "<p><strong>Priority model 5 ระดับ (P0-P4)</strong> ที่เราเสนอ ได้แรงบันดาลใจจากมาตรฐาน industry เหล่านี้. "
        "หลักการสำคัญ: exclusive/priority scheduling เป็น <em>โจทย์ที่วงการ digital signage แก้ไปแล้ว</em> &mdash; "
        "เรา adapt pattern ที่พิสูจน์แล้วแทนที่จะคิดใหม่ตั้งแต่ต้น.</p>"
    ))

    sections.append('<h3>มาตรฐาน Priority Scheduling (SMIL + DOOH)</h3>')
    sections.append(expand_section("SMIL, Xibo, Broadsign, DOOH Billing — มาตรฐาน Priority",
        '<table>'
        '<tr><th>Standard/Platform</th><th>Priority Mechanism</th><th>What We Adopt</th></tr>'
        '<tr><td><strong>W3C SMIL 3.0</strong><br/><code>&lt;excl&gt;</code> + <code>&lt;priorityClass&gt;</code></td>'
        '<td><ul>'
        '<li><code>&lt;excl&gt;</code>: only one child plays at a time (mutual exclusion)</li>'
        '<li><code>&lt;priorityClass&gt;</code>: assigns priority levels with <code>peers</code> + <code>higher</code> + <code>lower</code> policies</li>'
        '<li>Policies: <code>stop</code> (kill lower), <code>pause</code> (pause queue/stack), <code>defer</code> (queue for later), <code>never</code> (reject)</li>'
        '<li>Pause queue: nested interrupts push onto stack &rarr; resume in LIFO order</li>'
        '</ul></td>'
        '<td><ul>'
        '<li><strong>P0-P4 levels</strong> = simplified priorityClass</li>'
        '<li><strong>Exclusive = P1</strong> with guaranteed slot reservation</li>'
        '<li>No pause queue needed &mdash; Ad Decisioning Engine resolves at build time (player sees flat sequence)</li>'
        '<li>SMIL <code>peers=&quot;stop&quot;</code> semantic for overlapping exclusives</li>'
        '</ul></td></tr>'
        '<tr><td><strong>Xibo CMS</strong><br/>Interrupt Layout + Priority</td>'
        '<td><ul>'
        '<li>Priority number (0 = lowest) per scheduled event</li>'
        '<li>Interrupt Layout: higher priority event preempts current layout</li>'
        '<li>Share of Voice: percentage-based time allocation</li>'
        '<li>Schedule reassessment on criteria change (geo-fence, daypart, priority)</li>'
        '</ul></td>'
        '<td><ul>'
        '<li><strong>Priority number</strong> concept &rarr; our P0-P4 model</li>'
        '<li><strong>Time allocation</strong> &rarr; Ad Decisioning Engine timeline reservation</li>'
        '<li>Share of Voice concept applicable for future frequency-based billing</li>'
        '</ul></td></tr>'
        '<tr><td><strong>Broadsign Control</strong><br/>'
        '<a href="https://docs.broadsign.com/broadsign-control/latest/en/settings-section.html">Day Part Switch (verified)</a></td>'
        '<td><ul>'
        '<li><strong>Configurable interrupt:</strong> Day Part Switch can interrupt mid-play or wait for completion</li>'
        '<li>Trigger system: serial/network/XML/touch triggers interrupt current content</li>'
        '<li>Default: interrupted content restarts after trigger (<code>--truncate_current</code> to skip)</li>'
        '<li>Revenue-based priority: guaranteed &gt; programmatic</li>'
        '</ul></td>'
        '<td><ul>'
        '<li><strong>Configurable interrupt → our P0/P1 interrupt vs P2-P4 wait</strong></li>'
        '<li>Day Part Switch → P1-TK Takeover boundary handling</li>'
        '<li>Restart after interrupt → we chose "resume next" (skip interrupted) + make-good</li>'
        '</ul></td></tr>'
        '<tr><td><strong>DOOH Billing Models</strong><br/>'
        '<a href="https://www.themediaant.com/blog/understanding-dooh-pricing-models/">The Media Ant (verified)</a> + '
        '<a href="https://www.cjadvertising.com/blog/industry-trends/preempts-makegoods-money-move/">CJ Advertising (verified)</a></td>'
        '<td><ul>'
        '<li><strong>CPT (Cost Per Time):</strong> flat rate for time block ownership</li>'
        '<li><strong>Make-Good:</strong> free replacement slot for preempted ads — industry standard</li>'
        '<li>CPM, Flat per spot, SOV-based pricing models</li>'
        '</ul></td>'
        '<td><ul>'
        '<li><strong>CPT → P1-TK Takeover billing</strong></li>'
        '<li><strong>Make-Good → MakeGoodRecord compensation system</strong></li>'
        '<li>Partial play ≠ impression (ไม่นับ billing)</li>'
        '</ul></td></tr>'
        '</table>'
    ))

    sections.append('<h3>สถาปัตยกรรมเรา vs มาตรฐาน DOOH (14 concepts)</h3>')
    sections.append(expand_section("เปรียบเทียบกับมาตรฐาน DOOH (14 concepts)",
        '<table>'
        '<tr><th>DOOH Concept</th><th>Our Implementation</th><th>Gap</th></tr>'
        '<tr><td><strong>Ad Server</strong></td><td>Ad Decisioning Engine อยู่ใน Backend (AdonisJS)</td><td>ไม่แยก — OK สำหรับ 100-500 จอ</td></tr>'
        '<tr><td><strong>CMS</strong></td><td>Admin panel + owner dashboard</td><td>มาตรฐาน</td></tr>'
        '<tr><td><strong>SSP (Supply-Side Platform)</strong></td><td>ยังไม่มี — P3 = SSP avail ในอนาคต</td><td>Phase 6 roadmap</td></tr>'
        '<tr><td><strong>Impression tracking</strong></td><td>PoP ผ่าน Outbox pattern</td><td>เพิ่ม IAB fields (Phase 6)</td></tr>'
        '<tr><td><strong>Campaign pacing</strong></td><td>BEP-2998 fix + Ad Decisioning Engine</td><td>พื้นฐาน — ปรับปรุงใน Phase 6</td></tr>'
        '<tr><td><strong>SOV allocation</strong></td><td>สัดส่วน ownerTime/platformTime</td><td>เปลี่ยนชื่อเป็น SOV, logic เดิม</td></tr>'
        '<tr><td><strong>Guaranteed delivery</strong></td><td>P1-G guaranteed spots พร้อม reservation check (ไม่ interrupt)</td><td>มาตรฐาน</td></tr>'
        '<tr><td><strong>Daypart Takeover</strong></td><td>P1-TK จอง time block + Interrupt Controller</td><td>Implement แล้ว (Phase 3.5)</td></tr>'
        '<tr><td><strong>Exact-Time Spot</strong></td><td>P1-ET ±5s tolerance + IC trigger</td><td>Implement แล้ว (Phase 3.5)</td></tr>'
        '<tr><td><strong>Make-Good</strong></td><td>MakeGoodRecord: โดน interrupt → ชดเชย cycle ถัดไป</td><td>Implement แล้ว (Phase 3.5)</td></tr>'
        '<tr><td><strong>Interrupt handling</strong></td><td>เลือก interrupt: P0/P1-TK/P1-ET interrupt, P2-P4 รอ</td><td>มาตรฐาน (แบบ Broadsign configurable)</td></tr>'
        '<tr><td><strong>Creative management</strong></td><td>Upload media + CDN + checksum validation</td><td>มาตรฐาน</td></tr>'
        '<tr><td><strong>Offline resilience</strong></td><td>Cache 3 ชั้น (Live/Buffer/Fallback)</td><td>มาตรฐาน (เทียบเท่า Xibo/BrightSign)</td></tr>'
        '<tr><td><strong>Loop scheduling</strong></td><td>Loop 5 นาที + event-driven ผ่าน Scheduling Engine (BullMQ)</td><td>มาตรฐาน</td></tr>'
        '</table>'
    ))

    sections.append('<h3>วิธีจัดการ Offline ของ Platform ชั้นนำ</h3>')
    sections.append(expand_section("Xibo, piSignage, BrightSign, info-beamer — แนวทาง Offline",
        '<table>'
        '<tr><th>Platform</th><th>Approach</th><th>Buffer</th></tr>'
        '<tr><td>Xibo</td><td>RequiredFiles manifest + MD5 per file + 50MB chunk download</td><td>48h ahead (configurable)</td></tr>'
        '<tr><td>piSignage</td><td>Default playlist fallback + local media folder + delta sync</td><td>Full campaign window</td></tr>'
        '<tr><td>BrightSign BSN.Cloud</td><td>Local-first: all media cached, network = sync only</td><td>Content-dependent</td></tr>'
        '<tr><td>info-beamer</td><td>3-state degradation (Online/Degraded/Offline) + RTC fallback</td><td>All scheduled content</td></tr>'
        '</table>'
    ))

    sections.append('<h3>อ้างอิง Open Source</h3>')
    sections.append(expand_section("Xibo, piSignage, Anthias — อ้างอิง Open Source",
        '<table>'
        '<tr><th>Project</th><th>Repository</th><th>Relevant Pattern</th></tr>'
        '<tr><td>Xibo Player SDK</td><td><a href="https://github.com/xibo-players/xiboplayer">xibo-players/xiboplayer</a></td><td>Cache API + IndexedDB, XMR WebSocket, chunk downloads with MD5, 2-layout preload pool</td></tr>'
        '<tr><td>Xibo .NET Client</td><td><a href="https://github.com/xibosignage/xibo-dotnetclient">xibosignage/xibo-dotnetclient</a></td><td>ScheduleManager.cs: thread polling, priority resolution, disk-resident schedule, Splash fallback</td></tr>'
        '<tr><td>piSignage</td><td><a href="https://github.com/colloqi/piSignage">colloqi/piSignage</a></td><td>Node.js + WebSocket, default playlist fallback, local filesystem media</td></tr>'
        '<tr><td>Anthias (Screenly OSE)</td><td><a href="https://github.com/Screenly/Anthias">Screenly/Anthias</a></td><td>Docker microservices, Redis + SQLite, Celery queue, Qt viewer</td></tr>'
        '</table>'
    ))

    return "\n".join(sections)


def build_page_14(page_id: str) -> str:
    """Page 14: Use Case Catalog — Advertiser Scenarios (v3, improved Thai)."""
    global _code_block_count
    _code_block_count = 0
    sections = []

    sections.append(toc())

    sections.append(info_panel(
        "<p><strong>หน้านี้รวบรวม scenarios จากมุมมองของ <em>ผู้ลงโฆษณา</em></strong> "
        "&mdash; แต่ละ scenario อธิบายว่า &ldquo;ถ้าลงโฆษณาแบบนี้ในช่วงเวลานี้ จะเกิดอะไรขึ้นบ้าง&rdquo;</p>"
        "<p><strong>6 รูปแบบที่ครอบคลุม:</strong> "
        "(1) Takeover &mdash; ซื้อช่วงเวลาแบบ exclusive &nbsp;"
        "(2) Exact Time &mdash; กำหนดเวลาเล่นชัดเจน &nbsp;"
        "(3) Guaranteed &mdash; รับประกันจำนวนครั้ง &nbsp;"
        "(4) Run of Schedule &mdash; กระจายตลอดวัน &nbsp;"
        "(5) Daypart Targeting &mdash; กำหนด time window สำหรับโฆษณา &nbsp;"
        "(6) Cancel &amp; Override &mdash; ยกเลิกโฆษณากลางคัน</p>"
        "<p>แต่ละ scenario มี <strong>Happy Path</strong> (กรณีปกติที่ควรเกิด) "
        "และ <strong>Edge Cases</strong> (กรณีพิเศษที่อาจเกิดขึ้น) พร้อม diagram</p>"
        "<p><strong>Section 7: Avails &amp; Smart Booking</strong> &mdash; "
        "ระบบจองหลาย Block อัจฉริยะด้วย Avails API + Auto-suggest "
        "สำหรับ scenario ที่มีหลาย advertiser จองพร้อมกัน</p>"
    ))

    # Legend for Gantt diagrams

    # ──────────────────────────────────────────────────────────────
    # SECTION 1: Takeover
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>1. Takeover &mdash; จอง Time Block ให้โฆษณาเล่น 100% ของเวลา</h2>')
    sections.append(info_panel(
        "<p><strong>Takeover</strong> คือการซื้อช่วงเวลาแบบ exclusive บนป้ายโฆษณา &mdash; "
        "ในช่วงที่จอง โฆษณาของลูกค้าจะเล่น 100% ไม่มีโฆษณาอื่นแทรก</p>"
        "<ul>"
        "<li><strong>จอง:</strong> ต้องล่วงหน้าอย่างน้อย 5 นาที (ระบบบังคับ), แนะนำ &ge;1 ชั่วโมงเพื่อให้เจ้าของป้ายมีเวลา review</li>"
        "<li><strong>ถ้าช่วงเวลาทับซ้อน:</strong> ระบบ reject ทันที ต้องเลือกเวลาหรือป้ายอื่น</li>"
        "<li><strong>Creative:</strong> ต้องได้รับการอนุมัติจากเจ้าของป้ายก่อนถึงเวลา Takeover</li>"
        "</ul>"
    ))

    # ── UC-TK-1 ───────────────────────────────────────────────────
    sections.append('<h3>UC-TK-1: Happy Path &mdash; Takeover สำเร็จ</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าจอง Takeover ช่วง 12:00&ndash;13:00 บนป้าย A พร้อมอัปโหลด creative ล่วงหน้า 1 วัน</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>ส่ง notification ให้เจ้าของป้ายอนุมัติ &rarr; อนุมัติแล้ว status: <code>waiting-play</code> &rarr; ล็อก slot 12:00&ndash;13:00</td></tr>
<tr><td><strong>ตอนเล่นจริง</strong></td><td>เวลา 12:00 Player เปลี่ยนเป็น Takeover mode &mdash; โฆษณาลูกค้าเล่น loop ตลอด 1 ชั่วโมง ไม่มีโฆษณาอื่นแทรก</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP report แสดง plays ครบ 100% ของ slot ที่ซื้อ, status เปลี่ยนเป็น <code>done</code> หลัง 13:00</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-TK-1 Takeover Happy Path
    dateFormat HH:mm
    axisFormat %H:%M
    section ก่อน Takeover
    โฆษณาปกติ ROS         :done, pre, 11:00, 60m
    section Takeover Block 12-00 to 13-00
    TK START               :vert, tks, 12:00, 1m
    Brand X creative loop  :crit, tk, 12:00, 60m
    TK END                 :vert, tke, 13:00, 1m
    section หลัง Takeover
    โฆษณาปกติ ROS         :done, post, 13:00, 60m
    section PoP
    PoP batch ส่ง Server   :milestone, pop, 13:00, 0d""", page_id))
    sections.append(_gantt_legend())

    # ── UC-TK-2 ───────────────────────────────────────────────────
    sections.append('<h3>UC-TK-2: Edge Case &mdash; ช่วงเวลาทับซ้อน (Slot Conflict)</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้า B พยายามจอง Takeover 12:30&ndash;13:30 บนป้ายเดียวกัน ในขณะที่ลูกค้า A จอง 12:00&ndash;13:00 ไว้แล้ว</td></tr>
<tr><td><strong>ระบบตรวจสอบ</strong></td><td>ระบบพบว่าช่วงเวลาทับซ้อนกัน &rarr; ส่ง error: <code>ADVERTISEMENT_BILLBOARDS_ALREADY_IN_USE</code> กลับทันที</td></tr>
<tr><td><strong>ผลที่ลูกค้า B เจอ</strong></td><td>การจองล้มเหลว ต้องเลือกช่วงเวลาอื่น (เช่น 13:00&ndash;14:00) หรือเปลี่ยนป้าย</td></tr>
<tr><td><strong>ผลต่อลูกค้า A</strong></td><td>ไม่ถูกกระทบ Takeover ของ A ยังเล่นตาม schedule ปกติ</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([ลูกค้า B จอง TK 12:30-13:30]) e1@--> B{ช่วงเวลาว่างไหม?}
    B e2@-->|ว่าง| C[สร้าง exclusive booking]
    B e3@-->|ชน slot ของลูกค้า A 12:00-13:00| D[error: BILLBOARDS_ALREADY_IN_USE]
    D e4@--> E{ลูกค้า B เลือก}
    E e5@-->|เวลาอื่น| F[เช่น จอง 13:00-14:00 แทน]
    E e6@-->|ป้ายอื่น| G[เลือกป้ายที่ยังว่าง]
    F e7@--> C
    G e8@--> C
    C e9@--> H([จองสำเร็จ])
    e1@{ animation: slow }
    e2@{ animation: fast }
    e3@{ animation: slow }
    e4@{ animation: slow }
    e5@{ animation: fast }
    e6@{ animation: fast }
    e7@{ animation: fast }
    e8@{ animation: fast }
    e9@{ animation: fast }
    style D fill:#f8d7da,stroke:#dc3545
    style H fill:#d4edda,stroke:#28a745""", page_id))

    # ── UC-TK-3 ───────────────────────────────────────────────────
    sections.append('<h3>UC-TK-3: Edge Case &mdash; Creative ไม่ผ่าน Review ก่อนถึงเวลา</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าจอง Takeover 15:00 แต่ creative ยังอยู่ในสถานะ <code>waiting-approve</code> จนถึง 14:55</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>ถึงเวลา 15:00 แต่ creative ยังไม่ได้รับการอนุมัติ &rarr; Player ไม่มี Takeover schedule &rarr; เล่น ROS ปกติแทน</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>Takeover หาย PoP = 0 plays &mdash; ต้องติดต่อ Support เพื่อขอ make-good หรือคืนเงิน (กระบวนการ manual)</td></tr>
<tr><td><strong>วิธีป้องกัน</strong></td><td>ส่ง creative ล่วงหน้าอย่างน้อย 1 ชั่วโมง เพื่อให้เจ้าของป้ายมีเวลา review และอนุมัติ</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart LR
    A([ลูกค้าอัปโหลด Creative]) e1@--> B[status: draft]
    B e2@--> C[กด Publish]
    C e3@--> D[status: waiting-approve]
    D e4@--> E{เจ้าของป้ายอนุมัติ?}
    E e5@-->|อนุมัติก่อน 15:00| F[status: waiting-play]
    F e6@--> G([Takeover เล่นตาม schedule])
    E e7@-->|ยังไม่อนุมัติพอถึงเวลา| H[Takeover slot หาย]
    H e8@--> I([PoP = 0 ต้องขอ make-good])
    e1@{ animation: slow }
    e2@{ animation: fast }
    e3@{ animation: fast }
    e4@{ animation: slow }
    e5@{ animation: fast }
    e6@{ animation: fast }
    e7@{ animation: slow }
    e8@{ animation: slow }
    style H fill:#f8d7da,stroke:#dc3545
    style I fill:#fff3cd,stroke:#ffc107
    style G fill:#d4edda,stroke:#28a745""", page_id))

    # ──────────────────────────────────────────────────────────────
    # SECTION 2: Exact Time
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>2. Exact Time &mdash; โฆษณาต้องเล่นตรงเวลาที่กำหนด</h2>')
    sections.append(info_panel(
        "<p><strong>Exact Time</strong> เหมาะสำหรับโฆษณาที่ต้องการเล่น <em>ณ เวลาที่แน่นอน</em> "
        "เช่น เปิดตัว Flash Sale ตอน 12:00 หรือ tie-in กับ live broadcast &mdash; "
        "ระบบจะเล่นโฆษณาตรงช่วง <strong>window &plusmn;30 วินาที</strong> รอบเวลาเป้าหมาย</p>"
        "<ul>"
        "<li><strong>ถ้า ad ที่กำลังเล่นอยู่จบก่อน window ปิด:</strong> Exact Time เล่นทันที</li>"
        "<li><strong>ถ้า ad ที่กำลังเล่นอยู่ยาวเกิน window:</strong> Exact Time ถูก skip &rarr; ระบบเพิ่ม make-good ใน slot ถัดไป</li>"
        "</ul>"
    ))

    # ── UC-ET-1 ───────────────────────────────────────────────────
    sections.append('<h3>UC-ET-1: Happy Path &mdash; Flash Sale เล่นตรง 12:00</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าจอง Exact Time ที่ 12:00:00 สำหรับ Flash Sale 30 วินาที โดยอัปโหลด creative ล่วงหน้า 1 ชั่วโมง</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>Window เปิดที่ 11:59:30 &mdash; รอให้ ad ที่กำลังเล่นอยู่จบ หรือ interrupt ถ้าจะเกิน window</td></tr>
<tr><td><strong>ตอนเล่นจริง</strong></td><td>Flash Sale เล่น 30 วินาที ตั้งแต่ 12:00:00 &rarr; กลับเล่น ROS ปกติตอน 12:00:30</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>โฆษณาเล่นตรงเวลา (&plusmn;30 วินาที), PoP บันทึก 1 play ครบ</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-ET-1 Exact Time Flash Sale at 12-00
    dateFormat HH:mm:ss
    axisFormat %H:%M:%S
    tickInterval 30second
    section โฆษณา ROS ก่อนหน้า
    P2 Ad A 15s              :done, a1, 11:59:30, 15s
    section Exact Time Window
    Window เปิด 11-59-30     :vert, ws, 11:59:30, 1s
    เป้าหมาย 12-00-00        :milestone, et, 12:00:00, 0d
    Window ปิด 12-00-30      :vert, we, 12:00:30, 1s
    section Exact Time Play
    Flash Sale 30s           :crit, etad, 12:00:00, 30s
    ET จบ 12-00-30           :milestone, ee, 12:00:30, 0d
    section กลับ ROS
    P2 Ad B 15s              :done, a2, 12:00:30, 15s""", page_id))
    sections.append(_gantt_legend())

    # ── UC-ET-2 ───────────────────────────────────────────────────
    sections.append('<h3>UC-ET-2: Edge Case &mdash; Ad ที่กำลังเล่นอยู่ยาวเกิน Window</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>มี P2 ad ยาว 90 วินาที เริ่มเล่นตอน 11:59:10 &mdash; จะเล่นจบตอน 12:00:40 ซึ่งเลย window ปิด (12:00:30) ไปแล้ว</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>Exact Time ที่ตั้งไว้ถูก skip เพราะ window ปิดไปก่อน ad เดิมจบ</td></tr>
<tr><td><strong>ระบบชดเชย</strong></td><td>เพิ่ม Exact Time make-good เข้าใน sequence ถัดไป &mdash; โฆษณาจะเล่นหลัง 12:00:40</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>โฆษณาเล่นช้ากว่าเป้าหมายประมาณ 40 วินาที แต่ยังได้ 1 play ครบ</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-ET-2 ET Window Missed - Make-good
    dateFormat HH:mm:ss
    axisFormat %H:%M:%S
    tickInterval 30second
    section P2 Ad ที่กำลังเล่นอยู่
    P2 Ad 90s เริ่ม 11-59-10  :done, a1, 11:59:10, 90s
    section ET Window
    Window เปิด 11-59-30      :vert, ws, 11:59:30, 1s
    เป้าหมาย 12-00-00         :milestone, et, 12:00:00, 0d
    Window ปิด 12-00-30       :vert, we, 12:00:30, 1s
    section ผลลัพธ์
    Ad จบหลัง window          :milestone, ae, 12:00:40, 0d
    ET make-good 30s          :active, mg, 12:00:40, 30s""", page_id))
    sections.append(_gantt_legend())

    # ── UC-ET-3 ───────────────────────────────────────────────────
    sections.append('<h3>UC-ET-3: Edge Case &mdash; จองช้าเกินไป (Lead Time &lt;5 นาที)</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้ากด Publish โฆษณาตอน 11:58 แต่ตั้งเวลาเล่นไว้ที่ 12:00 &mdash; เหลือเวลาแค่ 2 นาที</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>ระบบตรวจสอบว่าเวลาเป้าหมายต้องอยู่ห่างจากปัจจุบันอย่างน้อย 5 นาที &rarr; ไม่ผ่าน validation</td></tr>
<tr><td><strong>ผลที่ลูกค้าเจอ</strong></td><td>ระบบแจ้ง error กลับมา &mdash; ต้องตั้งเวลาเล่นใหม่ให้อย่างน้อย 12:03 ขึ้นไป</td></tr>
<tr><td><strong>วิธีป้องกัน</strong></td><td>Plan และส่ง creative ล่วงหน้าให้มีเวลา review เพียงพอก่อนถึงเวลาเล่น</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([ลูกค้า Publish ET slot]) e1@--> B{เวลาเป้าหมาย >= ปัจจุบัน + 5 นาที?}
    B e2@-->|ใช่ เช่น จองตอน 11:54 เป้าหมาย 12:00| C[ผ่าน validation]
    C e3@--> D[สร้าง exclusive booking]
    D e4@--> E[ส่ง notification ให้เจ้าของป้าย]
    E e5@--> F([รอการอนุมัติ])
    B e6@-->|ไม่ใช่ เช่น จองตอน 11:58 เป้าหมาย 12:00| G[Validation error]
    G e7@--> H[ต้องตั้งเวลาใหม่]
    H e8@--> I([เลือกเวลาใหม่ที่ >= 12:03])
    e1@{ animation: slow }
    e2@{ animation: fast }
    e3@{ animation: fast }
    e4@{ animation: slow }
    e5@{ animation: slow }
    e6@{ animation: slow }
    e7@{ animation: slow }
    e8@{ animation: slow }
    style G fill:#f8d7da,stroke:#dc3545
    style F fill:#d4edda,stroke:#28a745""", page_id))

    # ──────────────────────────────────────────────────────────────
    # SECTION 3: Guaranteed
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>3. Guaranteed &mdash; รับประกันจำนวนครั้งที่เล่น</h2>')
    sections.append(info_panel(
        "<p><strong>Guaranteed</strong> คือการกำหนดว่าโฆษณาต้องเล่น <em>อย่างน้อย N ครั้ง</em> "
        "ต่อ 15 นาที / ชั่วโมง / วัน &mdash; ระบบจะรับประกัน minimum frequency นั้น "
        "แม้จะมีโฆษณา priority สูงกว่าแทรกเข้ามา</p>"
        "<ul>"
        "<li><strong>ถ้า Takeover หรือ Exact Time เข้ามาขัด:</strong> ระบบจะเพิ่ม make-good plays ในช่วงเวลาถัดไป</li>"
        "<li><strong>Frequency options:</strong> ต่อ 15 นาที, ต่อชั่วโมง, หรือต่อวัน</li>"
        "</ul>"
    ))

    # ── UC-G-1 ────────────────────────────────────────────────────
    sections.append('<h3>UC-G-1: Happy Path &mdash; 4 ครั้ง/ชั่วโมง ได้ครบทุก play</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าตั้งค่า frequency = 4 ครั้ง/ชั่วโมง, วันธรรมดา 08:00&ndash;18:00, creative ยาว 30 วินาที</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>กระจาย 4 plays ในแต่ละชั่วโมง (ทุก ~15 นาที) สลับกับโฆษณาอื่น</td></tr>
<tr><td><strong>ใน 1 ชั่วโมง</strong></td><td>เล่น 4 ครั้งตามที่รับประกัน ส่วนเวลาที่เหลือเป็น P2/P4 ads</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP report: 4 plays/hr &times; 10 hrs = 40 plays/วัน ครบ 100%</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-G-1 Guaranteed 4 plays per hour
    dateFormat HH:mm
    axisFormat %H:%M
    section Guaranteed slots
    G play 1 at 08-00      :crit, g1, 08:00, 1m
    G play 2 at 08-15      :crit, g2, 08:15, 1m
    G play 3 at 08-30      :crit, g3, 08:30, 1m
    G play 4 at 08-45      :crit, g4, 08:45, 1m
    section P2 fills ส่วนที่เหลือ
    P2 fills               :done, f1, 08:01, 14m
    P2 fills               :done, f2, 08:16, 14m
    P2 fills               :done, f3, 08:31, 14m
    P2 fills               :done, f4, 08:46, 14m""", page_id))
    sections.append(_gantt_legend())

    # ── UC-G-2 ────────────────────────────────────────────────────
    sections.append('<h3>UC-G-2: Edge Case &mdash; Takeover เข้ามาขัด ทำให้ได้ไม่ครบ</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>มี Takeover ของลูกค้าอื่นจอง 09:00&ndash;09:30 บนป้ายเดียวกัน ทับซ้อนกับ Guaranteed campaign</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>Takeover มี priority สูงกว่า &rarr; Guaranteed slots ที่อยู่ในช่วง 09:00&ndash;09:30 ถูก block &rarr; ได้เล่นแค่ 2 ครั้งในชั่วโมง 09:00 (แทนที่จะได้ 4 ครั้ง)</td></tr>
<tr><td><strong>ระบบชดเชย</strong></td><td>เพิ่ม make-good 2 plays ต้นชั่วโมง 10:00 เพื่อให้ยอดรวมครบ</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>ยังคงได้ 4 plays/hr เมื่อนับรวม make-good แต่บางครั้งอาจขยับมาอยู่ในชั่วโมงถัดไป</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-G-2 Takeover Blocks Guaranteed Slots
    dateFormat HH:mm
    axisFormat %H:%M
    section ชั่วโมง 09:00
    Takeover Block 30 นาที  :crit, tk, 09:00, 30m
    G play 3 at 09-30       :crit, g3, 09:30, 1m
    G play 4 at 09-45       :crit, g4, 09:45, 1m
    section Make-good ชั่วโมง 10:00
    Make-good play 1        :active, mg1, 10:00, 1m
    Make-good play 2        :active, mg2, 10:05, 1m
    G play 3 at 10-15       :crit, g5, 10:15, 1m
    G play 4 at 10-30       :crit, g6, 10:30, 1m""", page_id))
    sections.append(_gantt_legend())

    # ──────────────────────────────────────────────────────────────
    # SECTION 4: Run of Schedule
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>4. Run of Schedule &mdash; กระจายโฆษณาตลอด Operating Hours</h2>')
    sections.append(info_panel(
        "<p><strong>Run of Schedule (ROS)</strong> คือรูปแบบที่ระบบ <em>กระจายโฆษณา</em> "
        "ให้สม่ำเสมอตลอดช่วงเวลาที่เปิด &mdash; ไม่รับประกันเวลาเล่นที่แน่นอน "
        "แต่รับประกัน fair share ของ available slots ตามงบประมาณที่ซื้อ</p>"
        "<p><strong>Approval flow:</strong> สร้าง campaign &rarr; กด Publish &rarr; เจ้าของป้ายอนุมัติ &rarr; รอถึงวันเริ่ม &rarr; เล่น</p>"
    ))

    # ── UC-P2-1 ───────────────────────────────────────────────────
    sections.append('<h3>UC-P2-1: Happy Path &mdash; Campaign 2 สัปดาห์ เล่นต่อเนื่อง</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าสร้าง campaign 14 วัน, เฉพาะวันธรรมดา 07:00&ndash;22:00, เลือก package "target-reach", creative ยาว 15 วินาที</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>ส่งให้เจ้าของป้ายอนุมัติ &rarr; อนุมัติแล้ว &rarr; รอถึงวันเริ่ม &rarr; Player ดาวน์โหลด creative และเริ่มเล่น</td></tr>
<tr><td><strong>ระหว่าง campaign</strong></td><td>โฆษณากระจายสม่ำเสมอ สลับกับโฆษณาอื่นตามลำดับ priority</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP report อัปเดตทุกวัน, status เปลี่ยนเป็น <code>done</code> หลังสิ้นสุด campaign</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart LR
    A([สร้าง Campaign]) e1@--> B[เลือก Package + อัปโหลด Creative]
    B e2@--> C[กำหนด date range + วันที่เล่น]
    C e3@--> D[กด Publish]
    D e4@--> E[เจ้าของป้ายรับ notification]
    E e5@--> F{อนุมัติ?}
    F e6@-->|อนุมัติ| G[status: waiting-play]
    F e7@-->|ปฏิเสธ| H[status: rejected]
    H e8@--> I[แก้ creative หรือยกเลิก]
    G e9@--> J[ถึงวันเริ่ม campaign]
    J e10@--> K[Player ดาวน์โหลด + เล่น]
    K e11@--> L([PoP รายงานทุก play])
    e1@{ animation: slow }
    e2@{ animation: slow }
    e3@{ animation: slow }
    e4@{ animation: slow }
    e5@{ animation: slow }
    e6@{ animation: fast }
    e7@{ animation: slow }
    e8@{ animation: slow }
    e9@{ animation: slow }
    e10@{ animation: fast }
    e11@{ animation: slow }
    style H fill:#f8d7da,stroke:#dc3545
    style L fill:#d4edda,stroke:#28a745""", page_id))

    # ── UC-P2-2 ───────────────────────────────────────────────────
    sections.append('<h3>UC-P2-2: Edge Case &mdash; Creative ถูกปฏิเสธระหว่าง Review</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าส่ง creative ที่ไม่ตรงกับ spec ของป้าย เช่น ขนาดวิดีโอผิด หรือมีเนื้อหาที่เจ้าของป้ายไม่อนุมัติ</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>เจ้าของป้ายปฏิเสธ creative &rarr; status เปลี่ยนเป็น <code>rejected</code> &rarr; ระบบแจ้งลูกค้าทาง notification</td></tr>
<tr><td><strong>ผลที่ลูกค้าเจอ</strong></td><td>Campaign หยุดเล่น &mdash; ต้องอัปโหลด creative ใหม่แล้ว Publish ใหม่อีกครั้ง</td></tr>
<tr><td><strong>ระหว่างรอ</strong></td><td>ป้ายเล่น house filler แทน ลูกค้าไม่เสีย plays ระหว่างช่วงที่ยังไม่มี creative ผ่าน</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([กด Publish]) e1@--> B[เจ้าของป้ายรับ notification]
    B e2@--> C{ตรวจ creative}
    C e3@-->|ผ่าน| D[status: approved]
    D e4@--> E([Campaign เล่นตาม schedule])
    C e5@-->|ไม่ผ่าน| F[status: rejected]
    F e6@--> G[แจ้งลูกค้าทาง notification]
    G e7@--> H{ลูกค้าเลือก}
    H e8@-->|แก้ creative| I[อัปโหลด creative ใหม่]
    H e9@-->|ยกเลิก| J([Campaign cancelled])
    I e10@--> K[Publish ใหม่]
    K e11@--> B
    e1@{ animation: slow }
    e2@{ animation: slow }
    e3@{ animation: fast }
    e4@{ animation: fast }
    e5@{ animation: slow }
    e6@{ animation: slow }
    e7@{ animation: slow }
    e8@{ animation: fast }
    e9@{ animation: slow }
    e10@{ animation: fast }
    e11@{ animation: slow }
    style F fill:#f8d7da,stroke:#dc3545
    style E fill:#d4edda,stroke:#28a745""", page_id))

    # ── UC-P2-3 ───────────────────────────────────────────────────
    sections.append('<h3>UC-P2-3: Edge Case &mdash; ป้ายออฟไลน์ระหว่าง Campaign</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ป้ายโฆษณาขาดการเชื่อมต่อ 4 ชั่วโมง ขณะที่ campaign กำลังเล่นอยู่</td></tr>
<tr><td><strong>ระหว่างออฟไลน์</strong></td><td>ป้ายเล่นต่อจาก cache ที่ดาวน์โหลดไว้ (นาน 4 ชั่วโมง) &mdash; ถ้าออฟไลน์นานกว่านั้น จะสลับเล่น house filler แทน</td></tr>
<tr><td><strong>PoP ระหว่างออฟไลน์</strong></td><td>ระบบเก็บ play events ไว้ใน queue ก่อน &mdash; ยังไม่ส่งขึ้น server</td></tr>
<tr><td><strong>หลังกลับ online</strong></td><td>ป้ายส่ง PoP ที่ค้างไว้ทั้งหมดขึ้น server ในครั้งเดียว</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP report อัปเดตหลังป้ายกลับ online &mdash; ช่วงที่ออฟไลน์ &gt;4 ชั่วโมง plays อาจลดลงเพราะเล่น house filler</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-P2-3 ป้ายออฟไลน์ระหว่าง Campaign
    dateFormat HH:mm
    axisFormat %H:%M
    section สัญญาณ
    Online ปกติ            :done, n1, 08:00, 60m
    ออฟไลน์ 4 ชั่วโมง      :crit, n2, 09:00, 240m
    กลับ online            :done, n3, 13:00, 60m
    section โฆษณาที่เล่น
    Campaign ads ปกติ      :done, c1, 08:00, 60m
    Tier 2 cache ads       :active, c2, 09:00, 240m
    Campaign ads กลับมา   :done, c3, 13:00, 60m
    section PoP Reporting
    PoP ส่ง server ปกติ   :done, p1, 08:00, 60m
    PoP queue ใน device    :active, pq, 09:00, 240m
    PoP batch sync         :milestone, ps, 13:00, 0d""", page_id))
    sections.append(_gantt_legend())

    # ── UC-P2-4 ───────────────────────────────────────────────────
    sections.append('<h3>UC-P2-4: Edge Case &mdash; ลง Campaign หลาย Creative (Rotation)</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าอัปโหลด 3 creatives ใน campaign เดียว เช่น ไทย, อังกฤษ, และเวอร์ชันลด 50%</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>หมุนเวียน creatives ทั้ง 3 ตาม rotation rules &mdash; แต่ละ creative ต้องผ่าน approval จากเจ้าของป้ายก่อน</td></tr>
<tr><td><strong>ถ้า creative หนึ่งถูกปฏิเสธ</strong></td><td>creative นั้นหลุดออกจาก rotation &mdash; ที่เหลือยังเล่นต่อได้ตามปกติ</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP report แยก plays ตาม creative ID &mdash; ดูได้ว่า version ไหน performance ดีกว่า</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-P2-4 Multi-Creative Rotation (1 ชั่วโมง)
    dateFormat HH:mm
    axisFormat %H:%M
    section Creative A ภาษาไทย
    Creative A play 1      :done, a1, 08:00, 1m
    Creative A play 2      :done, a2, 08:20, 1m
    Creative A play 3      :done, a3, 08:40, 1m
    section Creative B ภาษาอังกฤษ
    Creative B play 1      :active, b1, 08:07, 1m
    Creative B play 2      :active, b2, 08:27, 1m
    Creative B play 3      :active, b3, 08:47, 1m
    section Creative C ลด 50 pct
    Creative C play 1      :crit, c1, 08:14, 1m
    Creative C play 2      :crit, c2, 08:34, 1m
    Creative C play 3      :crit, c3, 08:54, 1m""", page_id))
    sections.append(_gantt_legend())

    # ──────────────────────────────────────────────────────────────
    # SECTION 5: Daypart Targeting
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>5. Daypart Targeting &mdash; กำหนด Time Window สำหรับโฆษณา</h2>')
    sections.append(info_panel(
        "<p><strong>Daypart Targeting (P1-DG)</strong> คือรูปแบบที่ลูกค้าระบุว่าโฆษณาต้องเล่น "
        "<em>เฉพาะในช่วงเวลาที่กำหนด</em> เช่น Morning Peak 08:00&ndash;10:00 หรือ Evening Rush 17:00&ndash;19:00 "
        "พร้อมรับประกัน minimum frequency ภายใน window นั้น</p>"
        "<ul>"
        "<li><strong>Algorithm:</strong> Center-offset distribution &mdash; "
        "interval = windowDuration / plays, offset = interval / 2 "
        "&rarr; กระจาย plays สม่ำเสมอตลอด window ไม่กระจุกที่ต้น</li>"
        "<li><strong>plays_in_window:</strong> ลูกค้าระบุ frequency ต่อชั่วโมง "
        "&rarr; ระบบคำนวณ round(playsPerHour &times; windowHours)</li>"
        "<li><strong>Make-good policy:</strong> 3 ระดับ &mdash; "
        "Level 1 (repack ใน window เดิม) &rarr; Level 2 (ย้าย slot วันเดียวกัน) &rarr; Level 3 (credit คืน)</li>"
        "</ul>"
    ))

    # ── UC-DP-1 ────────────────────────────────────────────────────
    sections.append('<h3>UC-DP-1: Happy Path &mdash; P1-DG 6 plays ใน Morning Peak 08:00&ndash;10:00</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าตั้งค่า P1-DG: 3 plays/hour, window 08:00&ndash;10:00 (Morning Peak), creative ยาว 30 วินาที</td></tr>
<tr><td><strong>ระบบคำนวณ</strong></td><td>3 plays/hr &times; 2 hr = 6 plays &rarr; interval = 120 min / 6 = 20 min, offset = 10 min</td></tr>
<tr><td><strong>Play times</strong></td><td>08:10, 08:30, 08:50, 09:10, 09:30, 09:50 (ทุก 20 นาที เริ่มจาก offset 10 นาที)</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>PoP: 6 plays ครบใน window &mdash; กระจายสม่ำเสมอ ไม่กระจุกที่ต้น window</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-DP-1 P1-DG Morning Peak 08:00 to 10:00 (6 plays)
    dateFormat HH:mm
    axisFormat %H:%M
    section Daypart Window
    Window Open 08-00      :vert, wo, 08:00, 1m
    Window Close 10-00     :vert, wc, 10:00, 1m
    section P1-DG plays center-offset ทุก 20 นาที
    DG play 1 at 08-10     :crit, d1, 08:10, 1m
    DG play 2 at 08-30     :crit, d2, 08:30, 1m
    DG play 3 at 08-50     :crit, d3, 08:50, 1m
    DG play 4 at 09-10     :crit, d4, 09:10, 1m
    DG play 5 at 09-30     :crit, d5, 09:30, 1m
    DG play 6 at 09-50     :crit, d6, 09:50, 1m
    section P2 fills ระหว่าง DG plays
    P2 fills               :done, f1, 08:00, 10m
    P2 fills               :done, f2, 08:11, 19m
    P2 fills               :done, f3, 08:31, 19m
    P2 fills               :done, f4, 08:51, 19m
    P2 fills               :done, f5, 09:11, 19m
    P2 fills               :done, f6, 09:31, 19m
    P2 fills               :done, f7, 09:51, 9m""", page_id))
    sections.append(_gantt_legend())

    # ── UC-DP-2 ────────────────────────────────────────────────────
    sections.append('<h3>UC-DP-2: Edge Case &mdash; Takeover เข้าขัด Window ทำให้ต้อง Make-good</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>Takeover ของลูกค้าอื่นจอง 09:00&ndash;09:30 ทับซ้อนกับ P1-DG window 08:00&ndash;10:00</td></tr>
<tr><td><strong>สิ่งที่เกิดขึ้น</strong></td><td>P1-TK มี priority สูงกว่า &rarr; DG plays ที่ 09:10 และ 09:30 ถูก block &rarr; เหลือเพียง 4 plays ใน window</td></tr>
<tr><td><strong>Make-good Level 1</strong></td><td>Window เหลือ 09:30&ndash;10:00 (30 นาที) &rarr; repack 1 play ที่ 09:40 ด้วย center-offset &rarr; รวมเป็น 5 plays</td></tr>
<tr><td><strong>Make-good Level 2</strong></td><td>ยังขาด 1 play &rarr; ย้ายไป slot เดียวกันในวันเดียวกัน ช่วง 06:00&ndash;22:00 ที่ไม่ใช่ TK block</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>ได้ครบ 6 plays ภายในวันเดียวกัน &mdash; แต่ 1 play อาจอยู่นอก window ต้นทาง</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-DP-2 Takeover Blocks P1-DG Window - Make-good Level 1
    dateFormat HH:mm
    axisFormat %H:%M
    section Daypart Window 08-00 to 10-00
    Window Open 08-00      :vert, wo, 08:00, 1m
    Window Close 10-00     :vert, wc, 10:00, 1m
    section P1-TK เข้าขัด
    Takeover Block         :crit, tk, 09:00, 30m
    section P1-DG plays ที่เล่นได้
    DG play 1 at 08-10     :crit, d1, 08:10, 1m
    DG play 2 at 08-30     :crit, d2, 08:30, 1m
    DG play 3 at 08-50     :crit, d3, 08:50, 1m
    DG play 4 at 09-50     :crit, d4, 09:50, 1m
    section Make-good Level 1 repack ใน window
    Level 1 repack 09-40   :active, mg1, 09:40, 1m""", page_id))
    sections.append(_gantt_legend())

    # ──────────────────────────────────────────────────────────────
    # SECTION 6: Cancel & Override
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>6. Cancel &amp; Override &mdash; ยกเลิกโฆษณากลางคัน</h2>')
    sections.append(info_panel(
        "<p><strong>Cancel</strong> เกิดขึ้นได้ 2 สถานการณ์ มีกฎสิทธิ์ที่ต่างกัน:</p>"
        "<ul>"
        "<li><strong>ก่อนเล่น (UC-CX-1):</strong> ลูกค้า, admin หรือเจ้าของป้ายยกเลิกได้ &mdash; "
        "Backend push <code>stop-advertisement</code> → Player ลบออกจาก local schedule → ROS fills เข้ามาแทน</li>"
        "<li><strong>ขณะเล่น (UC-CX-2):</strong> <strong>เฉพาะ Admin หรือเจ้าของป้ายเท่านั้น</strong> ที่ cancel ได้ "
        "&mdash; ลูกค้าไม่มีสิทธิ์ cancel ad ที่เริ่มเล่นแล้ว &mdash; "
        "เหตุผลหลัก: การละเมิดลิขสิทธิ์ / คำสั่งระงับการเผยแพร่ &rarr; <strong>หยุดทันที (hard stop)</strong> "
        "ไม่รอจบ clip → house filler เล่นแทนทันที</li>"
        "</ul>"
    ))

    # ── UC-CX-1 ───────────────────────────────────────────────────
    sections.append('<h3>UC-CX-1: Happy Path &mdash; Cancel ก่อนถึงเวลาเล่น</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>ลูกค้าจอง P2 campaign เริ่ม 10:00 แต่ตัดสินใจยกเลิกตอน 09:30 (ก่อนถึงเวลาเล่น)</td></tr>
<tr><td><strong>ระบบทำงาน</strong></td><td>Backend เปลี่ยน status → <code>cancelled</code> แล้ว push Pusher event <code>stop-advertisement {ad_code, reason: 'cancelled', version++}</code> ไปยังทุก Player ที่มี ad นี้อยู่</td></tr>
<tr><td><strong>Player ทำงาน</strong></td><td>รับ event → ลบ ad ออกจาก Tier 1 schedule ทันที → version bump → slot 10:00 เปิดว่าง → ADE re-fill ด้วย ROS ในรอบ sync ถัดไป</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>Ad ไม่เล่น, PoP = 0 plays ตั้งแต่ cancel &mdash; slot ถูก fill ด้วย ROS ads ของเจ้าของป้ายแทน</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-CX-1 Cancel ก่อนถึงเวลาเล่น
    dateFormat HH:mm
    axisFormat %H:%M
    section Schedule เดิม (ก่อน cancel)
    P2 Campaign X (scheduled)  :crit, orig, 10:00, 60m
    section Cancel Event at 09-30
    stop-advertisement push    :milestone, ev, 09:30, 0d
    Player ลบจาก schedule     :milestone, rm, 09:31, 0d
    section หลัง Cancel
    ROS fills แทน slot ว่าง   :done, ros, 10:00, 60m
    section PoP
    0 plays (cancelled)        :milestone, pop, 10:00, 0d""", page_id))
    sections.append(_gantt_legend())

    # ── UC-CX-2 ───────────────────────────────────────────────────
    sections.append('<h3>UC-CX-2: Edge Case &mdash; Cancel ขณะ Ad กำลังเล่นอยู่ (Hard Stop)</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>Ad 30 วินาทีกำลังเล่นอยู่ ถูก admin ระงับตอนที่เล่นไป 15 วินาที เนื่องจาก ad ละเมิดลิขสิทธิ์และมีคำสั่งให้ระงับการเผยแพร่ทันที</td></tr>
<tr><td><strong>ผู้มีสิทธิ์ cancel</strong></td><td><strong>Admin หรือเจ้าของป้ายเท่านั้น</strong> &mdash; ลูกค้าไม่สามารถ cancel ad ที่เริ่มเล่นแล้วได้</td></tr>
<tr><td><strong>เหตุผล</strong></td><td>การละเมิดลิขสิทธิ์, เนื้อหาไม่เหมาะสม, คำสั่งทางกฎหมายให้ระงับการเผยแพร่</td></tr>
<tr><td><strong>Player ทำงาน</strong></td><td>รับ <code>stop-advertisement</code> event → <strong>หยุดทันที (hard stop)</strong> ไม่รอให้จบ clip → สลับเป็น house filler ทันที ห้ามจอดำ</td></tr>
<tr><td><strong>PoP บันทึก</strong></td><td>Play ที่เล่น <strong>จบก่อน</strong> cancel event = นับ &mdash; Play ที่กำลังเล่นอยู่ตอนถูก interrupt (15s ใน 30s) = <strong>ไม่นับ</strong> (partial play)</td></tr>
<tr><td><strong>ผลที่ลูกค้าได้รับ</strong></td><td>Ad ถูกลบจาก schedule ทั้งหมดทันที &mdash; PoP = เฉพาะ plays ที่เล่นจบก่อน event เท่านั้น &mdash; ไม่มี make-good เนื่องจากเป็น policy violation</td></tr>
</table>""")
    sections.append(mermaid_diagram("""gantt
    title UC-CX-2 Cancel ขณะเล่น - Hard Stop at 10-00-15 (Ad 30s)
    dateFormat HH:mm:ss
    axisFormat %M:%S
    section Ad กำลังเล่น
    Campaign X ad 30s           :active, playing, 10:00:00, 15s
    section Hard Stop at 10-00-15
    stop-advertisement received :milestone, ev, 10:00:15, 0d
    section หลัง Hard Stop
    House Filler ทันที          :done, fill, 10:00:15, 45s
    section PoP
    Partial play ไม่นับ         :milestone, pop, 10:00:15, 0d""", page_id))
    sections.append(_gantt_legend())

    # ──────────────────────────────────────────────────────────────
    # SECTION 7: Avails & Smart Booking
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>7. Avails &amp; Smart Booking &mdash; จองหลาย Block อัจฉริยะ</h2>')
    sections.append(info_panel(
        "<p><strong>ปัญหาของการจอง Takeover หลาย Block:</strong> ถ้าระบบรอให้ user submit แล้วค่อย reject "
        "เมื่อ slot ชน &mdash; นั่นคือ &ldquo;reject-at-submit&rdquo; ซึ่ง industry ถือว่า UX แย่ที่สุด "
        "(Broadsign, Xibo, Signagelive ทุกเจ้าหลีกเลี่ยง) &mdash; ทางออกคือ 3 Layer:</p>"
        "<ol>"
        "<li><strong>Priority Tier</strong> &mdash; กฎว่าใครชนะใครเมื่อ conflict (TK &gt; G &gt; Daypart &gt; ROS)</li>"
        "<li><strong>Avails API</strong> &mdash; ตรวจ availability จริงก่อน submit &mdash; "
        "แสดงว่า slot ไหน &ldquo;ว่าง&rdquo; หรือ &ldquo;ไม่ว่าง&rdquo; "
        "(ไม่เปิดเผยว่าใครจอง &mdash; privacy)</li>"
        "<li><strong>Auto-suggest</strong> &mdash; ถ้า slot ที่ต้องการไม่ว่าง ระบบเสนอ alternatives "
        "กระจายสม่ำเสมอตลอดวัน ไม่ให้ user ต้อง trial-and-error เอง</li>"
        "</ol>"
        "<p>Scenario: <strong>C จอง 5 x 1hr Takeover</strong> (UC-AV-1) แล้ว "
        "<strong>D ต้องการ 5 x 1hr เช่นกัน</strong> (UC-AV-2) &mdash; "
        "ระบบ handle conflict โดยที่ทั้งคู่ได้ครบ 5 slots ไม่ชนกันเลย</p>"
    ))

    # ── UC-AV-1 ───────────────────────────────────────────────────
    sections.append('<h3>UC-AV-1: Happy Path &mdash; C จอง 5 x 1hr Takeover ผ่าน Avails API</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>C ต้องการลง ad ต่อเนื่อง 1 ชั่วโมง 5 รอบ/วัน บนป้าย A &mdash; ป้ายมี A และ B ลง ROS อยู่ก่อนแล้ว</td></tr>
<tr><td><strong>Avails API ทำงาน</strong></td><td>C query <code>GET /v2/avails?screen_id=A&amp;date=2026-03-01&amp;duration=60m&amp;type=takeover&amp;count=5</code> &mdash; ระบบสแกน operating hours 06:00&ndash;22:00 ตรวจทุก 1hr window ว่ามี Takeover อื่นชนไหม</td></tr>
<tr><td><strong>ผลลัพธ์</strong></td><td>08:00, 10:00, 14:00, 16:00, 19:00 ว่างทั้งหมด (A/B มีแค่ ROS ซึ่ง Takeover ชนะ) &mdash; ระบบแสดง preview timeline + C confirm &rarr; Lock 5 blocks ทันที</td></tr>
<tr><td><strong>ผลต่อ A และ B</strong></td><td>ROS (P4): ถูก displace ช่วง Takeover ทั้ง 5 blocks &mdash; ไม่มี make-good (ROS = best effort). ถ้า A/B มี Guaranteed: ระบบสร้าง make-good อัตโนมัติ</td></tr>
<tr><td><strong>Privacy</strong></td><td>Avails API ไม่เปิดเผยว่า slot ถูกจองโดยใคร &mdash; แสดงเพียง &ldquo;available&rdquo; หรือ &ldquo;unavailable&rdquo; เท่านั้น</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([C ต้องการ 5 Block x 1hr Takeover]) e1@--> B[Avails API Query]
    B e2@--> C[สแกน operating hours 06-00 to 22-00]
    C e3@--> D{ตรวจ Priority Tier<br/>ทุก 1hr window}
    D e4@--> E[08-00, 10-00, 14-00, 16-00, 19-00<br/>ว่างทั้งหมด]
    E e5@--> F[5/5 slots available]
    F e6@--> G[แสดง Preview Timeline และราคา]
    G e7@--> H{C confirm}
    H e8@-->|ยืนยัน| I[Lock 5 Takeover blocks]
    H e9@-->|ขอปรับเวลา| C
    I e10@--> J[Pusher push schedule ไปยัง Players]
    J e11@--> K([Booking สำเร็จ])
    e1@{ animation: slow }
    e2@{ animation: slow }
    e3@{ animation: fast }
    e4@{ animation: fast }
    e5@{ animation: fast }
    e6@{ animation: slow }
    e7@{ animation: slow }
    e8@{ animation: fast }
    e9@{ animation: slow }
    e10@{ animation: slow }
    e11@{ animation: fast }
    style K fill:#d4edda,stroke:#28a745
    style I fill:#d4edda,stroke:#28a745""", page_id))
    sections.append('<h4>Timeline: C Takeover Blocks + A/B ROS (วัน 1 มีค.)</h4>')
    sections.append(mermaid_diagram("""gantt
    title UC-AV-1 C จอง 5 Takeover Block 1hr
    dateFormat HH:mm
    axisFormat %H:%M
    section A and B ROS
    A and B ROS fill        :done, ab0, 06:00, 120m
    A and B ROS fill        :done, ab1, 09:00, 60m
    A and B ROS fill        :done, ab2, 11:00, 180m
    A and B ROS fill        :done, ab3, 15:00, 60m
    A and B ROS fill        :done, ab4, 17:00, 120m
    A and B ROS fill        :done, ab5, 20:00, 120m
    section C Takeover 5 Blocks
    C Block 1 Takeover 1hr  :crit, c1, 08:00, 60m
    C Block 2 Takeover 1hr  :crit, c2, 10:00, 60m
    C Block 3 Takeover 1hr  :crit, c3, 14:00, 60m
    C Block 4 Takeover 1hr  :crit, c4, 16:00, 60m
    C Block 5 Takeover 1hr  :crit, c5, 19:00, 60m
    section Booking Events
    C ยืนยัน booking        :milestone, m1, 07:55, 0d
    5 slots locked           :milestone, m2, 07:56, 0d""", page_id))
    sections.append(_gantt_legend())
    sections.append('<h4>Avails API: โครงสร้าง Response</h4>')
    sections.append("""<table>
<tr><th>Field</th><th>Type</th><th>ความหมาย</th><th>ตัวอย่าง</th></tr>
<tr><td><code>requested</code></td><td>Window[]</td><td>slots ที่ user ขอ (ถ้า specify)</td><td><code>[{start:"08:00", duration:60}]</code></td></tr>
<tr><td><code>available</code></td><td>Window[]</td><td>slots ที่ว่างจริง พร้อม lock ได้ทันที</td><td><code>[{start:"08:00"}, {start:"10:00"}, ...]</code></td></tr>
<tr><td><code>conflicts</code></td><td>Conflict[]</td><td>slots ที่ไม่ว่าง &mdash; ไม่ระบุว่าใครจอง (privacy)</td><td><code>[{start:"13:00", reason:"unavailable"}]</code></td></tr>
<tr><td><code>suggestions</code></td><td>Suggestion[]</td><td>auto-suggest เรียงตาม distribution score</td><td><code>[{start:"07:00", score:0.95}, ...]</code></td></tr>
<tr><td><code>total_requested</code></td><td>number</td><td>จำนวน slots ที่ขอ</td><td><code>5</code></td></tr>
<tr><td><code>total_available</code></td><td>number</td><td>จำนวน slots ที่ว่างจริง</td><td><code>5</code> (UC-AV-1) / <code>0</code> (UC-AV-2)</td></tr>
</table>""")

    # ── UC-AV-2 ───────────────────────────────────────────────────
    sections.append('<h3>UC-AV-2: D จองแบบเดียวกัน หลัง C &mdash; Auto-suggest หา Alternatives</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>D ต้องการ 5 x 1hr Takeover บนป้ายเดียวกัน วันเดียวกัน &mdash; C ล็อก 08:00, 10:00, 14:00, 16:00, 19:00 ไปแล้ว</td></tr>
<tr><td><strong>Avails API ตรวจ</strong></td><td>ทุก slot ที่ D ต้องการชนกับ C Takeover ทั้งหมด (Takeover vs Takeover = hard reject) &mdash; <code>total_available: 0</code> &rarr; trigger Auto-suggest ทันที</td></tr>
<tr><td><strong>Auto-suggest ทำงาน</strong></td><td>สแกน Takeover-free windows ที่เหลือ 11 slots &rarr; แบ่งวัน 5 zones &rarr; เลือก 1 slot/zone ที่ห่างจาก C's blocks มากที่สุด &rarr; เสนอ 07:00, 09:00, 12:00, 15:00, 17:00</td></tr>
<tr><td><strong>D เลือก</strong></td><td>Confirm ทั้ง 5 suggestions หรือปรับบางช่วงได้ &mdash; Lock สำเร็จ ไม่มี overlap กับ C แม้แต่นาทีเดียว</td></tr>
<tr><td><strong>ผลลัพธ์รวม</strong></td><td>C ได้ 5 blocks (08-09, 10-11, 14-15, 16-17, 19-20), D ได้ 5 blocks (07-08, 09-10, 12-13, 15-16, 17-18) &mdash; A/B ROS เล่นใน 6 ชั่วโมงที่เหลือ (06, 11, 13, 18, 20, 21)</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([D ต้องการ 5 Block x 1hr - slots เดียวกับ C]) e1@--> B[Avails API Query]
    B e2@--> C{ตรวจ Priority Tier<br/>ทุก slot ที่ D ขอ}
    C e3@-->|08-00 to 09-00| D1[C Takeover - CONFLICT]
    C e4@-->|10-00 to 11-00| D2[C Takeover - CONFLICT]
    C e5@-->|14-00 to 15-00| D3[C Takeover - CONFLICT]
    C e6@-->|16-00 to 17-00| D4[C Takeover - CONFLICT]
    C e7@-->|19-00 to 20-00| D5[C Takeover - CONFLICT]
    D1 e8@--> E[0/5 slots available]
    D2 e9@--> E
    D3 e10@--> E
    D4 e11@--> E
    D5 e12@--> E
    E e13@--> F[Auto-suggest triggered]
    F e14@--> G[สแกน Takeover-free windows<br/>11 slots เหลือจาก 16]
    G e15@--> H[Even distribution<br/>แบ่ง 5 zones กระจายตลอดวัน]
    H e16@--> I[Suggest: 07-00, 09-00, 12-00, 15-00, 17-00]
    I e17@--> J{D เลือก}
    J e18@-->|confirm ทั้งหมด| K[Lock 5 alternative Takeover]
    J e19@-->|ปรับ slots บางช่วง| L[D เลือก subset และเพิ่มเอง]
    L e20@--> K
    K e21@--> M([Booking สำเร็จ - ไม่ชน C เลย])
    e1@{ animation: slow }
    e2@{ animation: slow }
    e3@{ animation: slow }
    e4@{ animation: slow }
    e5@{ animation: slow }
    e6@{ animation: slow }
    e7@{ animation: slow }
    e8@{ animation: fast }
    e9@{ animation: fast }
    e10@{ animation: fast }
    e11@{ animation: fast }
    e12@{ animation: fast }
    e13@{ animation: fast }
    e14@{ animation: fast }
    e15@{ animation: fast }
    e16@{ animation: fast }
    e17@{ animation: slow }
    e18@{ animation: fast }
    e19@{ animation: slow }
    e20@{ animation: fast }
    e21@{ animation: fast }
    style M fill:#d4edda,stroke:#28a745
    style E fill:#f8d7da,stroke:#dc3545
    style F fill:#fff3cd,stroke:#ffc107
    style I fill:#cce5ff,stroke:#004085""", page_id))
    sections.append('<h4>Auto-suggest Algorithm: Even Distribution</h4>')
    sections.append("""<table>
<tr><th>Step</th><th>การทำงาน</th><th>ผลลัพธ์</th></tr>
<tr><td><strong>1. Load operating hours</strong></td><td>06:00&ndash;22:00 = 16 possible 1hr windows</td><td>[06:00, 07:00, ..., 21:00]</td></tr>
<tr><td><strong>2. Remove locked Takeovers</strong></td><td>C: 08:00, 10:00, 14:00, 16:00, 19:00 ถูกหัก</td><td>11 slots remaining</td></tr>
<tr><td><strong>3. Zone division</strong></td><td>แบ่ง day เป็น 5 zones: Early (06-08), Morning (08-11), Midday (11-14), Afternoon (14-18), Evening (18-22)</td><td>แต่ละ zone เลือก best available slot</td></tr>
<tr><td><strong>4. Score by gap</strong></td><td>slot ที่ห่างจาก Takeover blocks ข้างเคียงมากที่สุด = score สูง &mdash; หลีกเลี่ยง slot ที่ติดกับ Takeover อยู่แล้ว</td><td>07:00(0.95), 09:00(0.92), 12:00(0.88), 15:00(0.90), 17:00(0.87)</td></tr>
<tr><td><strong>5. Return sorted</strong></td><td>เรียง chronologically ให้ D เห็น timeline ชัด</td><td>07:00, 09:00, 12:00, 15:00, 17:00</td></tr>
</table>""")
    sections.append('<h4>Timeline: Final Daily Schedule — C + D + A/B (วัน 1 มีค.)</h4>')
    sections.append(mermaid_diagram("""gantt
    title UC-AV-2 Final Daily Schedule - C and D and A/B
    dateFormat HH:mm
    axisFormat %H:%M
    section A and B ROS
    A and B ROS fill        :done, ab1, 06:00, 60m
    A and B ROS fill        :done, ab2, 11:00, 60m
    A and B ROS fill        :done, ab3, 13:00, 60m
    A and B ROS fill        :done, ab4, 18:00, 60m
    A and B ROS fill        :done, ab5, 20:00, 120m
    section C Takeover
    C Block 1               :crit, c1, 08:00, 60m
    C Block 2               :crit, c2, 10:00, 60m
    C Block 3               :crit, c3, 14:00, 60m
    C Block 4               :crit, c4, 16:00, 60m
    C Block 5               :crit, c5, 19:00, 60m
    section D Takeover Auto-suggested
    D Block 1               :active, d1, 07:00, 60m
    D Block 2               :active, d2, 09:00, 60m
    D Block 3               :active, d3, 12:00, 60m
    D Block 4               :active, d4, 15:00, 60m
    D Block 5               :active, d5, 17:00, 60m""", page_id))
    sections.append(_gantt_legend())

    # ── UC-AV-3 ───────────────────────────────────────────────────
    sections.append('<h3>UC-AV-3: Edge Case &mdash; Slots ไม่เพียงพอ (E จองหลัง C และ D)</h3>')
    sections.append("""<table>
<tr><th>หัวข้อ</th><th>รายละเอียด</th></tr>
<tr><td><strong>สถานการณ์</strong></td><td>E ต้องการ 5 x 1hr Takeover วันเดียวกัน หลังจาก C และ D จองครบแล้ว &mdash; C 5 blocks + D 5 blocks = 10 จาก 16 slots ถูกล็อก เหลือเพียง 6 slots ว่าง</td></tr>
<tr><td><strong>Auto-suggest เสนอ</strong></td><td>เสนอได้สูงสุด 5 จาก 6 ที่เหลือ (06:00, 11:00, 13:00, 18:00, 20:00) &mdash; ถ้า E ต้องการ &gt;6 slots: ระบบแจ้ง &ldquo;available: 6, requested: N&rdquo; พร้อมแสดง options</td></tr>
<tr><td><strong>Option 1</strong></td><td>จอง slots ที่มีวันนี้ก่อน + Avails query วันถัดไปสำหรับ slots ที่ขาด</td></tr>
<tr><td><strong>Option 2</strong></td><td>เลือกวันอื่นที่มี slots ว่างครบ 5 (ระบบ suggest วันที่ดีที่สุดอัตโนมัติ)</td></tr>
<tr><td><strong>Option 3</strong></td><td>Waitlist &mdash; แจ้ง notification เมื่อมี cancellation เปิด slot ว่าง</td></tr>
</table>""")
    sections.append(mermaid_diagram("""flowchart TD
    A([E ต้องการ 5 Block x 1hr - วันเดียวกัน]) e1@--> B[Avails API Query]
    B e2@--> C[C มี 5 + D มี 5 = 10 slots locked]
    C e3@--> D[เหลือ 6 slots ว่างจาก 16]
    D e4@--> E{Auto-suggest 5 จาก 6}
    E e5@--> F[Suggest: 06-00, 11-00, 13-00, 18-00, 20-00]
    F e6@--> G{E เลือก}
    G e7@-->|จอง 5 slots ที่ suggest| H[Lock 5 slots วันนี้]
    G e8@-->|ต้องการมากกว่า 6| I{slots ไม่เพียงพอ}
    I e9@-->|Partial + วันอื่น| J[Lock N วันนี้ + query วันถัดไป]
    I e10@-->|ทั้งหมดวันอื่น| K[Avails API query วันอื่น]
    I e11@-->|Waitlist| L[Queue - แจ้งเมื่อมี cancellation]
    H e12@--> M([Booking สำเร็จ 5 slots])
    J e13@--> N([Partial booking + follow-up])
    K e14@--> O([Booking เต็ม วันอื่น])
    L e15@--> P([Waitlist active])
    e1@{ animation: slow }
    e2@{ animation: slow }
    e3@{ animation: fast }
    e4@{ animation: fast }
    e5@{ animation: fast }
    e6@{ animation: slow }
    e7@{ animation: fast }
    e8@{ animation: slow }
    e9@{ animation: slow }
    e10@{ animation: slow }
    e11@{ animation: slow }
    e12@{ animation: fast }
    e13@{ animation: fast }
    e14@{ animation: slow }
    e15@{ animation: fast }
    style M fill:#d4edda,stroke:#28a745
    style I fill:#fff3cd,stroke:#ffc107
    style E fill:#cce5ff,stroke:#004085""", page_id))

    # ──────────────────────────────────────────────────────────────
    # SECTION 8: Summary
    # ──────────────────────────────────────────────────────────────
    sections.append('<h2>8. สรุปเปรียบเทียบ 5 รูปแบบ</h2>')
    sections.append("""<table>
<tr>
  <th>รูปแบบ</th>
  <th>เหมาะกับ</th>
  <th>จองล่วงหน้า</th>
  <th>ถ้าช่วงเวลาชน</th>
  <th>การรับประกัน</th>
</tr>
<tr>
  <td><strong>Takeover</strong></td>
  <td>Brand campaign, Event tie-in</td>
  <td>&ge;5 นาที (แนะนำ &ge;1 ชั่วโมง)</td>
  <td>Reject ทันที &mdash; ต้องเลือกเวลาใหม่</td>
  <td>100% ของ slot ที่ซื้อ</td>
</tr>
<tr>
  <td><strong>Exact Time</strong></td>
  <td>Flash Sale, Live Event</td>
  <td>&ge;5 นาที</td>
  <td>Reject ทันที &mdash; ต้องเลือกเวลาใหม่</td>
  <td>เล่นตรงเวลา &plusmn;30s (make-good ถ้า miss)</td>
</tr>
<tr>
  <td><strong>Guaranteed</strong></td>
  <td>Brand recall, Consistent presence</td>
  <td>ก่อนวันเริ่ม campaign</td>
  <td>ไม่มี conflict &mdash; แต่ถ้า Takeover เข้าขัด จะได้ make-good</td>
  <td>N plays ต่อ 15 นาที / ชั่วโมง / วัน</td>
</tr>
<tr>
  <td><strong>Daypart Targeting</strong></td>
  <td>Peak hour brand recall, Time-sensitive product</td>
  <td>ก่อนวันเริ่ม campaign</td>
  <td>ไม่มี conflict &mdash; แต่ถ้า Takeover เข้าขัด จะได้ make-good 3 ระดับ</td>
  <td>N plays ภายใน time window ที่กำหนด</td>
</tr>
<tr>
  <td><strong>Run of Schedule</strong></td>
  <td>Awareness, งบประมาณยืดหยุ่น</td>
  <td>ก่อนวันเริ่ม campaign</td>
  <td>ไม่มี conflict &mdash; แชร์ pool กับโฆษณาอื่น</td>
  <td>Fair share ของ available slots</td>
</tr>
</table>""")

    sections.append(warning_panel(
        "<p><strong>สิ่งสำคัญที่ต้องรู้ก่อนลงโฆษณา</strong></p>"
        "<ul>"
        "<li><strong>Takeover / Exact Time:</strong> "
        "เจ้าของป้ายต้องอนุมัติ creative ก่อนถึงเวลาเล่น &mdash; "
        "ถ้า creative ยังไม่ผ่าน review ถึงเวลา Takeover จะหายไปเลยโดยไม่ได้เล่น</li>"
        "<li><strong>การอนุมัติใช้เวลา:</strong> "
        "แม้ระบบบังคับ lead time แค่ 5 นาที แต่ในทางปฏิบัติควรส่งล่วงหน้า "
        "<strong>อย่างน้อย 1 ชั่วโมง</strong> เพื่อให้เจ้าของป้ายมีเวลาตรวจสอบ</li>"
        "<li><strong>Creative spec:</strong> "
        "ขนาดและ format ต้องตรงกับที่ป้ายรองรับ &mdash; ถ้าไม่ตรง เจ้าของป้ายจะปฏิเสธ</li>"
        "<li><strong>การนับ PoP:</strong> "
        "โฆษณาต้องเล่นจบครบทั้งชิ้นจึงจะนับเป็น 1 play &mdash; "
        "ถ้าถูก interrupt ก่อนจบ ไม่นับ และระบบจะสร้าง make-good ให้อัตโนมัติ</li>"
        "<li><strong>ป้ายออฟไลน์:</strong> "
        "ถ้าป้ายออฟไลน์นาน &gt;4 ชั่วโมง อาจเล่น house filler แทน campaign &mdash; "
        "PoP จะ sync ขึ้นระบบเมื่อป้ายกลับมา online</li>"
        "</ul>"
    ))

    return "\n".join(sections)

SECTION_BUILDERS = {
    "parent": ("parent", build_parent_content),
    "1": ("1_problem_current", build_page_1),
    "2": ("2_proposed", build_page_2),
    "3": ("3_key_flows", build_page_3),
    "4": ("4_tech_algorithm", build_page_4),
    "5": ("5_tech_player", build_page_5),
    "6": ("6_interrupt_makegood", build_page_6),
    "7": ("7_events", build_page_7),
    "8": ("8_edge_migration", build_page_8),
    "9": ("9_es_big_picture", build_page_9),
    "10": ("10_es_process", build_page_10),
    "11": ("11_es_design", build_page_11),
    "12": ("12_usecase_distribution", build_page_12),
    "13": ("13_usecase_industry", build_page_13),
    "14": ("14_usecase_catalog", build_page_14),
}


def _get_api():
    creds = load_credentials()
    return ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(
            creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]
        ),
        ssl_context=create_ssl_context(),
    )


def _update_page(api, page_id: str, content: str, title: str | None = None):
    page = api.get_page(page_id)
    version = page["version"]["number"]
    t = title or page["title"]
    api.update_page(page_id=page_id, title=t, content=content, version=version)
    new_ver = version + 1
    print(f"  Updated: {t} (v{version} -> v{new_ver})")
    print(f"  URL: https://100-stars.atlassian.net/wiki/spaces/{SPACE_KEY}/pages/{page_id}")
    # Fix Confluence ADF panel bug: storage→ADF conversion sometimes creates
    # bodiedExtension instead of native panel for success/error/warning macros.
    # This causes "Error loading the extension!" in view mode.
    fixed = _fix_page_panels(api, page_id, t, new_ver)
    if fixed:
        print(f"  Fixed {fixed} ADF panel(s) (bodiedExtension → native panel)")


# Panel macro keys that Confluence should render as native ADF panels
_PANEL_TYPES = {"info", "note", "warning", "error", "success", "tip"}


def _fix_page_panels(api, page_id: str, title: str, current_ver: int) -> int:
    """Fix Confluence bug: bodiedExtension with panel-type key → native panel.

    Returns number of nodes fixed (0 if no fix needed).
    """
    # Fetch ADF via v2 API
    v2_data = api._request("GET", f"/api/v2/pages/{page_id}?body-format=atlas_doc_format")
    adf = json.loads(v2_data["body"]["atlas_doc_format"]["value"])
    ver = v2_data["version"]["number"]

    fixed_count = 0

    def fix_node(node):
        nonlocal fixed_count
        if not isinstance(node, dict):
            return node
        if (
            node.get("type") == "bodiedExtension"
            and node.get("attrs", {}).get("extensionKey", "") in _PANEL_TYPES
            and "macro.core" in node.get("attrs", {}).get("extensionType", "")
        ):
            fixed_count += 1
            return {
                "type": "panel",
                "attrs": {"panelType": node["attrs"]["extensionKey"]},
                "content": [fix_node(c) for c in node.get("content", [])],
            }
        if "content" in node and isinstance(node["content"], list):
            node["content"] = [fix_node(c) for c in node["content"]]
        return node

    adf = fix_node(adf)

    if fixed_count == 0:
        return 0

    # Update via v2 API with fixed ADF
    api._request(
        "PUT",
        f"/api/v2/pages/{page_id}",
        data={
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "atlas_doc_format",
                "value": json.dumps(adf),
            },
            "version": {"number": ver + 1},
        },
    )
    return fixed_count


def main():
    dry_run = "--dry-run" in sys.argv
    create_all = "--create-all" in sys.argv

    # Parse --section N
    section = None
    if "--section" in sys.argv:
        idx = sys.argv.index("--section")
        if idx + 1 < len(sys.argv):
            section = sys.argv[idx + 1]
        else:
            print("Error: --section requires argument (parent, 1-13)")
            sys.exit(1)

    # Parse --update PAGE_ID (legacy)
    update_page_id = None
    if "--update" in sys.argv:
        idx = sys.argv.index("--update")
        if idx + 1 < len(sys.argv):
            update_page_id = sys.argv[idx + 1]

    page_ids = load_page_ids()
    parent_id = page_ids["parent"]

    # ── Dry-run single section ──
    if dry_run and section:
        if section not in SECTION_BUILDERS:
            print(f"Error: unknown section '{section}'. Valid: {list(SECTION_BUILDERS.keys())}")
            sys.exit(1)
        key, builder = SECTION_BUILDERS[section]
        pid = parent_id if section == "parent" else (page_ids["pages"].get(key) or "DRAFT")
        content = builder(page_id=pid)
        out = Path(__file__).parent.parent / "tasks" / f"arch-page-{section}-preview.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"  DRY RUN section {section} — {out}")
        print(f"  Content length: {len(content)} chars, code blocks: {_code_block_count}")
        return

    # ── Dry-run all sections ──
    if dry_run and not section:
        out_dir = Path(__file__).parent.parent / "tasks"
        out_dir.mkdir(exist_ok=True)
        for sec, (key, builder) in SECTION_BUILDERS.items():
            pid = parent_id if sec == "parent" else (page_ids["pages"].get(key) or "DRAFT")
            content = builder(page_id=pid)
            out = out_dir / f"arch-page-{sec}-preview.html"
            out.write_text(content, encoding="utf-8")
            print(f"  [{sec:>6}] {len(content):>6} chars, {_code_block_count} code blocks → {out.name}")
        return

    api = _get_api()

    # ── Create all sub-pages ──
    if create_all:
        # Update parent first
        print("=== Updating parent page ===")
        content = build_parent_content(page_id=parent_id)
        _update_page(api, parent_id, content)

        # Create sub-pages
        for sec in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]:
            key, builder = SECTION_BUILDERS[sec]
            title = SUB_PAGE_TITLES[key]
            existing_id = page_ids["pages"].get(key)

            if existing_id:
                print(f"\n=== Updating sub-page {sec}: {title} ===")
                content = builder(page_id=existing_id)
                _update_page(api, existing_id, content, title)
            else:
                print(f"\n=== Creating sub-page {sec}: {title} ===")
                # Create with placeholder, then update with real content
                result = api.create_page(
                    space_key=SPACE_KEY,
                    title=title,
                    content="<p>Loading...</p>",
                    parent_id=parent_id,
                )
                new_id = result.get("id", "unknown")
                page_ids["pages"][key] = new_id
                save_page_ids(page_ids)
                print(f"  Created: {new_id}")

                # Now update with real content (needs page_id for Forge macros)
                content = builder(page_id=new_id)
                _update_page(api, new_id, content, title)

        print(f"\n=== Done! Page IDs saved to {PAGE_IDS_FILE} ===")
        return

    # ── Update single section ──
    if section:
        if section not in SECTION_BUILDERS:
            print(f"Error: unknown section '{section}'. Valid: {list(SECTION_BUILDERS.keys())}")
            sys.exit(1)
        key, builder = SECTION_BUILDERS[section]
        if section == "parent":
            pid = parent_id
        else:
            pid = page_ids["pages"].get(key)
            if not pid:
                # Create new sub-page (page ID is null)
                title = SUB_PAGE_TITLES[key]
                print(f"=== Creating section {section}: {title} ===")
                result = api.create_page(
                    space_key=SPACE_KEY,
                    title=title,
                    content="<p>Loading...</p>",
                    parent_id=parent_id,
                )
                pid = result.get("id", "unknown")
                page_ids["pages"][key] = pid
                save_page_ids(page_ids)
                print(f"  Created: {pid}")
        content = builder(page_id=pid)
        title = SUB_PAGE_TITLES.get(key)
        print(f"=== Updating section {section} ===")
        _update_page(api, pid, content, title)
        return

    # ── Legacy: update specific page ──
    if update_page_id:
        content = build_parent_content(page_id=update_page_id)
        print(f"=== Updating page {update_page_id} ===")
        _update_page(api, update_page_id, content)
        return

    print("Usage:")
    print("  --dry-run [--section N]     Preview HTML output")
    print("  --create-all                Create/update parent + all sub-pages")
    print("  --section N                 Update single section (parent, 1-13)")
    print("  --update PAGE_ID            Legacy: update specific page")


if __name__ == "__main__":
    main()
