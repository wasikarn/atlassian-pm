#!/usr/bin/env python3
"""Create Release Notes 1.32.0 Confluence page under Release Notes parent."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'atlassian-scripts'))

from lib.auth import create_ssl_context, load_credentials, get_auth_header
from lib.api import ConfluenceAPI

PARENT_PAGE_ID = "119799810"   # "Release Notes" parent page
SPACE_KEY = "BEP"
VERSION_ID = "10268"
RELEASE_URL = f"https://100-stars.atlassian.net/projects/BEP/versions/{VERSION_ID}"
TITLE = "Release Notes - Tathep Platform - 1.32.0 - Feb 20"

JIRA_BASE = "https://100-stars.atlassian.net/browse"


def jira_link(key: str) -> str:
    return f'<a href="{JIRA_BASE}/{key}">{key}</a>'


def section(title: str, color: str, items: list[tuple[str, str]]) -> str:
    """Render a section with h2 header and bulleted issue list."""
    rows = "\n".join(
        f'<li>{jira_link(key)} — {desc}</li>' for key, desc in items
    )
    return f"""
<h2><span style="color:{color};">{title}</span></h2>
<ul>
{rows}
</ul>"""


CONTENT = f"""
<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>How to use this page:</strong></p>
    <p>Release notes สำหรับ Sprint 32 (Feb 6–20, 2026) — คลิก issue key เพื่อดูรายละเอียดแต่ละ ticket ใน Jira</p>
  </ac:rich-text-body>
</ac:structured-macro>

<table data-layout="default" data-table-width="1000">
  <colgroup><col style="width:165px"/><col style="width:835px"/></colgroup>
  <tbody>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Release</strong></p></td>
      <td><p><a href="{RELEASE_URL}">{RELEASE_URL}</a></p></td>
    </tr>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Date</strong></p></td>
      <td><p>2026-02-20</p></td>
    </tr>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Version</strong></p></td>
      <td><p>1.32.0</p></td>
    </tr>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Sprint</strong></p></td>
      <td><p>Sprint 32 (Feb 6–20, 2026)</p></td>
    </tr>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Description</strong></p></td>
      <td>
        <p>Release หลักของ Sprint 32 — เปิดตัวระบบคูปอง end-to-end บน Platform:</p>
        <ul>
          <li>หน้าเก็บคูปอง (Collect Coupons) + หน้าคูปองของฉัน (My Coupons)</li>
          <li>รองรับคูปอง 3 ประเภท: เติมเครดิต / ส่วนลด / Cash Back</li>
          <li>ปรับ Navbar และ Menu ตาม Design ใหม่</li>
          <li>Account-Based Billboard Filtering</li>
          <li>เสริมความแข็งแกร่ง: Redlock, Rate Limiting, Daily Cap</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td data-highlight-colour="#F4F5F7"><p><strong>Contributors</strong></p></td>
      <td>
        <p>BIG-TATHEP · K.Thanainun · joakim · wanchalerm · Natthakarn · kanya · Kanthisorn</p>
      </td>
    </tr>
  </tbody>
</table>

<h2>🆕 New Features</h2>

<h3>Coupon System — Platform</h3>
<ul>
  <li>{jira_link("BEP-3288")} — หน้าเก็บคูปอง + ใช้คูปองเติมเครดิต (Collect &amp; Redeem: Top-up Credit)</li>
  <li>{jira_link("BEP-3289")} — หน้าเก็บคูปอง + ใช้คูปองส่วนลด (Collect &amp; Redeem: Discount)</li>
  <li>{jira_link("BEP-3290")} — หน้าเก็บคูปอง + ใช้คูปอง Cash Back (Collect &amp; Redeem: Cashback)</li>
  <li>{jira_link("BEP-3291")} — หน้าคูปองของฉัน (My Coupons)</li>
  <li>{jira_link("BEP-3156")} — [BE] API เก็บคูปอง (Collect Coupon)</li>
  <li>{jira_link("BEP-3157")} — [BE] API คูปองของฉัน (My Coupons)</li>
  <li>{jira_link("BEP-3218")} — [FE-Web] UI หน้าคูปองของฉัน (My Coupons UI)</li>
  <li>{jira_link("BEP-3219")} — [FE-Web] API Integration หน้าเก็บคูปอง</li>
  <li>{jira_link("BEP-3230")} — [BE] Get Coupon Detail by Code API (Public V2)</li>
  <li>{jira_link("BEP-3235")} — [FE-Web] Popup เติมเครดิต — เพิ่มขั้นตอน Collect ก่อน Redeem</li>
