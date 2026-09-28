# Handoff: OPS-17 — seed corpus โจทย์ 100 ข้อบน R2

เขียนเมื่อ 2026-09-28 โดยสรุปจาก session ของพาย ใครจะทำงานฝั่ง ingest, retrieval หรือ generation
ให้อ่านไฟล์นี้กับ `AGENTS.md` ก่อนเริ่ม

ส่วนที่ 1–3 เป็นบริบท ส่วนที่ 4 คือสิ่งที่ Claude Code ต้องแก้ใน repo

---

## 1. ตอนนี้มีอะไรแล้ว

**มี PDF โจทย์ 100 ไฟล์อยู่บน R2 แล้ว (อัปขึ้นไปเมื่อ 2026-09-28)**

| อะไร | ที่ไหน |
|---|---|
| object บน R2 | bucket dev ใน `.env` (`R2_BUCKET_NAME`) ใต้ key `sources/programming-in-th/{task_id}.pdf` |
| รายการโจทย์ + topic/difficulty | `scripts/seed/pith-100-manifest.csv` (100 แถว) |
| สคริปต์อัป | `scripts/seed_pith_to_r2.py` |
| cache PDF ในเครื่อง + ผลการอัป | `data/pith/*.pdf`, `data/pith/uploaded.csv` (มี `sha256`, `size_bytes`) อยู่ใต้ `data/` ซึ่ง gitignore อยู่แล้ว |
| ต้นทาง | `https://programming.in.th/api/tasks/{task_id}/statement` โจทย์ public ไม่ต้อง login |

- object แต่ละไฟล์มี R2 metadata ได้แก่ `task-id`, `topic`, `difficulty`, `sha256` ส่วนชื่อโจทย์ภาษาไทยไม่ได้ใส่ใน metadata เพราะ R2 รับเฉพาะ ASCII ให้ดูชื่อจาก manifest แทน
- สคริปต์รันซ้ำได้ ถ้า object มีอยู่แล้วจะข้าม และสคริปต์ไม่ลบอะไรเลย
  - `uv run --env-file .env python scripts/seed_pith_to_r2.py --dry-run`
  - `uv run --env-file .env python scripts/seed_pith_to_r2.py`
- **ยังไม่ได้ลงทะเบียนเข้า DB:** ยังไม่มีแถวใน `core.knowledge_documents` และยังไม่มีอะไรใน `rag.*` ระบบจึงยังไม่รู้ว่ามีไฟล์เหล่านี้ (งาน OPS-18 กับ AI-08 ด้านล่าง)
- **เทสต์ห้ามอ่าน prefix นี้** กฎใน AGENTS.md ว่า "tests must never hit the real R2 bucket" ใช้ตามเดิม

## 2. วิธีคัด 100 ข้อ และข้อจำกัดที่ต้องรู้

**คัดยังไง**
- เริ่มจากโจทย์ public ทั้งหมดบนเว็บ 814 ข้อ แล้วเลือกเฉพาะหมวดระดับเริ่มต้นมาเป็นตัวเลือก 190 ข้อ
  - `prog/00` = โจทย์พื้นฐาน
  - `prog/10` = TOI ยุคแรกกับ COCI
  - `codecube` ข้อที่เลขไม่เกิน 100
- **ตัด PDF ที่ข้อความภาษาไทยเสียออกทั้งหมด (53 จาก 190 ไฟล์)** ส่วนใหญ่เป็น CodeCube อาการที่เจอ
  - สระหรือวรรณยุกต์ลอยแยกจากตัวอักษร เช่น "เปนภารกิ จ", "ทีใ่"
  - สระอำเพี้ยน เช่น "ควำม", "ข้อมูลนำเข้ำ", "จานวน"
  - เป็นตัวอักษรในช่วง Private Use Area จากฟอนต์ไทยรุ่นเก่า

  ไฟล์พวกนี้เปิดอ่านได้ปกติ แต่ข้อความที่ extract ออกมาใช้ทำ embedding และ `text_snapshot` ไม่ได้ ถ้าจะเพิ่มเอกสารใหม่ในอนาคต ต้องเช็คข้อความที่ extract ได้ก่อนทุกครั้ง
