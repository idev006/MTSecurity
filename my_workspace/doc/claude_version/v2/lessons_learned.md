# MTSecurity v2 — Lessons Learned / Bug & Solution Log

> Knowledge base for development, debugging, and future-proofing
> Format: Date | Category | Symptom → Root Cause → Fix → Prevention

---

## BUG-001 — EventsView: page_size & filters had no effect

**Date:** 2026-05-15
**Severity:** High (core feature broken)
**Session:** Context window #3

### Symptom
- Clicking page size buttons (10 / 25 / 50 / 100) on `/events` — table always showed 50 rows
- Selecting severity / status / behavior filters — table always returned same unfiltered results
- Both bugs present since the feature was first added

### Investigation Path
1. Checked Vue frontend first — `onPageSizeClick()` handler looked correct, `v-model` + `@change` on filters looked correct
2. Used Claude in Chrome extension to click "10" button via JS → DOM updated (btn-neutral class) → proved Vue reactivity works
3. Patched `window.fetch` to intercept API calls → confirmed `?page_size=25&page=1` WAS being sent by browser
4. Direct browser `fetch('/api/v1/events?page_size=5')` returned 50 rows → **backend confirmed ignoring the param**
5. Found root cause in `api/routers/events.py`

### Root Cause
```python
# BEFORE (broken)
async def list_events(request, db, user, f: EventFilter = None):
    if f is None:
        f = EventFilter()   # ← always default page_size=50, no filters
```

FastAPI treats a **Pydantic BaseModel parameter as a request body** on GET routes.
Since GET requests have no body, `f` was always `None`.
The `if f is None: f = EventFilter()` fallback silently used all defaults (`page_size=50`, no filters).
Every single query always returned the first 50 events regardless of what the browser sent.

### Fix
```python
# api/routers/events.py
from fastapi import Depends

# AFTER (fixed)
async def list_events(request, db, user, f: EventFilter = Depends()):
    # Depends() tells FastAPI to parse each field of EventFilter from query params
    # No fallback needed — FastAPI always provides a valid EventFilter instance
```

**Commit:** `e603e98`

### Prevention Rules
1. **NEVER use `= None` for Pydantic model parameters in GET routes.** Always use `= Depends()`.
2. FastAPI parameter type → source mapping:
   - `simple type + = None` → optional query param ✅
   - `Pydantic model + = None` → **tries request body** (GET has none → always None) ❌
   - `Pydantic model + = Depends()` → parses each field as individual query params ✅
3. **Test filtering immediately** after adding a filter schema — don't assume it works until verified with network inspection.
4. Any router that uses a Pydantic model for filtering should have this pattern — check `rules.py`, `users.py`, etc. for the same issue if they have list endpoints with filtering.

---

## BUG-002 — EventsView: Race condition with AppLayout overwrites data

**Date:** 2026-05-15
**Severity:** Medium (intermittent, hard to reproduce consistently)
**Session:** Context window #2-3

### Symptom
- After fixing the backend `Depends()` bug, the EventsView sometimes still showed wrong data
- Switching page size appeared to work but occasionally reverted to 50 rows
- Filtering would sometimes have no visible effect

### Investigation Path
1. Browser network inspector showed **two simultaneous requests** to `/api/v1/events`:
   - `GET /events?page_size=50` (no other params) — from AppLayout
   - `GET /events?page=1&page_size=25` — from EventsView
2. Both requests wrote to the **same `events.events` Pinia store array**
3. Whichever request resolved last "won" — often the unfiltered AppLayout request

### Root Cause
```typescript
// AppLayout.vue (line 364) — fires on every page mount
await events.fetchRecent()  // defaults: page_size=50, no filters

// EventsView.vue — also fires on mount
await eventsApi.list({ page: 1, page_size: 25 })
→ events.events = result  // same Pinia store!
```
Race condition: two concurrent writes to the same reactive array.

### Fix
```typescript
// EventsView.vue — use LOCAL state, not shared Pinia store
const rows = ref<EventRead[]>([])  // local to EventsView

// Load from API directly, write to local ref
rows.value = await eventsApi.list(params)

// Keep store in sync only for the navbar bell count
// (after ack/silence/escalate actions)
eventsStore.acknowledge(ev.id)
```

**Commit:** `82c27e1`