</ul>

<h3>Navigation &amp; UI</h3>
<ul>
  <li>{jira_link("BEP-3211")} — [FE-Web] ปรับ Navbar และ Menu ตาม Design ใหม่</li>
</ul>

<h3>Billboard</h3>
<ul>
  <li>{jira_link("BEP-3276")} — กรอง Billboard ตาม Account Visibility (Account-Based Billboard Filtering)</li>
</ul>

<h2>🔒 Security &amp; Stability</h2>
<ul>
  <li>{jira_link("BEP-3164")} — [BE] เพิ่ม Redlock ป้องกัน Race Condition ระบบคูปอง</li>
  <li>{jira_link("BEP-3166")} — [BE] เพิ่ม Rate Limiting สำหรับ API เก็บคูปอง</li>
  <li>{jira_link("BEP-3331")} — [BE] เพิ่ม Global Daily Redemption Cap ป้องกัน Coupon Abuse</li>
</ul>

<h2>🐛 Bug Fixes — Coupon</h2>
<ul>
  <li>{jira_link("BEP-3340")} — คูปองที่ถูกยกเลิกยังแสดงผลในระบบ</li>
  <li>{jira_link("BEP-3339")} — [Admin] คูปองที่ถูกเก็บแล้วไม่ควรกดลบได้</li>
  <li>{jira_link("BEP-3337")} — หน้าใช้คูปองแสดงเฉพาะคูปองเติมเครดิต ไม่แสดงคูปองประเภทอื่น</li>
  <li>{jira_link("BEP-3334")} — คูปองสิทธิเต็ม แต่ระบบขึ้นแจ้งเตือนไม่ถูกต้อง</li>
  <li>{jira_link("BEP-3319")} — Filter ป้ายแสดงคูปองไม่ตรงเงื่อนไขป้าย</li>
  <li>{jira_link("BEP-3318")} — คูปองหมดอายุไม่แสดงรายละเอียดในแท็บ &quot;คูปองของฉัน&quot;</li>
  <li>{jira_link("BEP-3313")} — แถบสถานะ &quot;จำกัดจำนวน&quot; แสดงไม่ตรงกันระหว่างหน้าเก็บคูปองกับหน้าคูปองของฉัน</li>
  <li>{jira_link("BEP-3312")} — กดใช้คูปองแล้ว ขึ้นแจ้งเตือน &quot;ไม่สามารถโหลดคูปองได้&quot;</li>
  <li>{jira_link("BEP-3308")} — คูปองมีเงื่อนไขชำระขั้นต่ำ แต่ไม่แสดง Tooltip</li>
  <li>{jira_link("BEP-3307")} — ตั้งค่าคูปองใช้ได้กับบางป้าย แต่ระบบแสดงป้ายทั้งหมด</li>
  <li>{jira_link("BEP-3304")} — ใช้คูปอง Cashback/ส่วนลด แล้วระบบไม่พาไปหน้าสร้างโฆษณา</li>
  <li>{jira_link("BEP-3303")} — คูปองยังไม่ถึงวันเริ่มใช้งาน แต่แสดงวันหมดอายุแทนวันเริ่มใช้</li>
  <li>{jira_link("BEP-3301")} — Admin ยกเลิก/ลบคูปอง แต่หน้าเก็บคูปองไม่แจ้งเตือน</li>
  <li>{jira_link("BEP-3300")} — คูปองไม่แสดงหน้าเก็บคูปองตามช่วงวันที่ตั้งค่า</li>
  <li>{jira_link("BEP-3299")} — คูปองเติมเครดิต 3 ใบ ใช้ไป 1 ใบ แต่ผู้ใช้คนที่ 2 รับไม่ได้</li>
  <li>{jira_link("BEP-3298")} — หน้า Coupon Detail แสดงข้อมูลเงื่อนไขไม่ครบ</li>
  <li>{jira_link("BEP-3297")} — กดปุ่ม &quot;เก็บ&quot; จากหน้าเงื่อนไข ระบบเด้ง Pop-up เติมเครดิตทันที</li>
  <li>{jira_link("BEP-3295")} — Coupon Detail แสดงข้อมูล &quot;จำกัดการใช้งาน&quot; ผิด (กรณีไม่จำกัด)</li>
  <li>{jira_link("BEP-3294")} — กดรับคูปองเติมเครดิตไม่ได้ ขึ้น &quot;ใช้แล้ว&quot; ทั้งที่ยังไม่ได้รับ</li>
  <li>{jira_link("BEP-3293")} — คูปองยังแสดงใน &quot;คูปองทั้งหมด&quot; ทั้งที่ตั้งวันแสดงผลเป็นวันถัดไป</li>
  <li>{jira_link("BEP-3165")} — [BE] Bug: checkCoupon() นับ maxPerUser ผิด — คูปองใช้ซ้ำไม่ได้</li>
  <li>{jira_link("BEP-3161")} — [FE-Admin] คัดลอกคูปองแล้วแก้ไข กดบันทึกไม่ได้</li>
  <li>{jira_link("BEP-3198")} — [Admin] หน้าสร้างคูปองส่วนลด — เลือก Dropdown ขั้นต่ำถูกต้องแต่ยังแจ้ง error</li>
  <li>{jira_link("BEP-3274")} — [FE-Admin] คูปองที่ปิดการแสดงผลยังขึ้นหน้าเก็บคูปอง</li>
  <li>{jira_link("BEP-3167")} — [FE-Web] อัปเดต Enum คูปอง (สถานะ + ประเภท)</li>