- ไฟล์ที่เหลือเป็น PDF ดิจิทัลทั้งหมด ไม่มีหน้าสแกน รวม 188 หน้า ข้อละ 1–3 หน้า

**สัดส่วน**
- ความยาก: `easy` 80 ข้อ / `medium` 20 ข้อ (ตรงกับค่า `easy|medium|hard` ใน schema)
- ที่มา: `prog/00` 36 / `prog/10` 54 / `codecube` 10
- topic (17 ค่า):

| topic | จำนวน | topic | จำนวน |
|---|---|---|---|
| math | 21 | recursion | 5 |
| strings | 13 | io-arithmetic | 4 |
| 2d-arrays | 12 | pattern-printing | 3 |
| simulation | 10 | conditionals | 3 |
| arrays | 8 | greedy | 2 |
| loops | 7 | queue, stack, binary-search, two-pointers, bit-manipulation | ตัวละ **1** |
| sorting | 7 | | |

**ข้อจำกัดที่กระทบ RAG โดยตรง**
- บาง topic × difficulty ไม่มีเอกสารเลยหรือมีแค่ข้อเดียว เช่น `stack` + `medium` = 0 ข้อ ถ้า filter แบบตายตัว retrieval จะคืนผลว่าง แล้ว Gemini จะแต่งโจทย์เองโดยไม่มี citation
- PDF มีแค่ตัวอย่าง input/output ข้อละ 1–3 ชุด ไม่มี test case ครบชุด
- ลิขสิทธิ์โจทย์เป็นของ TOI, สสวท., COCI และ CodeCube ใช้ในโปรเจกต์วิชาได้ แต่ถ้าเปิดเป็นระบบสาธารณะต้องแสดง `source_url` เป็นเครดิต

## 3. ข้อเสนอสำหรับงาน AI (เหตุผลของแถวใหม่ในส่วนที่ 4)

1. **embedding model:** `text-embedding-004` ที่ AI-04 กับ `rag/tables.py` ยกเป็นตัวอย่างไว้ Google เลิกให้บริการแล้ว ให้ใช้ `gemini-embedding-001` แทน
   - รองรับภาษาไทย
   - ตั้ง `output_dimensionality=768` ได้ จึงใช้ `VECTOR(768)` เดิมได้โดยไม่ต้อง migrate
   - ขนาดที่ย่อลงมาต้อง normalize vector เองก่อนคิด cosine
   - ต้องตัดสินใจก่อน ingest ครั้งแรก เพราะเปลี่ยนทีหลังต้อง re-embed ทั้งหมด
2. **chunking:** หั่นทีละโจทย์ ไม่หั่นตามจำนวน token
   - 1 โจทย์ = 1 chunk หรือแบ่งเป็น 2 chunk: (เรื่องราว + ข้อกำหนด) กับ (input/output + ตัวอย่าง)
   - ใส่ `task_id` ไว้ใน metadata ของ chunk ด้วย
3. **retrieval:** ถ้ากรองแล้วได้ไม่ถึง 3 chunk ให้ถอย filter ลงหนึ่งขั้น (ตัด difficulty ออกก่อน) แล้วบอกผู้ใช้ว่าถอย และหน้า T-03 ควรให้เลือกได้เฉพาะ topic ที่มีเอกสารจริง
4. **test case:** ห้ามให้ LLM เขียน `expected_output` เอง
   - ให้ LLM เขียน reference solution กับ input แล้วรัน solution ผ่าน `CodeRunner` เพื่อหา output
   - ใช้ตัวอย่าง I/O จาก chunk ตรวจ solution ก่อน