### Prevention Rules
1. **Each view should own its data.** Only use shared store for truly global state (unread count, live alerts).
2. When a view needs server-side pagination/filtering, **never mix that with a global store** that is also written by other components.
3. Pattern: view-specific data → local `ref<T[]>()` + direct API call. Global summary counts → Pinia store.

---

## BUG-003 — Vite HMR not propagating changes to browser

**Date:** 2026-05-15
**Severity:** Low (dev workflow friction only)
**Session:** Context window #2-3

### Symptom
- File changes saved to disk, verified by `git diff`
- Browser at localhost:5173 still shows old behavior
- No HMR update messages appear in browser console

### Investigation Path
1. Confirmed file was genuinely saved (`git status` showed modified)
2. HMR console messages (`[vite] hot updated`) never appeared
3. Hard refresh (Ctrl+Shift+R) also didn't help consistently
4. Eventually resolved after committing and doing a fresh navigation

### Root Cause (suspected)
- Vite HMR can fail to propagate on Windows when file watchers miss events
- Possible cause: file written by tool that doesn't trigger `fs.watch` properly
- OR: large component tree where HMR invalidation chain breaks

### Fix / Workaround
1. If HMR not working: navigate away from the route and back
2. If still stuck: hard refresh (Ctrl+Shift+R)
3. If still stuck: restart the Vite dev server
4. Verify the change is actually in the running code using browser DevTools → Sources

### Prevention Rules
1. When debugging frontend bugs, **always verify the code running in the browser** matches what's on disk (DevTools → Sources → search for a unique string from the latest code).
2. Don't assume HMR worked just because the terminal says "saved". Check the browser console for `[vite] hot updated` confirmation.

---

## BUG-004 — Backend process running without --reload (no auto-restart on file change)

**Date:** 2026-05-15
**Severity:** Medium (dev workflow — file changes invisible until restart)
**Session:** Context window #3

### Symptom
- Fixed backend code, saved file → browser still shows old behavior
- `curl /api/v1/events?page_size=5` still returned 50 rows after the fix

### Investigation Path
1. Checked running processes → `python main.py` (no `--reload` flag)
2. Backend needs manual restart after code changes

### Fix
```powershell
Stop-Process -Id <pid> -Force
Start-Process "D:\dev\MTSecurity\my_env\Scripts\python" -ArgumentList "main.py" -WorkingDirectory "D:\dev\MTSecurity\my_workspace\backend"
```

### Prevention Rules
1. Add `--reload` flag to backend startup for dev, or use `uvicorn main:app --reload`
2. The `.claude/launch.json` only configures the frontend. Consider adding a backend config.
3. After any backend file change, **always restart the backend** and verify with a direct curl test before testing in browser.
4. Quick verify after backend restart:
   ```bash
   curl "http://localhost:8000/api/v1/events?page_size=5" -H "Authorization: Bearer <token>" | python -c "import sys,json; print(len(json.load(sys.stdin)))"
   # Should print: 5
   ```

---

## PATTERN-001 — FastAPI dependency injection patterns

**Category:** Architecture Pattern
**Applies to:** All routers

### Query parameter model (GET list endpoints)
```python
# ✅ CORRECT — parse each field as query param
async def list_events(f: EventFilter = Depends()):

# ✅ ALSO CORRECT — explicit with type hint
async def list_events(f: Annotated[EventFilter, Depends()]):

# ❌ WRONG — treated as request body (always None on GET)
async def list_events(f: EventFilter = None):

# ❌ WRONG — treated as request body
async def list_events(f: EventFilter | None = None):
```

### Database session
```python
# Standard pattern (from api/deps.py)
DBDep = Annotated[AsyncSession, Depends(get_db)]

async def my_endpoint(db: DBDep):
    result = await db.execute(select(MyModel))
```

### Auth + permission
```python
# From api/deps.py
CurrentUser = Annotated[User, Depends(get_current_user)]

@router.get("", dependencies=[require("events:read")])
async def list_events(user: CurrentUser):
    # user.role, user.camera_ids(), etc.
```

---

## PATTERN-002 — Frontend state ownership

**Category:** Architecture Pattern
**Applies to:** All Vue views with paginated/filtered data

```typescript
// ✅ View-owned state (for paginated/filtered data)
const rows = ref<EventRead[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  rows.value = await eventsApi.list({ page: page.value, page_size: pageSize.value })
}

// ✅ Sync global store only for cross-view state (bell count, etc.)
eventsStore.acknowledge(ev.id)  // updates newCount in navbar

// ❌ Anti-pattern: writing paginated results to a shared store
// (race condition when AppLayout also writes to same store)
eventsStore.events = await eventsApi.list(params)
```