</ul>

<h2>🐛 Bug Fixes — UI</h2>
<ul>
  <li>{jira_link("BEP-3287")} — [FE-Web] Hamburger Menu — กดเลือกเมนูครั้งที่ 2 แล้วเมนูไม่หุบ (Mobile)</li>
  <li>{jira_link("BEP-3286")} — [FE-Web] Navbar Cosmetic fixes</li>
  <li>{jira_link("BEP-3280")} — [FE-Web] หน้าเก็บคูปอง — Cosmetic fixes</li>
  <li>{jira_link("BEP-3311")} — [Platform] หน้าคูปองของฉัน — Cosmetic fixes</li>
  <li>{jira_link("BEP-3309")} — [Platform] หน้าใช้คูปอง Cash Back — Cosmetic fixes</li>
  <li>{jira_link("BEP-3089")} — [FE-Web] Bug: Notification แสดงเครดิตไม่มี comma</li>
</ul>

<h2>🔥 Hotfixes</h2>
<ul>
  <li>{jira_link("BEP-3275")} — Prod./Stg.: อัปโหลดรูป — กดบันทึกซ้ำ Error / เผยแพร่ไม่ Active</li>
  <li>{jira_link("BEP-3270")} — Mobile View: ระบบเชิญเพื่อน — กดปุ่มคัดลอกลิงก์ไม่ทำงาน (iPhone 13)</li>
  <li>{jira_link("BEP-3124")} — [FE-Web] Hotfix: อัปโหลดรูปโฆษณา — ความยาวแสดงผลเป็น 0</li>
</ul>
"""


def main():
    creds = load_credentials()
    api = ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    print(f"Creating: {TITLE}")
    print(f"Parent: {PARENT_PAGE_ID} | Space: {SPACE_KEY}")

    result = api.create_page(
        space_key=SPACE_KEY,
        title=TITLE,
        content=CONTENT,
        parent_id=PARENT_PAGE_ID,
    )

    page_id = result.get("id")
    url = f"https://100-stars.atlassian.net/wiki/spaces/{SPACE_KEY}/pages/{page_id}"
    print(f"\n✓ Created: {url}")
    return url


if __name__ == "__main__":
    main()