5. **กันลอกโจทย์:** ใน prompt ให้สั่งว่า "ใช้แนวคิด แต่เปลี่ยนเรื่องราวและข้อกำหนด" แล้วเทียบ similarity ระหว่าง draft กับ chunk ที่ cite ถ้าเกินเกณฑ์ให้ gen ใหม่
6. **วัดผลก่อนเพิ่มเอกสาร:** ทำ eval 20 prompt กระจายหลายๆ topic × difficulty แล้วดู
   - retrieval ค้นเจอ chunk ที่เกี่ยวจริงกี่ข้อ
   - draft ที่อาจารย์อนุมัติได้โดยไม่ต้องแก้หนักกี่ข้อ

   ถ้าค้นไม่เจอ แปลว่าต้องเติมเอกสาร ถ้าค้นเจอแต่ draft แย่ ต้องแก้ prompt หรือขั้นตอน test case

---

## 4. สิ่งที่ Claude Code ต้องทำ

### 4.0 ก่อนเริ่ม: commit `36933e0` บน branch `scriptupload-R2-PDF` มีการเปลี่ยนแปลงที่น่าจะไม่ตั้งใจติดมา

`git show --stat 36933e0` แสดงว่านอกจากสคริปต์กับ manifest แล้ว commit นี้ยัง

| ไฟล์ | เปลี่ยนอะไร | ต้องทำอะไร |
|---|---|---|
| `CONTEXT.md` | **ลบทั้งไฟล์** (105 บรรทัด ซึ่งเป็นเอกสาร domain ที่ AGENTS.md บอกให้อ่าน) | คืนไฟล์: `git checkout origin/dev -- CONTEXT.md` |
| `.gitignore` | เพิ่มบรรทัด `/docs` ทำให้ไฟล์ใหม่ใต้ `docs/` ทั้งหมดไม่ถูก track รวมถึง handoff นี้ | ลบบรรทัดนั้นออก |
| `.claude/settings.json` | ปิด plugin `github@claude-plugins-official` | ถามพายว่าตั้งใจไหม ถ้าไม่ตั้งใจให้คืนค่าเดิม |
| `dd`, `message.txt` | ลบ | ถามพายว่าตั้งใจไหม (ดูเป็นไฟล์ขยะ แต่ไม่ควรลบรวมอยู่ใน commit นี้) |

**ชื่อ branch:** `scriptupload-R2-PDF` ไม่ตรงรูปแบบ `<type>/<TASK-ID>-<slug>` ให้ย้ายงานไป branch `chore/OPS-17-seed-pith-pdfs` ที่แตกจาก `dev` ล่าสุด แล้ว cherry-pick เฉพาะ 2 ไฟล์ใต้ `scripts/`

**import ของสคริปต์ (ไม่บังคับ):** ตอนนี้ `seed_pith_to_r2.py` เช็ค endpoint เองในไฟล์ เพราะตอนรันครั้งแรกเรียก `greader.r2_safety` ซึ่งถูกย้ายไปแล้ว บน `dev` ตัวนี้อยู่ที่ `greader.database.storage.safety.assert_valid_r2_endpoint` จะเปลี่ยนไป import จากตรงนั้นก็ได้ เพื่อให้มีจุดเช็คแค่ที่เดียว

**Resolved (session 2026-09-28, executed on `chore/OPS-17-seed-pith-pdfs`):**
- Branch rebuilt from `origin/dev`, only `scripts/seed_pith_to_r2.py` and
  `scripts/seed/pith-100-manifest.csv` carried over from `36933e0` — the
  branch never touches `CONTEXT.md`, `.gitignore`, `.claude/settings.json`,
  `dd`, or `message.txt`, so no revert was needed on it.