### Rule of thumb
- **Global store (Pinia)**: live alert queue, unread count, camera statuses, system health
- **Local ref**: paginated tables, filtered views, forms

---

## PATTERN-003 — Vue 3 filter controls (select + @change)

**Category:** Frontend Pattern
**Applies to:** EventsView, any filter UIs

### Reliable pattern
```vue
<!-- v-model updates ref FIRST, then @change fires — order guaranteed in Vue 3 -->
<select v-model="severity" @change="resetAndLoad">
  <option value="">ALL</option>
  <option value="critical">CRITICAL</option>
</select>

<script setup>
const severity = ref('')

function resetAndLoad() {
  page.value = 1
  load()  // severity.value is already updated by v-model at this point
}
</script>
```

### Unreliable patterns (avoid)
```typescript
// ❌ watch() can be unreliable for UI interactions (timing edge cases)
watch(severity, () => load())

// ❌ @change without v-model — ref not updated yet when handler runs
// <select @change="onFilterChange">
function onFilterChange(e) {
  severity.value = e.target.value  // must manually sync
  load()
}
```

---

## PATTERN-004 — Page size buttons (avoid <select> for this)

**Category:** Frontend Pattern
**Applies to:** Any paginated table with discrete page sizes

```vue
<!-- ✅ Button group — no v-model, no type coercion, click is immediate -->
<div class="join">
  <button v-for="s in PAGE_SIZES" :key="s"
    class="join-item btn btn-xs font-mono"
    :class="pageSize === s ? 'btn-neutral' : 'btn-ghost'"
    @click="onPageSizeClick(s)">
    {{ s }}
  </button>
</div>

<script setup>
const PAGE_SIZES = [10, 25, 50, 100]
const pageSize = ref(25)

function onPageSizeClick(s: number) {
  if (pageSize.value === s) return  // already selected, no-op
  pageSize.value = s
  page.value = 1
  load()
}
</script>
```

Problems with `<select>` for page size:
- `:value` binding unreliable for select elements (one-way binding issues)
- Type coercion: `v-model` on `<select>` returns string, comparing to number fails silently
- Less visual feedback than button group

---

## PATTERN-005 — Backend file change verification

**Category:** Dev Workflow
**Applies to:** Any backend change

```bash
# 1. Make the change
# 2. Restart backend (no --reload flag present)
Stop-Process -Id <pid> -Force && python main.py

# 3. Verify via direct curl (don't rely on browser — might have cached JS)
TOKEN=$(...)  # get token from browser localStorage
curl "http://localhost:8000/api/v1/events?page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; print(len(json.load(sys.stdin)))"

# 4. Only then test in browser
```

---

## LESSON-001 — Debugging strategy: browser vs backend

**Category:** Debugging Methodology

When a UI feature doesn't work, use binary search to find which layer is broken:

```
Layer 1: Is the frontend sending the right request?
  → Browser DevTools → Network tab → check URL params
  → OR patch window.fetch to log calls

Layer 2: Is the backend receiving and using the params?
  → curl directly to backend with same params
  → Compare response count/content

Layer 3: Is the backend query correct?
  → Check router dependency pattern (Depends vs = None)
  → Check model field names match query string keys
  → Add logging to router handler

Layer 4: Is the database returning correct rows?
  → Check SQL with echo=True on engine temporarily
```

**In this project:** Always test with a direct `curl` to `localhost:8000` before testing in browser. Browser has JS cache, Vite proxy, Vue reactivity — too many variables.

---

## LESSON-002 — Code patterns that have tripped us up

**Category:** Code Quality Awareness

These patterns look correct but have subtle bugs:

### 1. Pydantic model as GET parameter (BUG-001)
```python
# Looks fine, is broken:
async def endpoint(f: MyFilter = None): ...  # ← always None on GET
```

### 2. Shared store for paginated view data (BUG-002)
```typescript
// Looks fine, has race condition:
store.items = await api.list(params)  // ← AppLayout may overwrite it
```

### 3. Vue watch on ref for UI interaction
```typescript
// Looks fine, timing edge cases:
watch(filterRef, () => load())  // ← may fire before user interaction completes
```

