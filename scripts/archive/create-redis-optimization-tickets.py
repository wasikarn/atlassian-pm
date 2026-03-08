#!/usr/bin/env python3
"""Batch create 10 Redis optimization tickets + Confluence doc.

Creates Task tickets for Redis data type opportunities found in tathep-platform-api.
Each ticket gets: ADF description, story points, "Relates" link to BEP-3302.
Then creates a Confluence doc summarizing all 14 tickets (4 existing + 10 new).

Usage:
    python3 scripts/create-redis-optimization-tickets.py [--dry-run]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts"))
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

# --- ADF helpers ---
def bold(text):
    return {"type": "text", "text": text, "marks": [{"type": "strong"}]}

def plain(text):
    return {"type": "text", "text": text}

def code(text):
    return {"type": "text", "text": text, "marks": [{"type": "code"}]}

def link(text, href):
    return {"type": "text", "text": text, "marks": [{"type": "link", "attrs": {"href": href}}]}

def para(*parts):
    return {"type": "paragraph", "content": list(parts)}

def panel(panel_type, paragraphs):
    return {"type": "panel", "content": paragraphs, "attrs": {"panelType": panel_type}}

def heading(level, text):
    return {"type": "heading", "attrs": {"level": level}, "content": [plain(text)]}

def rule():
    return {"type": "rule"}

def bullet_list(items):
    return {"type": "bulletList", "content": [
        {"type": "listItem", "content": [para(*item) if isinstance(item, list) else para(item)]}
        for item in items
    ]}

def table(headers, rows, header_bg="#fffae6"):
    header_row = {"type": "tableRow", "content": [
        {"type": "tableHeader", "attrs": {"background": header_bg}, "content": [para(plain(h))]}
        for h in headers
    ]}
    data_rows = []
    for row in rows:
        data_rows.append({"type": "tableRow", "content": [
            {"type": "tableCell", "attrs": {}, "content": [para(*cell) if isinstance(cell, list) else para(cell)]}
            for cell in row
        ]})
    return {"type": "table", "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
            "content": [header_row] + data_rows}

def ac_panel(title, given, when, then, panel_type="success"):
    return panel(panel_type, [
        para(bold(title)),
        para(bold("Given: "), *([given] if isinstance(given, dict) else given)),
        para(bold("When: "), *([when] if isinstance(when, dict) else when)),
        para(bold("Then: "), *([then] if isinstance(then, dict) else then)),
    ])

def ref_table(refs):
    return table(["Type", "Link"], refs, "#eae6ff")

PATTERN_GUIDE_LINK = "https://100-stars.atlassian.net/wiki/spaces/BEP/pages/164167729"
ADR_LINK = "https://100-stars.atlassian.net/wiki/spaces/BEP/pages/164167695"
BEP_3302_LINK = "https://100-stars.atlassian.net/browse/BEP-3302"

# ============================================================
# TICKET DEFINITIONS
# ============================================================

TICKETS = [
    # --- #1: KEYS → SCAN (P0 bug fix) ---
    {
        "summary": "[BE] Fix CacheService KEYS Command — Replace with SCAN (Production Redis Blocking)",
        "sp": 1,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(code("CacheService.deleteByPrefix()"), plain(" ใช้ "), code("redis.keys(prefix*)"),
                         plain(" ซึ่งเป็น "), bold("O(N) blocking command"), plain(" — scan ทุก key ใน Redis และ block event loop ระหว่างรัน ทุก client ต้องรอจนเสร็จ"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("error", [
                    para(bold("KEYS Command Blocks Redis Event Loop")),
                    para(bold("File: "), code("app/Services/CacheService.ts"), plain(" (line 151)")),
                    para(code("redis.keys(`${prefix}*`)"), plain(" ถูกเรียกจาก "), code("SaveQuestionnaireResponseUseCase"), plain(" (line 262) ทุกครั้งที่ user submit questionnaire")),
                    para(bold("Impact: "), plain("ถ้า Redis มี key จำนวนมาก → ทุก Redis operation (cache, rate limit, queue) หยุดรอจน KEYS เสร็จ")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    para(bold("Option A: SCAN cursor (drop-in replacement):")),
                    bullet_list([
                        [plain("เปลี่ยน "), code("redis.keys(prefix*)"), plain(" เป็น "), code("redis.scanStream({match: prefix*, count: 100})")],
                        [plain("Non-blocking — scan ทีละ batch, ไม่ block event loop")],
                    ]),
                    para(bold("Option B: Hash-based cache (better long-term):")),
                    bullet_list([
                        [plain("เก็บ questionnaire data ใน "), code("HSET questionnaire:{code} field value")],
                        [plain("ลบทั้ง key ด้วย "), code("DEL questionnaire:{code}"), plain(" — O(1) แทน pattern match")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Services/CacheService.ts")], [plain("เปลี่ยน "), code("deleteByPrefix()"), plain(" จาก KEYS เป็น SCAN")]],
                    [[code("tests/unit/.../savequestionnaireresponseusecase-spec.ts")], [plain("อัปเดต test stub")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Non-blocking Delete — ไม่ block Redis",
                    plain("Redis มี 100,000+ keys"),
                    [code("deleteByPrefix()"), plain(" ถูกเรียก")],
                    plain("ใช้ SCAN cursor แทน KEYS — ไม่ block event loop, ทุก client ยังทำงานได้ปกติ")),
                ac_panel("AC2: Backward Compatible — ลบ key ครบเหมือนเดิม",
                    [plain("มี 50 keys ที่ match prefix "), code("questionnaire::questions::ABC*")],
                    [code("deleteByPrefix('questionnaire::questions::ABC')"), plain(" ถูกเรียก")],
                    plain("ลบครบทั้ง 50 keys เหมือน KEYS command เดิม")),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("SCAN command", "https://redis.io/docs/latest/commands/scan/")]],
                    [[plain("Related")], [link("BEP-3302", BEP_3302_LINK), plain(" — Bentocache Migration")]],
                ]),
            ]
        }
    },
    # --- #2: Notification Unread Cache (Hash) ---
    {
        "summary": "[BE] Cache Notification Unread Count with Redis Hash (HINCRBY)",
        "sp": 3,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("ทุกครั้งที่มี notification event → "), code("NotificationUserUnreadCalculation"), plain(" job รัน "),
                         bold("5 DB queries per user"), plain(" (subscriptions → visibility → notifications → read records → reader info) แล้ว count ใน memory → write DB → push via Pusher"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("error", [
                    para(bold("5 DB Queries + In-Memory Filter Per User Per Event")),
                    para(bold("File: "), code("app/Services/NotificationUserUnreadService.ts")),
                    para(bold("Job: "), code("app/Jobs/NotificationUserUnreadCalculation.ts")),
                    para(plain("Flow: query subscriptions → query visibility → query notifications → query read records → query reader info → filter in memory → updateOrCreate DB → Pusher push")),
                    para(bold("Impact: "), plain("N users × 5 queries per notification batch — scales badly")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    para(bold("Redis Hash per user — atomic increment/decrement:")),
                    bullet_list([
                        [bold("Key: "), code("notification:unread:{userCode}")],
                        [bold("Fields: "), plain("channel names (subscription categories)")],
                        [bold("Write: "), code("HINCRBY notification:unread:{userCode} {channel} 1"), plain(" เมื่อมี notification ใหม่")],
                        [bold("Read: "), code("HGETALL notification:unread:{userCode}"), plain(" → sum values = total unread")],
                        [bold("Mark read: "), code("HINCRBY ... -1"), plain(" หรือ "), code("HDEL"), plain(" ถ้า channel count = 0")],
                        [bold("TTL: "), plain("ไม่ต้อง — invalidate เมื่อ user reads all")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Services/NotificationUserUnreadService.ts")], [plain("เพิ่ม Redis Hash increment/decrement")]],
                    [[code("app/Jobs/NotificationUserUnreadCalculation.ts")], [plain("ใช้ Redis Hash แทน 5 DB queries")]],
                    [[code("app/UseCases/Public/V2/Notification/GetNotificationUserUnread.ts")], [plain("อ่านจาก Redis Hash (fallback DB)")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม key registry")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Atomic Increment — notification ใหม่ increment ทันที",
                    plain("User มี unread count = 5"),
                    plain("Notification ใหม่เข้ามา"),
                    [code("HINCRBY"), plain(" เพิ่ม count เป็น 6, Pusher push ค่าใหม่ทันที")]),
                ac_panel("AC2: Mark Read — decrement เมื่อ user อ่าน",
                    plain("User มี unread = 6"),
                    plain("User อ่าน notification 1 รายการ"),
                    [code("HINCRBY ... -1"), plain(" ลด count เป็น 5")]),
                ac_panel("AC3: Fallback — Redis miss ใช้ DB",
                    plain("Redis key หายไป"),
                    plain("API ขอ unread count"),
                    plain("Fallback query DB (existing logic) + rebuild Redis Hash"),
                    "warning"),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Hash commands", "https://redis.io/docs/latest/develop/data-types/hashes/")]],
                    [[plain("Related")], [link("BEP-3302", BEP_3302_LINK), plain(" — Bentocache Migration")]],
                ]),
            ]
        }
    },
    # --- #3: Multi-Session Management (Set) ---
    {
        "summary": "[BE] Implement Multi-Session Management with Redis Set (SADD/SREM)",
        "sp": 2,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("Key "), code("auth::sessions::{userId}"), plain(" ถูก spec ไว้ใน "), code("app/Constants/Redis.ts"), plain(" (line 227-240) เป็น Redis Set แต่"),
                         bold(" ยังไม่มี code implement จริง"), plain(" — ทำให้ 'Logout All Devices' feature ยังไม่ทำงาน"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("error", [
                    para(bold("Spec-Only — No Implementation")),
                    para(bold("File: "), code("app/Constants/Redis.ts"), plain(" (lines 227-240)")),
                    para(plain("มี key pattern + SADD/SMEMBERS/SREM comments แต่ไม่มี code ที่เรียกจริง — user ไม่สามารถ logout all devices หรือดู active sessions ได้")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Login: "), code("SADD auth:sessions:{userId} {sessionId}")],
                        [bold("Logout: "), code("SREM auth:sessions:{userId} {sessionId}")],
                        [bold("List sessions: "), code("SMEMBERS auth:sessions:{userId}")],
                        [bold("Logout all: "), code("DEL auth:sessions:{userId}"), plain(" + invalidate all tokens")],
                        [bold("TTL: "), plain("EXPIRE 45 days (match token TTL)")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Constants/Redis.ts")], [plain("Key pattern already defined — no change")]],
                    [[code("app/Modules/Auth/*")], [plain("เพิ่ม SADD on login, SREM on logout")]],
                    [[code("API endpoint")], [plain("เพิ่ม GET /auth/sessions, DELETE /auth/sessions")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Track Sessions — login เพิ่ม session ใน Set",
                    plain("User login จาก device ใหม่"),
                    plain("Auth token ถูกสร้าง"),
                    [code("SADD"), plain(" บันทึก sessionId ใน user's session set")]),
                ac_panel("AC2: Logout All — ลบ sessions ทั้งหมดได้",
                    plain("User มี 3 active sessions"),
                    plain("เรียก DELETE /auth/sessions"),
                    plain("ทุก session ถูกลบ + tokens invalidated")),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Set commands", "https://redis.io/docs/latest/develop/data-types/sets/")]],
                ]),
            ]
        }
    },
    # --- #4: Billboard Proximity (Geo) ---
    {
        "summary": "[BE] Add Billboard Proximity Search with Redis Geo (GEOADD/GEOSEARCH)",
        "sp": 3,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("Billboard location data (lat/lng) อยู่ใน MySQL — proximity queries ใช้ SQL "), code("GROUP BY"),
                         plain(" + "), code("COUNT"), plain(" ใน background jobs ("), code("BillboardMatchingIndexStep2"), plain(") ไม่มี real-time proximity API"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("error", [
                    para(bold("No Real-Time Proximity Query")),
                    para(bold("File: "), code("app/Jobs/BillboardPlaceGetAnalytic.ts"), plain(" → fan-out "), code("BillboardPlaceGetAnalyticDetail")),
                    para(bold("Model: "), code("app/Models/BillboardAnalyticPlace.ts")),
                    para(plain("'หาป้ายใกล้พิกัดนี้ 5 กม.' ต้องรอ background job — ไม่สามารถตอบ real-time ได้")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Index: "), code("GEOADD billboards:{city} {lng} {lat} {billboardCode}")],
                        [bold("Query: "), code("GEOSEARCH billboards:{city} FROMLONLAT {lng} {lat} BYRADIUS 5 km ASC COUNT 10")],
                        [bold("Distance: "), code("GEODIST billboards:{city} BRD-001 BRD-002 km")],
                        [bold("Sync: "), plain("Rebuild geo index เมื่อ billboard ถูกสร้าง/ย้าย/ลบ")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Services/ (new)")], [plain("BillboardGeoService — GEOADD/GEOSEARCH wrapper")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม geo key registry")]],
                    [[code("API endpoint")], [plain("GET /billboards/nearby?lat=&lng=&radius=")]],
                    [[code("app/Jobs/")], [plain("Sync job: rebuild geo index from DB")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Proximity Search — หาป้ายใกล้พิกัด",
                    plain("มี 100 billboards ใน geo index"),
                    [plain("Query: "), code("GEOSEARCH ... BYRADIUS 5 km")],
                    plain("Return billboards ภายใน 5 กม. เรียงตามระยะทาง, response < 10ms")),
                ac_panel("AC2: Auto-Sync — billboard ใหม่เข้า geo index อัตโนมัติ",
                    plain("Billboard ใหม่ถูกสร้างใน DB"),
                    plain("Billboard create event fired"),
                    [code("GEOADD"), plain(" เพิ่ม billboard ใน geo index ทันที")]),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Geospatial", "https://redis.io/docs/latest/develop/data-types/geospatial/")]],
                ]),
            ]
        }
    },
    # --- #5: Unique View Counting (HyperLogLog) ---
    {
        "summary": "[BE] Add Real-Time Unique View Counting with Redis HyperLogLog (PFADD/PFCOUNT)",
        "sp": 2,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("Unique impression counting ปัจจุบันรอ daily aggregate job ("), code("PlayHistoryDailyAnalyticCalculate"),
                         plain(") — ไม่มี real-time unique count ระหว่างวัน. HyperLogLog ใช้แค่ 12 KB per counter ไม่ว่าจะมีกี่ unique viewers"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("warning", [
                    para(bold("No Real-Time Unique Count")),
                    para(bold("Jobs: "), code("PlayHistoryDailyAnalyticCalculate"), plain(", "), code("AdvertisementDailyAnalyticCalculate")),
                    para(plain("Daily jobs aggregate unique counts จาก DB — ระหว่างวันไม่มีข้อมูล real-time. Admin ต้องรอ job รันเสร็จถึงจะเห็นตัวเลข")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Write: "), code("PFADD views:billboard:{code}:{date} {viewerFingerprint}")],
                        [bold("Read: "), code("PFCOUNT views:billboard:{code}:{date}"), plain(" → approximate unique count")],
                        [bold("Merge: "), code("PFMERGE views:billboard:{code}:week views:billboard:{code}:mon ... :sun")],
                        [bold("Memory: "), plain("12 KB per counter ไม่ว่าจะมีกี่ unique")],
                        [bold("Error rate: "), plain("~0.81% — ยอมรับได้สำหรับ analytics dashboard")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Jobs/PlayHistoryGetAnalytic.ts")], [plain("เพิ่ม PFADD เมื่อ play event เข้ามา")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม HyperLogLog key registry")]],
                    [[code("API endpoint")], [plain("GET /analytics/billboard/{code}/unique-views?date=")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Real-Time Unique Count — ไม่ต้องรอ daily job",
                    plain("Billboard BRD-001 มี 500 unique viewers วันนี้"),
                    [code("PFCOUNT views:billboard:BRD-001:2026-02-20")],
                    plain("Return ~500 (±0.81%) ทันที, ไม่ต้องรอ daily aggregate job")),
                ac_panel("AC2: Memory Efficient — 12 KB per counter",
                    plain("มี 200 billboards × 365 วัน"),
                    plain("ตรวจสอบ memory usage"),
                    plain("ใช้ ~876 KB total (200 × 365 × 12 KB / 1024) — ไม่กระทบ Redis memory")),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("HyperLogLog", "https://redis.io/docs/latest/develop/data-types/probabilistic/hyperloglogs/")]],
                ]),
            ]
        }
    },
    # --- #6: Pusher Log Buffering (List) ---
    {
        "summary": "[BE] Buffer Pusher Event Logs with Redis List (LPUSH + Batch Flush)",
        "sp": 2,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("ทุก Pusher event → synchronous DB write to "), code("pusher_logs"), plain(" table — อยู่ใน hot path ของ real-time notification system"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("warning", [
                    para(bold("Synchronous DB Write in Hot Path")),
                    para(bold("File: "), code("app/Services/PusherService.ts"), plain(" (lines 43-82)")),
                    para(plain("ทุกครั้งที่ trigger Pusher event → INSERT INTO pusher_logs ทันที — ถ้า Pusher trigger 100 events/sec → 100 DB writes/sec เฉพาะ logging")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Buffer: "), code("LPUSH pusher:logs {JSON.stringify(logEntry)}")],
                        [bold("Flush: "), plain("Background job ทุก 30s: "), code("LRANGE pusher:logs 0 99"), plain(" → batch INSERT → "), code("LTRIM pusher:logs 100 -1")],
                        [bold("Fallback: "), plain("ถ้า Redis unavailable → synchronous DB write เดิม")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Services/PusherService.ts")], [plain("เปลี่ยน DB write เป็น LPUSH")]],
                    [[code("app/Jobs/ (new)")], [plain("PusherLogFlushJob — batch flush ทุก 30s")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม key registry")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Buffer — ไม่ write DB ทันที",
                    plain("Pusher trigger 100 events ใน 1 วินาที"),
                    plain("PusherService.trigger() ถูกเรียก"),
                    [plain("LPUSH ทั้ง 100 entries ใน Redis List, DB writes = 0 (buffered)")]),
                ac_panel("AC2: Batch Flush — ลด DB writes 90%+",
                    plain("Redis List มี 100 buffered logs"),
                    plain("PusherLogFlushJob รัน"),
                    plain("Batch INSERT 100 rows ใน 1 DB call → LTRIM ลบ buffered entries")),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("List commands", "https://redis.io/docs/latest/develop/data-types/lists/")]],
                ]),
            ]
        }
    },
    # --- #7: Event-Driven Outbox (Pub/Sub) ---
    {
        "summary": "[BE] Replace Outbox Polling with Redis Pub/Sub Trigger",
        "sp": 2,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(code("OutboxPollingPublisher"), plain(" poll DB ทุก 5 วินาที "), code("WHERE status = 'pending'"),
                         plain(" — latency 0-5s, waste queries เมื่อไม่มี events"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("warning", [
                    para(bold("DB Polling Every 5 Seconds")),
                    para(bold("File: "), code("app/Modules/TransactionalMessaging/Jobs/OutboxPollingPublisher.ts")),
                    para(bold("Config: "), code("TransactionalMessagingConfig.ts"), plain(" — OUTBOX_POLLING_INTERVAL: 5000ms")),
                    para(plain("17,280 queries/day (ทุก 5s × 86,400s/day) แม้ไม่มี pending events")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("After DB insert outbox: "), code("PUBLISH outbox:trigger {messageId}")],
                        [bold("Publisher subscribes: "), code("SUBSCRIBE outbox:trigger"), plain(" → process immediately")],
                        [bold("Safety net: "), plain("ลด polling frequency เป็นทุก 30s (6x less queries)")],
                        [bold("Latency: "), plain("จาก 0-5s → near-zero (Pub/Sub = instant)")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("OutboxPollingPublisher.ts")], [plain("เพิ่ม SUBSCRIBE listener + ลด poll interval เป็น 30s")]],
                    [[code("TransactionalMessagingConfig.ts")], [plain("OUTBOX_POLLING_INTERVAL: 5000 → 30000")]],
                    [[code("Outbox insert code")], [plain("เพิ่ม PUBLISH หลัง DB insert")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Instant Delivery — Pub/Sub trigger ทันที",
                    plain("Outbox event ถูก insert ลง DB"),
                    [code("PUBLISH outbox:trigger"), plain(" ถูกเรียก")],
                    plain("Publisher รับ event ภายใน <100ms (แทน 0-5s)")),
                ac_panel("AC2: Reduced Polling — ลด 6x",
                    plain("ไม่มี pending events"),
                    plain("Polling interval = 30s"),
                    plain("DB queries ลดจาก 17,280/day เหลือ 2,880/day")),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Pub/Sub", "https://redis.io/docs/latest/develop/interact/pubsub/")]],
                ]),
            ]
        }
    },
    # --- #8: DAU Tracking (Bitmap) ---
    {
        "summary": "[BE] Add Daily Active User Tracking with Redis Bitmap (SETBIT/BITCOUNT)",
        "sp": 1,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("ปัจจุบันไม่มี DAU/WAU/MAU tracking ใน platform — ต้อง query DB logs ย้อนหลัง. Redis Bitmap ใช้ ~125 KB per 1M users per day"))
                ]),
                rule(),
                heading(2, "2. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Track: "), code("SETBIT dau:{YYYY-MM-DD} {userId} 1"), plain(" — O(1) per request")],
                        [bold("Count DAU: "), code("BITCOUNT dau:{YYYY-MM-DD}"), plain(" — O(N/8) bits")],
                        [bold("Weekly retention: "), code("BITOP AND dau:week dau:mon ... dau:sun"), plain(" → users active ALL 7 days")],
                        [bold("Memory: "), plain("~125 KB per 1M users per day (bitmap)")],
                        [bold("TTL: "), plain("EXPIRE 90 days")],
                    ]),
                ]),
                rule(),
                heading(2, "3. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Middleware/ (new or existing auth)")], [plain("เพิ่ม SETBIT on authenticated request")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม bitmap key registry")]],
                    [[code("API endpoint")], [plain("GET /analytics/dau?date= (admin only)")]],
                ]),
                rule(),
                heading(2, "4. ✅ Acceptance Criteria"),
                ac_panel("AC1: Track — ทุก authenticated request set bit",
                    plain("User ID 42 ส่ง API request"),
                    plain("Auth middleware verified"),
                    [code("SETBIT dau:2026-02-20 42 1"), plain(" — idempotent, O(1)")]),
                ac_panel("AC2: Count — DAU query ตอบทันที",
                    plain("วันนี้มี 500 unique users"),
                    [code("BITCOUNT dau:2026-02-20")],
                    plain("Return 500 ทันที, ไม่ต้อง query DB")),
                rule(),
                heading(2, "5. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Bitmaps", "https://redis.io/docs/latest/develop/data-types/bitmaps/")]],
                ]),
            ]
        }
    },
    # --- #9: Billboard Metadata Cache (Hash) ---
    {
        "summary": "[BE] Cache Billboard Metadata with Redis Hash (HSET/HGET)",
        "sp": 1,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(code("Billboard.query().where('code', billboardCode).first()"), plain(" ถูกเรียกซ้ำใน loop ของ "),
                         code("PlaySchedulePeriodService.ts"), plain(" (line 568) ทุก 10-15 นาทีต่อ screen — ไม่มี cache"))
                ]),
                rule(),
                heading(2, "2. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Cache: "), code("HSET billboard:{code} name '...' lat 13.7 lng 100.5 status active")],
                        [bold("Read single field: "), code("HGET billboard:{code} status"), plain(" — O(1)")],
                        [bold("Read all: "), code("HGETALL billboard:{code}"), plain(" — O(N) fields")],
                        [bold("Invalidate: "), code("DEL billboard:{code}"), plain(" เมื่อ billboard ถูก update")],
                        [bold("TTL: "), plain("1 hour — billboard metadata เปลี่ยนไม่บ่อย")],
                    ]),
                ]),
                rule(),
                heading(2, "3. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Services/PlaySchedulePeriodService.ts")], [plain("เปลี่ยน DB query เป็น HGETALL + fallback")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม billboard hash key registry")]],
                ]),
                rule(),
                heading(2, "4. ✅ Acceptance Criteria"),
                ac_panel("AC1: Cache Hit — ไม่ query DB",
                    plain("Billboard BRD-001 อยู่ใน Redis Hash"),
                    [code("HGETALL billboard:BRD-001")],
                    plain("Return metadata ทันที, ไม่ query DB")),
                ac_panel("AC2: Cache Miss — fallback DB + populate",
                    plain("Billboard BRD-002 ไม่อยู่ใน Redis"),
                    [code("HGETALL billboard:BRD-002"), plain(" return empty")],
                    plain("Query DB → HSET populate → return data")),
                rule(),
                heading(2, "5. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Hash commands", "https://redis.io/docs/latest/develop/data-types/hashes/")]],
                    [[plain("Related")], [link("BEP-3315", "https://100-stars.atlassian.net/browse/BEP-3315"), plain(" — PlaySchedule ZCOUNT (same service)")]],
                ]),
            ]
        }
    },
    # --- #10: Analytics Accumulation (Hash) ---
    {
        "summary": "[BE] Accumulate Daily Analytics in Redis Hash (HINCRBY + Daily Flush)",
        "sp": 3,
        "description": {
            "type": "doc", "version": 1,
            "content": [
                heading(2, "1. 📋 Context"),
                panel("info", [
                    para(plain("Daily analytics jobs ("), code("PlayHistoryDailyAnalyticCalculate"), plain(", "), code("AdvertisementDailyAnalyticCalculate"),
                         plain(") fan-out Bull jobs per screen/ad แล้ว aggregate จาก DB — ใช้ Redis Hash สะสม metrics ระหว่างวันแล้ว flush ทีเดียว"))
                ]),
                rule(),
                heading(2, "2. 🔴 Problem"),
                panel("warning", [
                    para(bold("Fan-Out Jobs + DB Aggregate Per Entity")),
                    para(bold("Jobs: "), code("PlayHistoryDailyAnalyticCalculate"), plain(" → "), code("PlayHistoryDailyAnalyticCalculateDetail")),
                    para(plain("ทุก daily job → fan-out per screen/ad → query DB per entity → update analytic table. 200 billboards × 10 ads = 2,000 DB queries per daily run")),
                ]),
                rule(),
                heading(2, "3. 🔧 Solution"),
                panel("success", [
                    bullet_list([
                        [bold("Accumulate: "), code("HINCRBY analytics:billboard:{code}:{date} impressions 1")],
                        [bold("Multi-field: "), code("HINCRBY analytics:billboard:{code}:{date} clicks 1")],
                        [bold("Flush: "), plain("Daily job → "), code("HGETALL"), plain(" each key → batch upsert DB → "), code("DEL"), plain(" Redis keys")],
                        [bold("TTL: "), plain("2 days safety net (ถ้า flush job ไม่รัน)")],
                    ]),
                ]),
                rule(),
                heading(2, "4. ⚙️ Scope"),
                table(["File", "Change"], [
                    [[code("app/Jobs/PlayHistoryGetAnalytic.ts")], [plain("เพิ่ม HINCRBY เมื่อ play event")]],
                    [[code("app/Jobs/PlayHistoryDailyAnalyticCalculate.ts")], [plain("เปลี่ยนจาก DB aggregate เป็น HGETALL + batch upsert")]],
                    [[code("app/Constants/Redis.ts")], [plain("เพิ่ม analytics hash key registry")]],
                ]),
                rule(),
                heading(2, "5. ✅ Acceptance Criteria"),
                ac_panel("AC1: Real-Time Accumulation — ไม่ต้องรอ daily job",
                    plain("Billboard BRD-001 มี 50 impressions วันนี้"),
                    plain("Play event ใหม่เข้ามา"),
                    [code("HINCRBY"), plain(" เพิ่ม impressions เป็น 51, ดูได้ทันทีจาก Redis")]),
                ac_panel("AC2: Daily Flush — sync to DB efficiently",
                    plain("มี 200 billboard analytics keys ใน Redis"),
                    plain("Daily flush job รัน"),
                    [code("HGETALL"), plain(" + batch upsert 200 rows → "), code("DEL"), plain(" keys, ลด 2,000 queries → 200 HGETALL + 1 batch upsert")]),
                rule(),
                heading(2, "6. 🔗 Reference"),
                ref_table([
                    [[plain("Redis Docs")], [link("Hash commands", "https://redis.io/docs/latest/develop/data-types/hashes/")]],
                ]),
            ]
        }
    },
]


def main():
    dry_run = "--dry-run" in sys.argv

    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    print(f"=== Creating {len(TICKETS)} Redis Optimization Tickets ===")
    if dry_run:
        print("(DRY RUN mode)\n")

    created = []

    for i, ticket in enumerate(TICKETS, 1):
        summary = ticket["summary"]
        sp = ticket["sp"]
        desc = ticket["description"]

        print(f"  [{i}/{len(TICKETS)}] {summary} ({sp} SP)")

        if dry_run:
            created.append({"key": f"BEP-XXXX", "summary": summary, "sp": sp})
            continue

        try:
            result = api.create_issue(
                project_key="BEP",
                issue_type="Task",
                summary=summary,
                additional_fields={
                    "description": desc,
                    "customfield_10016": sp,  # Story Points
                },
            )
            key = result["key"]
            print(f"         → {key}")
            created.append({"key": key, "summary": summary, "sp": sp})
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            print(f"         → ERROR: {e}")
            created.append({"key": "ERROR", "summary": summary, "sp": sp, "error": str(e)})

    print(f"\n=== Created {len([c for c in created if c['key'] != 'ERROR'])} tickets ===\n")

    # Output JSON for next steps
    output_file = Path(__file__).parent / "redis-tickets-created.json"
    with open(output_file, "w") as f:
        json.dump(created, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {output_file}")

    # Print summary
    print("\n| # | Key | Summary | SP |")
    print("|---|-----|---------|-----|")
    for i, t in enumerate(created, 1):
        print(f"| {i} | {t['key']} | {t['summary'][:60]} | {t['sp']} |")


if __name__ == "__main__":
    main()