- `.claude/settings.json` plugin toggle: confirmed intentional, kept disabled.
- `dd` / `message.txt`: confirmed junk, kept deleted (not restored).
- Import consolidation: done — `seed_pith_to_r2.py` now imports
  `assert_valid_r2_endpoint` from `greader.database.storage.safety`, wrapped
  in the same `try/except ValueError: sys.exit(str(error))` pattern
  `scripts/ci_r2_cleanup.py` uses.
- Old branch `scriptupload-R2-PDF` deleted, local and origin, after the new
  branch was pushed; no PR had been opened against it.

### 4.1 `docs/task-scope.md` — เพิ่มแถว

แถวใหม่ต่อท้ายตาราง หมายเลขถัดไปที่ยังว่างคือ OPS-17, OPS-18, AI-08, DES-04, DES-05 (เช็คแล้วทั้งใน `task-scope.md` และ `task-archive.md` บน `dev`)

| TASK-ID | Owner | Status | May touch | Done when |
|---|---|---|---|---|
| OPS-17 | พาย | done | `scripts/`, `docs/task-scope.md`, `AGENTS.md`, `docs/handoff/`; creates: `scripts/seed_pith_to_r2.py`, `scripts/seed/pith-100-manifest.csv`, `docs/handoff/2026-09-28-OPS-17-pith-seed.md` | PDF โจทย์ 100 ไฟล์จาก programming.in.th อยู่บน R2 ใต้ `sources/programming-in-th/`; manifest มี topic และ difficulty ครบทุกแถว; รันสคริปต์ซ้ำแล้วข้ามครบ 100 ไฟล์ |
| OPS-18 | พาย | open | `scripts/seed_pith_to_r2.py`, `core/uploads/models.py`, `database/core/knowledge_document_repository.py`, `tests/db/` | มี 100 แถวใน `core.knowledge_documents` ที่ `r2_object_key` ชี้ไปที่ seed และ `metadata` มี `topic`, `difficulty`, `course: "seed-pith"`; รันซ้ำไม่เกิดแถวซ้ำ (เช็คจาก `content_hash`); repository เขียน `metadata_` ได้ พร้อมเทสต์ `postgres` ยืนยัน. ต้องคุยกับเจ้าของ CORE-16 ก่อน เพราะแตะ `core/uploads/models.py` เหมือนกัน |
| AI-08 | ฟิล์ม | open | `ai/`; creates: `scripts/ingest_seed.py` | ทำหลัง AI-02 ถึง AI-04 และ OPS-18: ingest seed ทั้ง 100 ไฟล์จาก R2 แล้ว `rag.knowledge_sources` มีสถานะ `ready` ครบ 100 แถว, `metadata` ก็อป topic และ difficulty มาจาก core, chunk ละโจทย์ (1–2 chunk ต่อไฟล์) และมี `task_id` ใน metadata |
| DES-04 | อุ้ม | open | `docs/`; creates: `docs/rag-eval.md` | มี prompt ทดสอบ 20 ข้อ กระจายหลายๆ topic × difficulty ใน `docs/rag-eval.md`; แต่ละข้อบันทึกว่า retrieval เจอ chunk ที่เกี่ยวข้องไหม และ draft อนุมัติได้โดยแก้ไม่เกิน 2 จุดไหม; สรุปท้ายไฟล์ว่า topic ไหนต้องเติมเอกสาร |
| DES-05 | อุ้ม | open | `scripts/seed/pith-100-manifest.csv` | เติมโจทย์ topic ที่มีน้อยกว่า 3 ข้อ (queue, stack, binary-search, two-pointers, bit-manipulation, greedy) topic ละอย่างน้อย 3 ข้อ และเพิ่ม `medium` ให้ recursion กับ strings; ทุกไฟล์ที่เพิ่มผ่านการเช็คว่าข้อความภาษาไทยที่ extract ได้ไม่เพี้ยน (ดู handoff OPS-17 ข้อ 2); รันสคริปต์ seed แล้วอัปเฉพาะไฟล์ใหม่ |