### 4. Missing await on async store action
```typescript
// Looks fine, silently fails:
store.fetchData()  // ← missing await, component may render before data arrives
await store.fetchData()  // ← correct
```

---

## LESSON-003 — Tools that actually work for debugging

**Category:** Dev Tooling

| Problem | Tool | How |
|---------|------|-----|
| Which network requests fire? | Claude in Chrome extension | `read_network_requests` with urlPattern |
| Does my click handler fire? | Claude in Chrome + JS eval | Patch `window.fetch`, click via JS, check call log |
| Is backend receiving params? | Direct curl | Bypass all frontend layers |
| Is Vue state updated? | Claude in Chrome + JS eval | Check DOM classes that reflect reactive state |
| Is backend code reloaded? | Process list + restart | `Get-WmiObject Win32_Process` → stop → restart |
| HMR not working? | Browser DevTools → Sources | Find the file, search for unique string in latest code |

---

## REFACTOR-001 — Backend --reload support (2026-05-15)

**Problem:** `python main.py` had no `--reload` flag → every code change required manual process kill + restart.

**Root cause:** Service init (CameraManager, AIPipeline, etc.) happened in `bootstrap()` BEFORE passing app to uvicorn. `uvicorn --reload` requires importing the app from a **string path** (`"api.app:app"`), which means uvicorn controls the process. Passing an already-instantiated `app` object blocks this.

**Solution:** Move all service init into FastAPI `lifespan` context manager:
```python
# api/app.py
@asynccontextmanager
async def _lifespan(app: FastAPI):
    # startup: init MessageBus, DB, CameraManager, AI, RuleEngine...
    yield
    # shutdown: stop all services

app = create_app()  # module-level — required for string import
```

```python
# main.py
uvicorn.run(
    "api.app:app",   # string import → uvicorn can reload
    reload=args.reload,
    reload_dirs=[...],
)
```

**Usage:**
```bash
python main.py           # production
python main.py --reload  # dev — auto-reloads on any .py change
```

**Commit:** `534f8f6`

**Prevention:** Any FastAPI project that needs `--reload` must:
1. Use string import (`"module:app"`) not object reference
2. Put ALL startup work in `lifespan`, not before `uvicorn.run()`

---

## BUG-005 — AI Pipeline: detect เฉพาะ person ไม่ detect cat/dog หรือ object อื่นๆ

**Date:** 2026-05-15
**Severity:** High (AI detection ทำงานได้แค่ 1 ใน 80 class)
**Session:** Context window #4

### Symptom
- Pilot Console แสดง bounding box เฉพาะ `person` เท่านั้น
- `cat`, `dog`, `laptop`, `car` และ object อื่นๆ ที่อยู่ในกล้องไม่ถูก detect เลย
- ไม่มี error ใดๆ ใน log

### Investigation Path
1. ตรวจสอบ `ai/pipeline.py` — พบ `self._target_classes = target_classes or [0]` (COCO class 0 = person)
2. ตรวจสอบ `api/app.py` — `AIPipeline` ถูก init โดยไม่ส่ง `target_classes` → default เป็น `[0]`
3. ตรวจสอบ `ai/detector.py` `postprocess_yolo()` — มี filter `np.isin(class_ids, target_classes)` ซึ่ง filter ออกทุก class ยกเว้น person

### Root Cause (Layer 1 — หลัก)
```python
# ai/pipeline.py — BEFORE (broken)
self._target_classes = target_classes or [0]   # 0 = person
# AIPipeline ถูก init ใน app.py โดยไม่ส่ง target_classes
# → default เป็น [0] → filter ออกทุก class ยกเว้น person (COCO index 0)
```

COCO class indices สำคัญ: `person=0`, `cat=15`, `dog=16`, `laptop=63`, `car=2`

### Root Cause (Layer 2 — ซ่อนอยู่)
Process ที่ listen port 8000 เป็น **system Python** (`C:\Users\acer\AppData\Local\Python\pythoncore-3.12-64\python.exe`) ซึ่งไม่มี `openvino` ติดตั้ง → `InferenceEngine` รันใน **dummy mode** → `infer()` return `([], 0.0)` เสมอ → ไม่มี detection เลยแม้แต่ person