**แก้แถวเดิม** (เติมท้ายคอลัมน์ Done when โดยไม่ลบข้อความเดิม)

- **AI-03:** เติม `ขอบเขต chunk คือ 1 โจทย์ (หรือแยก เรื่องราว+ข้อกำหนด / I/O+ตัวอย่าง) ไม่หั่นตามจำนวน token; seed ใน R2 (OPS-17) ใช้เป็นไฟล์ทดสอบได้`
- **AI-04:** ในวงเล็บตัวเลือก เปลี่ยน `google-genai เรียก text-embedding-004` เป็น `google-genai เรียก gemini-embedding-001 ด้วย output_dimensionality=768 แล้ว normalize เอง (text-embedding-004 ถูกยกเลิกแล้ว)`
- **AI-05:** เติม `ถ้ากรองแล้วได้น้อยกว่า 3 chunk ให้ถอย filter ลงหนึ่งขั้น (ตัด difficulty ก่อน) และคืน flag บอกว่าถอย`
- **AI-06:** เติม `expected_output ของ test case ได้จากการรัน reference solution ผ่าน CodeRunner ไม่ใช่ให้ LLM เขียน; ตัวอย่าง I/O ใน chunk ใช้ตรวจ solution; draft ที่คล้าย chunk ที่ cite เกินเกณฑ์ต้อง regenerate. ตอนนี้ CodeRunner ใน production ยังเป็น stub (CORE-17)`

### 4.2 `AGENTS.md`

**ตาราง Status:** แก้ช่อง State ของแถว `ai/` ต่อท้ายว่า

> Seed corpus: 100 PDFs on R2 under `sources/programming-in-th/` (OPS-17), not yet in `core.knowledge_documents` (OPS-18) or `rag` (AI-08).

**เพิ่ม section ใหม่** ต่อจาก `## Commands`:

```markdown
## Seed corpus on R2

100 Thai problem-statement PDFs from programming.in.th live in the dev R2
bucket under `sources/programming-in-th/{task_id}.pdf` (OPS-17). Their topic
and difficulty are in `scripts/seed/pith-100-manifest.csv`; background, selection
rules and known limits are in `docs/handoff/2026-09-28-OPS-17-pith-seed.md`.

- Re-seed with `uv run --env-file .env python scripts/seed_pith_to_r2.py`
  (`--dry-run` first). It skips objects that exist and never deletes.
- Do not delete or overwrite objects under that prefix; ingestion work reads them.
- Tests never read this prefix — the "never hit the real R2 bucket" rule above
  still applies. Use `tests/fixtures/pdfs/` or moto.
- Adding a PDF: check its extracted Thai text first. 53 of 190 candidates were
  rejected for floating vowels, broken ำ or Private-Use-Area glyphs.
```

### 4.3 ไฟล์นี้

วางไฟล์นี้ที่ `docs/handoff/2026-09-28-OPS-17-pith-seed.md` (ต้องลบ `/docs` ออกจาก `.gitignore` ตามข้อ 4.0 ก่อน ไม่งั้นจะ add ไม่ได้)

### 4.4 ตรวจก่อนเปิด PR

- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` ผ่าน
- `uv run python -m scripts.task_scope พาย --maintainer` ต้องไม่มีแถวใหม่ในหัวข้อ "needs updating" ถ้ามี แปลว่า path ใน May touch ยังไม่มีอยู่จริง ให้ย้ายไปไว้ใน `creates:`; `uv run python -m scripts.task_scope ฟิล์ม` กับ `อุ้ม` ต้องเห็น AI-08 และ DES-04/05 ตามลำดับ
- `tests/unit/test_task_scope.py` ผ่าน
- `git diff origin/dev --stat` ต้องไม่มี `CONTEXT.md`, `.gitignore` ที่มี `/docs`, หรือ `.claude/settings.json` ติดไป
- PR target `dev` และคำอธิบาย PR อ้างผล CI ของ head commit