### Fix
```python
# ai/pipeline.py — AFTER (fixed)
self._target_classes = target_classes  # None = detect ทุก COCO class

# config.py — เพิ่ม configurable field
ai_target_classes: list[int] | None = None  # None = all; e.g. [0,15,16] = person+cat+dog

# api/app.py — ส่งจาก config
ai_pipeline = AIPipeline(
    ...
    target_classes=cfg.ai_target_classes,  # ← เพิ่มบรรทัดนี้
)
```

Layer 2: Kill process system Python และ restart ด้วย project venv (`D:\dev\MTSecurity\my_env\Scripts\python`)

### Verification
หลังแก้ไข browser DOM แสดง: `["PERSON: TRK-154 (85%)", "LAPTOP: TRK-155 (73%)"]` — detect ได้หลาย class พร้อมกัน

### Prevention Rules
1. **ตรวจสอบ default ของ `target_classes`** ใน `AIPipeline.__init__` ทุกครั้งที่ตั้ง pipeline ใหม่ — `or [0]` เป็น footgun
2. **ก่อน debug detection ปัญหา:** ตรวจสอบว่า `InferenceEngine.is_ready` เป็น `True` เสมอ (`is_ready = _infer_req is not None`)
3. **ตรวจสอบ port binding:** `netstat -ano | findstr ":8000"` → verify PID เป็น project venv process
4. **Verify OpenVINO:** `python -c "import openvino; print(openvino.__version__)"` ใน venv ก่อน start backend
5. ถ้าต้องการ detect เฉพาะบาง class → ใช้ `.env`: `AI_TARGET_CLASSES=[0,15,16]`

---

## BUG-006 — Backend ถูกรันด้วย System Python แทน Project Venv

**Date:** 2026-05-15
**Severity:** High (AI ไม่ทำงานเลย, packages หาย)
**Session:** Context window #4

### Symptom
- AI detection ไม่มีผลลัพธ์เลย (dummy mode)
- `netstat -ano | findstr ":8000"` แสดง PID ที่ไม่ใช่ process ที่เราตั้งใจรัน

### Root Cause
มีสอง Python process รัน `main.py --reload` พร้อมกัน:
- PID ของ project venv (`D:\dev\MTSecurity\my_env\Scripts\python`) — มี openvino ✓
- PID ของ system Python (`C:\Users\acer\AppData\Local\Python\pythoncore-3.12-64\python.exe`) — ไม่มี openvino ✗

Process ที่ start ก่อนจะ bind port 8000 ได้ก่อน ถ้า system Python ชนะจะทำให้ AI อยู่ใน dummy mode

### Fix
```powershell
# 1. หา PID ที่ listen port 8000
netstat -ano | findstr ":8000"

# 2. ตรวจสอบว่า PID นั้นเป็น Python ตัวไหน
Get-WmiObject Win32_Process -Filter "ProcessId=<PID>" | Select-Object ExecutablePath

# 3. ถ้าเป็น system Python — kill และ restart ด้วย venv
Stop-Process -Id <PID> -Force
Start-Process cmd -ArgumentList "/k `"cd /d D:\dev\MTSecurity\my_workspace\backend && D:\dev\MTSecurity\my_env\Scripts\python main.py --reload`""
```

### Prevention Rules
1. **ใช้ batch file dev.bat** (มีอยู่แล้วใน project) แทนการรัน command เอง — batch file ระบุ path venv ตายตัว
2. **ปิด terminal เก่าให้หมด** ก่อน start backend ใหม่ทุกครั้ง
3. **Quick verify หลัง start:** `(Invoke-WebRequest http://localhost:8000/api/v1/health).Content` ตรวจ `boot_state: RUNNING`

---

## TODO — Known technical debt

| Item | Location | Priority | Notes |
|------|----------|----------|-------|
| Check other list endpoints for `Depends()` bug | `rules.py`, `users.py` GET list | High | Same pattern as BUG-001 may exist |
| ~~Add total count to EventFilter response~~ | ~~backend events.py~~ | ~~Low~~ | **Fixed** — EventPage schema + COUNT(*) query (2026-05-15) |
| LPR integration in AI pipeline | `ai/lpr/` | Low | Currently wired but not active |
| NLQ (Natural Language Query) | `nlq/` | Low | Needs Anthropic API key |
| Snapshot cleanup job | alerts/snapshot.py | Medium | max_snapshot_age_days in config but no cron |
| ~~WebSocket reconnect on frontend~~ | ~~stores/system.ts~~ | ~~Medium~~ | **Fixed** — `_destroyed` flag กัน reconnect timer leak (2026-05-15) |
