// Reference copy of the Figma Make prototype "Questly Classroom Web App (Copy)"
// (fileKey ft2Fe3c5xrv3NO2zCq21wi, src/App.tsx), pulled 2026-10-12.
// READ-ONLY reference for markup structure and copy. Do NOT port the React
// state/onClick logic: Questly templates are server-rendered Jinja2 with no
// browser JavaScript. Mock data below is illustrative only.
import { useMemo, useState, type ReactNode } from "react";

type Role = "student" | "teacher" | "admin";
type Screen =
  | "login"
  | "signup"
  | "verify"
  | "classrooms"
  | "classroom"
  | "solve"
  | "join"
  | "create-classroom"
  | "results"
  | "create-problem"
  | "documents"
  | "class-settings"
  | "admin";

type IconName =
  | "book"
  | "bell"
  | "chevron"
  | "plus"
  | "users"
  | "chart"
  | "code"
  | "clock"
  | "check"
  | "x"
  | "play"
  | "send"
  | "settings"
  | "sparkles"
  | "file"
  | "upload"
  | "arrow"
  | "copy"
  | "more"
  | "search"
  | "shield";

// Icon paths: see templates/_components/icons.html (already converted).

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Button({ children, variant = "primary", icon, onClick, type = "button", disabled = false }: { children: ReactNode; variant?: "primary" | "secondary" | "ghost" | "danger"; icon?: IconName; onClick?: () => void; type?: "button" | "submit"; disabled?: boolean }) {
  return <button type={type} disabled={disabled} onClick={onClick} className={`btn btn-${variant}`}>{icon && <Icon name={icon} />}{children}</button>;
}

function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "success" | "warning" | "danger" | "neutral" | "pink" | "blue" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

const problems = [
  { id: 1, title: "Two Sum", slug: "Array & Hash Map", difficulty: "Easy", due: "12 May, 23:59", status: "Passed", solved: 32, total: 36 },
  { id: 2, title: "Valid Parentheses", slug: "Stack", difficulty: "Easy", due: "14 May, 23:59", status: "In progress", solved: 24, total: 36 },
  { id: 3, title: "Longest Increasing Subsequence", slug: "Dynamic Programming", difficulty: "Hard", due: "18 May, 23:59", status: "Not started", solved: 9, total: 36 },
  { id: 4, title: "Binary Tree Level Order", slug: "Tree & BFS", difficulty: "Medium", due: "20 May, 23:59", status: "Not started", solved: 18, total: 36 },
];

const students = [
  ["65010001", "Araya S.", "Passed", "10/10", "8 May, 14:32"],
  ["65010012", "Napat K.", "Partial", "7/10", "9 May, 09:15"],
  ["65010024", "Pimchanok T.", "Passed", "10/10", "9 May, 18:44"],
  ["65010037", "Thanawat J.", "Runtime error", "3/10", "10 May, 11:08"],
  ["65010048", "Krittin P.", "Pending", "—", "Not submitted"],
];

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [role, setRole] = useState<Role>("student");
  const [tab, setTab] = useState("Problems");
  const [menu, setMenu] = useState(false);
  const [empty, setEmpty] = useState(false);
  const [created, setCreated] = useState(false);
  const [result, setResult] = useState<"idle" | "passed" | "partial" | "error">("idle");

  const enter = (nextRole: Role = "student") => {
    setRole(nextRole);
    setScreen(nextRole === "admin" ? "admin" : "classrooms");
    setMenu(false);
  };

  if (screen === "login" || screen === "signup" || screen === "verify") {
    return <Auth screen={screen} setScreen={setScreen} enter={enter} />;
  }

  return (
    <div className="app-shell">
      <Header role={role} menu={menu} setMenu={setMenu} enter={enter} logout={() => setScreen("login")} />
      <main>
        {screen === "classrooms" && <Classrooms role={role} empty={empty} setEmpty={setEmpty} go={setScreen} />}
        {screen === "join" && <Join go={setScreen} />}
        {screen === "create-classroom" && <CreateClassroom created={created} setCreated={setCreated} go={setScreen} />}
        {screen === "classroom" && <Classroom role={role} tab={tab} setTab={setTab} go={setScreen} />}
        {screen === "solve" && <Solve result={result} setResult={setResult} go={setScreen} />}
        {screen === "results" && <Results go={setScreen} />}
        {screen === "create-problem" && <CreateProblem go={setScreen} />}
        {screen === "documents" && <Documents go={setScreen} />}
        {screen === "class-settings" && <ClassSettings go={setScreen} />}
        {screen === "admin" && <Admin />}
      </main>
    </div>
  );
}

function Auth({ screen, setScreen, enter }: { screen: Screen; setScreen: (s: Screen) => void; enter: (r?: Role) => void }) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const invalid = submitted && (!email.endsWith("@kmitl.ac.th") || email.startsWith("used"));
  if (screen === "verify") {
    return <div className="auth-page"><div className="auth-brand"><Logo light /><p>เปลี่ยนทุกโจทย์ให้เป็นก้าวต่อไปของคุณ</p></div><section className="auth-card verify-card"><div className="mail-illustration"><Icon name="send" size={32} /></div><h1>ยืนยันอีเมลของคุณ</h1><p>เราได้ส่งลิงก์ยืนยันไปที่</p><strong>{email || "student@kmitl.ac.th"}</strong><div className="notice"><Icon name="clock" /><span>กำลังรอการยืนยันอีเมล<br /><small>เปิดลิงก์ในอีเมล แล้วกลับมาที่หน้านี้</small></span></div><Button onClick={() => enter("student")}>ฉันยืนยันอีเมลแล้ว</Button><Button variant="ghost">ส่งอีเมลอีกครั้ง</Button><button className="text-link" onClick={() => setScreen("login")}>กลับไปหน้าเข้าสู่ระบบ</button></section></div>;
  }
  return (
    <div className="auth-page">
      <div className="auth-brand"><Logo light /><div><h2>Learn. Code. Grow.</h2><p>พื้นที่เรียนรู้การเขียนโปรแกรม<br />ที่เติบโตไปพร้อมกับคุณ</p></div><div className="code-art"><span>function grow(skill) {"{"}</span><span> &nbsp;return skill + practice;</span><span>{"}"}</span></div></div>
      <section className="auth-card">
        <div className="mobile-logo"><Logo /></div>
        <h1>{screen === "login" ? "ยินดีต้อนรับกลับ" : "สร้างบัญชี Questly"}</h1>
        <p>{screen === "login" ? "เข้าสู่ระบบเพื่อทำภารกิจของคุณต่อ" : "เริ่มต้นเส้นทางการเขียนโปรแกรมของคุณ"}</p>
        {screen === "signup" && <label>ชื่อ–นามสกุล<input placeholder="เช่น สมชาย ใจดี" /></label>}
        <label>อีเมลสถาบัน<input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@kmitl.ac.th" className={invalid ? "input-error" : ""} /></label>
        {invalid && <div className="field-error"><Icon name="x" size={14} />{email.startsWith("used") ? "อีเมลนี้ถูกใช้งานแล้ว" : "กรุณาใช้อีเมล @kmitl.ac.th เท่านั้น"}</div>}
        <label>รหัสผ่าน<input type="password" placeholder="อย่างน้อย 8 ตัวอักษร" /></label>
        {screen === "login" && <div className="form-row"><label className="check"><input type="checkbox" /> จดจำฉัน</label><button className="text-link">ลืมรหัสผ่าน?</button></div>}
        <Button onClick={() => { setSubmitted(true); if (screen === "login") enter("student"); else if (email.endsWith("@kmitl.ac.th") && !email.startsWith("used")) setScreen("verify"); }}>{screen === "login" ? "เข้าสู่ระบบ" : "สร้างบัญชี"}</Button>
        <div className="divider"><span>หรือทดลองในฐานะ</span></div>
        <div className="demo-buttons"><Button variant="secondary" onClick={() => enter("teacher")}>อาจารย์</Button><Button variant="secondary" onClick={() => enter("admin")}>ผู้ดูแลระบบ</Button></div>
        <p className="auth-switch">{screen === "login" ? "ยังไม่มีบัญชี?" : "มีบัญชีอยู่แล้ว?"} <button className="text-link" onClick={() => setScreen(screen === "login" ? "signup" : "login")}>{screen === "login" ? "สมัครสมาชิก" : "เข้าสู่ระบบ"}</button></p>
      </section>
    </div>
  );
}

function Logo({ light = false }: { light?: boolean }) {
  return <div className={`logo ${light ? "logo-light" : ""}`}><span><Icon name="book" size={22} /></span>Questly</div>;
}

function Header({ role, menu, setMenu, enter, logout }: { role: Role; menu: boolean; setMenu: (v: boolean) => void; enter: (r: Role) => void; logout: () => void }) {
  const names = { student: "Araya S.", teacher: "Dr. Narin K.", admin: "System Admin" };
  return <header><Logo /><div className="header-actions"><button className="icon-btn notification"><Icon name="bell" /><i /></button><button className="user-button" onClick={() => setMenu(!menu)}><span className="avatar">{names[role].slice(0, 2).toUpperCase()}</span><span><strong>{names[role]}</strong><small>{role === "teacher" ? "Instructor" : role[0].toUpperCase() + role.slice(1)}</small></span><Icon name="chevron" size={15} /></button>{menu && <div className="user-menu"><small>สลับมุมมองสำหรับเดโม</small><button onClick={() => enter("student")}>Student view</button><button onClick={() => enter("teacher")}>Instructor view</button><button onClick={() => enter("admin")}>Admin settings</button><hr /><button onClick={logout}>ออกจากระบบ</button></div>}</div></header>;
}

function PageTop({ eyebrow, title, description, children, back }: { eyebrow?: string; title: string; description?: string; children?: ReactNode; back?: () => void }) {
  return <div className="page-top">{back && <button className="back" onClick={back}><Icon name="arrow" /> กลับ</button>}<div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{children && <div className="page-actions">{children}</div>}</div>;
}

function Classrooms({ role, empty, setEmpty, go }: { role: Role; empty: boolean; setEmpty: (v: boolean) => void; go: (s: Screen) => void }) {
  return <div className="container"><PageTop eyebrow={role === "teacher" ? "INSTRUCTOR SPACE" : "STUDENT SPACE"} title="ห้องเรียนของฉัน" description={role === "teacher" ? "จัดการห้องเรียนและติดตามความก้าวหน้าของนักเรียน" : "เลือกห้องเรียนเพื่อดูโจทย์และความก้าวหน้าของคุณ"}><Button variant="secondary" onClick={() => setEmpty(!empty)}>{empty ? "แสดงตัวอย่าง" : "ดู Empty state"}</Button>{role === "student" ? <Button icon="plus" onClick={() => go("join")}>เข้าร่วมห้องเรียน</Button> : <Button icon="plus" onClick={() => go("create-classroom")}>สร้างห้องเรียน</Button>}</PageTop>
    {empty ? <div className="empty-state"><div className="empty-icon"><Icon name="book" size={34} /></div><h2>ยังไม่มีห้องเรียน</h2><p>{role === "student" ? "เข้าร่วมด้วยโค้ดที่ได้รับจากอาจารย์ แล้วเริ่มทำโจทย์ได้เลย" : "สร้างห้องเรียนแรกเพื่อเริ่มเพิ่มโจทย์และเชิญนักเรียน"}</p><Button icon="plus" onClick={() => go(role === "student" ? "join" : "create-classroom")}>{role === "student" ? "เข้าร่วมห้องเรียน" : "สร้างห้องเรียน"}</Button></div> :
    <div className="class-grid"><ClassCard title="Programming Fundamentals" code="CS101 · Section 1" accent="pink" progress={role === "student" ? 72 : 86} meta={role === "student" ? "8 / 11 problems" : "36 students"} onClick={() => go("classroom")} /><ClassCard title="Data Structures" code="CS202 · Section 2" accent="violet" progress={role === "student" ? 45 : 64} meta={role === "student" ? "5 / 12 problems" : "42 students"} onClick={() => go("classroom")} /><ClassCard title="Algorithm Design" code="CS301 · Section 1" accent="blue" progress={role === "student" ? 20 : 91} meta={role === "student" ? "2 / 10 problems" : "28 students"} onClick={() => go("classroom")} /></div>}
  </div>;
}

function ClassCard({ title, code, accent, progress, meta, onClick }: { title: string; code: string; accent: string; progress: number; meta: string; onClick: () => void }) {
  return <button className="class-card" onClick={onClick}><div className={`class-cover cover-${accent}`}><span><Icon name="code" /></span><small>{code}</small></div><div className="class-body"><h2>{title}</h2><p>ภาคการศึกษา 2/2567</p><div className="progress-row"><span>{meta}</span><strong>{progress}%</strong></div><div className="progress"><i style={{ width: `${progress}%` }} /></div><div className="card-footer"><span>อัปเดตเมื่อ 2 ชั่วโมงที่แล้ว</span><Icon name="chevron" /></div></div></button>;
}

function Join({ go }: { go: (s: Screen) => void }) {
  const [loading, setLoading] = useState(false);
  return <div className="narrow container"><PageTop title="เข้าร่วมห้องเรียน" description="กรอกโค้ด 6 ตัวอักษรที่ได้รับจากอาจารย์" back={() => go("classrooms")} /><div className="panel centered"><div className="join-icon"><Icon name="users" size={30} /></div><label>รหัสเข้าร่วมห้องเรียน<input className="code-input" defaultValue="QST-824" maxLength={7} /></label><p className="hint">ตัวอย่าง: QST-824</p><Button disabled={loading} onClick={() => { setLoading(true); setTimeout(() => go("classroom"), 800); }}>{loading ? <><span className="spinner" /> กำลังเข้าร่วม...</> : "เข้าร่วมห้องเรียน"}</Button></div></div>;
}

function CreateClassroom({ created, setCreated, go }: { created: boolean; setCreated: (v: boolean) => void; go: (s: Screen) => void }) {
  return <div className="narrow container"><PageTop title={created ? "สร้างห้องเรียนสำเร็จ" : "สร้างห้องเรียนใหม่"} description={created ? "แชร์โค้ดนี้ให้นักเรียนเพื่อเข้าร่วมห้องเรียน" : "ตั้งค่าพื้นฐาน คุณสามารถแก้ไขได้ภายหลัง"} back={() => go("classrooms")} />{created ? <div className="panel success-panel"><span className="success-ring"><Icon name="check" size={28} /></span><h2>Programming Fundamentals</h2><p>โค้ดเข้าร่วมของห้องเรียน</p><div className="invite-code">QST-824 <button><Icon name="copy" /></button></div><small>โค้ดนี้ใช้ได้จนกว่าคุณจะสร้างโค้ดใหม่</small><Button onClick={() => go("classroom")}>ไปที่ห้องเรียน</Button></div> : <div className="panel form-panel"><label>ชื่อห้องเรียน<input defaultValue="Programming Fundamentals" /></label><label>รหัสวิชา<input defaultValue="CS101" /></label><div className="two-col"><label>กลุ่มเรียน<input defaultValue="Section 1" /></label><label>ภาคการศึกษา<select defaultValue="2/2567"><option>2/2567</option><option>1/2568</option></select></label></div><label>คำอธิบาย<textarea placeholder="รายละเอียดสั้น ๆ เกี่ยวกับห้องเรียน" /></label><div className="form-actions"><Button variant="secondary" onClick={() => go("classrooms")}>ยกเลิก</Button><Button onClick={() => setCreated(true)}>สร้างห้องเรียน</Button></div></div>}</div>;
}

function Classroom({ role, tab, setTab, go }: { role: Role; tab: string; setTab: (s: string) => void; go: (s: Screen) => void }) {
  const tabs = role === "student" ? ["Problems", "Summary", "Submissions"] : ["Problems", "Summary", "Members"];
  return <div className="container"><div className="crumb"><button onClick={() => go("classrooms")}>ห้องเรียนของฉัน</button><Icon name="chevron" size={14} /><span>Programming Fundamentals</span></div><PageTop eyebrow="CS101 · SECTION 1" title="Programming Fundamentals" description="ภาคการศึกษา 2/2567 · Dr. Narin K.">{role === "teacher" && <><Button variant="secondary" icon="settings" onClick={() => go("class-settings")}>ตั้งค่า</Button><Button icon="sparkles" onClick={() => go("create-problem")}>สร้างโจทย์ด้วย AI</Button></>}</PageTop><div className="tabs">{tabs.map((t) => <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t === "Problems" ? "โจทย์" : t === "Summary" ? "ภาพรวม" : t === "Submissions" ? "ประวัติการส่ง" : "สมาชิก"}</button>)}</div>
    {tab === "Problems" && (role === "student" ? <StudentProblems go={go} /> : <TeacherProblems go={go} />)}
    {tab === "Summary" && <Summary role={role} />}
    {tab === "Submissions" && <SubmissionHistory />}
    {tab === "Members" && <Members />}
  </div>;
}

function StudentProblems({ go }: { go: (s: Screen) => void }) {
  return <><div className="stats-strip"><Stat label="โจทย์ทั้งหมด" value="11" icon="code" /><Stat label="ผ่านแล้ว" value="8" icon="check" /><Stat label="คะแนนรวม" value="720 / 1,000" icon="chart" /><Stat label="ส่งตรงเวลา" value="100%" icon="clock" /></div><div className="section-head"><div><h2>โจทย์ทั้งหมด</h2><p>ทำโจทย์เพื่อสะสมคะแนนและพัฒนาทักษะ</p></div><div className="search"><Icon name="search" /><input placeholder="ค้นหาโจทย์" /></div></div><div className="problem-list">{problems.map((p) => <button className="problem-row" key={p.id} onClick={() => go("solve")}><span className="problem-number">{String(p.id).padStart(2, "0")}</span><span className="problem-name"><strong>{p.title}</strong><small>{p.slug}</small></span><Difficulty value={p.difficulty} /><span className="deadline"><Icon name="clock" size={15} />{p.due}</span><Badge tone={p.status === "Passed" ? "success" : p.status === "In progress" ? "warning" : "neutral"}>{p.status}</Badge><Icon name="chevron" /></button>)}</div></>;
}

function TeacherProblems({ go }: { go: (s: Screen) => void }) {
  return <><div className="stats-strip"><Stat label="โจทย์ที่เผยแพร่" value="11" icon="code" /><Stat label="อัตราส่งงาน" value="78%" icon="send" /><Stat label="ผ่านเฉลี่ย" value="71%" icon="chart" /><Stat label="นักเรียน" value="36" icon="users" /></div><div className="section-head"><div><h2>โจทย์ทั้งหมด</h2><p>ติดตามการส่งและผลลัพธ์ของนักเรียน</p></div><Button icon="plus" onClick={() => go("create-problem")}>เพิ่มโจทย์</Button></div><div className="table-card"><table><thead><tr><th>โจทย์</th><th>ระดับ</th><th>กำหนดส่ง</th><th>ส่งแล้ว</th><th>ผ่าน</th><th>สถานะ</th><th /></tr></thead><tbody>{problems.map((p) => <tr key={p.id}><td><strong>{p.title}</strong><small>{p.slug}</small></td><td><Difficulty value={p.difficulty} /></td><td>{p.due}</td><td>{p.solved}/{p.total}</td><td><div className="mini-progress"><i style={{ width: `${p.solved / p.total * 100}%` }} /></div></td><td><Badge tone="success">Published</Badge></td><td><button className="icon-btn" onClick={() => go("results")}><Icon name="more" /></button></td></tr>)}</tbody></table></div></>;
}

function Difficulty({ value }: { value: string }) {
  return <Badge tone={value === "Easy" ? "success" : value === "Hard" ? "danger" : "warning"}>{value}</Badge>;
}

function Stat({ label, value, icon }: { label: string; value: string; icon: IconName }) {
  return <div className="stat"><span><Icon name={icon} /></span><div><small>{label}</small><strong>{value}</strong></div></div>;
}

function Summary({ role }: { role: Role }) {
  return <div className="summary-grid"><div className="panel chart-panel"><div className="section-head"><div><h2>{role === "student" ? "ความก้าวหน้าของฉัน" : "อัตราการส่งงาน"}</h2><p>6 สัปดาห์ล่าสุด</p></div><Badge tone="pink">+12% จากสัปดาห์ก่อน</Badge></div><div className="bar-chart">{[35, 52, 47, 68, 72, 86].map((h, i) => <div key={i}><span style={{ height: `${h}%` }} /><small>W{i + 1}</small></div>)}</div></div><div className="panel"><h2>สรุปผลการเรียน</h2><div className="donut"><div><strong>{role === "student" ? "72%" : "78%"}</strong><small>สำเร็จ</small></div></div><div className="legend"><span><i className="green" />ผ่านแล้ว <strong>8</strong></span><span><i className="yellow" />กำลังทำ <strong>1</strong></span><span><i className="gray" />ยังไม่เริ่ม <strong>2</strong></span></div></div><div className="panel activity-panel"><h2>กิจกรรมล่าสุด</h2>{["Araya ส่งโจทย์ Two Sum สำเร็จ", "เผยแพร่โจทย์ Valid Parentheses", "อัปเดตคะแนนเมื่อวานนี้"].map((x, i) => <div className="activity" key={x}><span><Icon name={i === 0 ? "check" : i === 1 ? "send" : "chart"} /></span><div><strong>{x}</strong><small>{i === 0 ? "12 นาทีที่แล้ว" : i === 1 ? "2 ชั่วโมงที่แล้ว" : "1 วันที่แล้ว"}</small></div></div>)}</div></div>;
}

function SubmissionHistory() {
  return <div className="table-card top-space"><table><thead><tr><th>โจทย์</th><th>เวลาที่ส่ง</th><th>ผลลัพธ์</th><th>คะแนน</th><th>ภาษา</th></tr></thead><tbody>{problems.slice(0, 3).map((p, i) => <tr key={p.id}><td><strong>{p.title}</strong></td><td>{8 + i} May, {14 + i}:32</td><td><Badge tone={i === 1 ? "warning" : "success"}>{i === 1 ? "Partial" : "All passed"}</Badge></td><td><strong>{i === 1 ? "70" : "100"}/100</strong></td><td>Python 3.11</td></tr>)}</tbody></table></div>;
}

function Members() {
  return <div className="table-card top-space"><div className="table-toolbar"><div><h2>สมาชิกในห้องเรียน</h2><p>นักเรียน 36 คน · อาจารย์ 2 คน</p></div><Button variant="secondary" icon="plus">เชิญสมาชิก</Button></div><table><thead><tr><th>ชื่อ</th><th>รหัสนักศึกษา</th><th>อีเมล</th><th>บทบาท</th><th>เข้าร่วมเมื่อ</th></tr></thead><tbody>{students.slice(0, 4).map((s, i) => <tr key={s[0]}><td><div className="member"><span className="avatar">{s[1].slice(0, 2)}</span><strong>{s[1]}</strong></div></td><td>{s[0]}</td><td>student{i + 1}@kmitl.ac.th</td><td><Badge tone="blue">Student</Badge></td><td>4 May 2025</td></tr>)}</tbody></table></div>;
}

function Solve({ result, setResult, go }: { result: string; setResult: (v: "idle" | "passed" | "partial" | "error") => void; go: (s: Screen) => void }) {
  const [code, setCode] = useState("def two_sum(nums, target):\n    # Write your solution here\n    seen = {}\n    for i, num in enumerate(nums):\n        if target - num in seen:\n            return [seen[target - num], i]\n        seen[num] = i");
  return <div className="solve-page"><div className="solve-top"><button className="back" onClick={() => go("classroom")}><Icon name="arrow" /> กลับไปที่โจทย์</button><div><strong>Two Sum</strong><Difficulty value="Easy" /></div><select><option>Python 3.11</option><option>JavaScript</option></select></div><div className="solve-grid"><section className="problem-description"><Badge tone="pink">ARRAY & HASH MAP</Badge><h1>Two Sum</h1><p>กำหนดอาร์เรย์ของจำนวนเต็ม <code>nums</code> และจำนวนเต็ม <code>target</code> ให้คืนค่า index ของจำนวนสองตัวที่รวมกันแล้วเท่ากับ target</p><h3>ตัวอย่าง</h3><pre>Input: nums = [2,7,11,15], target = 9{"\n"}Output: [0,1]</pre><h3>ข้อกำหนด</h3><ul><li>2 ≤ nums.length ≤ 10⁴</li><li>มีคำตอบที่ถูกต้องเพียงหนึ่งคำตอบ</li><li>ห้ามใช้สมาชิกตัวเดิมซ้ำ</li></ul><div className="problem-meta"><span><Icon name="clock" /> กำหนดส่ง 12 May, 23:59</span><span>100 คะแนน</span></div></section><section className="editor-pane"><div className="editor-head"><span>solution.py</span><small>Saved</small></div><div className="editor"><div className="line-numbers">{code.split("\n").map((_, i) => <span key={i}>{i + 1}</span>)}</div><textarea value={code} onChange={(e) => setCode(e.target.value)} spellCheck={false} /></div><div className="console"><div className="console-tabs"><strong>ผลการทดสอบ</strong><button onClick={() => setResult("error")}>จำลอง error</button></div>{result === "idle" ? <div className="console-empty"><Icon name="play" /><p>กด Run เพื่อทดสอบโค้ดของคุณ</p></div> : <TestResult result={result} />}</div><div className="editor-actions"><Button variant="secondary" icon="play" onClick={() => setResult("partial")}>Run</Button><Button variant="secondary" icon="check" onClick={() => setResult("passed")}>Test</Button><Button icon="send" onClick={() => setResult("passed")}>Submit</Button></div></section></div></div>;
}

function TestResult({ result }: { result: string }) {
  const passed = result === "passed";
  const error = result === "error";
  return <div className={`test-result ${passed ? "test-passed" : error ? "test-error" : "test-partial"}`}><div className="result-title"><span><Icon name={passed ? "check" : "x"} /></span><div><strong>{passed ? "ผ่านทุก Test case" : error ? "Runtime Error" : "ผ่านบางส่วน"}</strong><small>{passed ? "10 / 10 test cases passed · 100 คะแนน" : error ? "NameError on line 4" : "7 / 10 test cases passed · 70 คะแนน"}</small></div></div><div className="case-dots">{Array.from({ length: 10 }).map((_, i) => <i key={i} className={passed || (!error && i < 7) ? "pass" : "fail"} />)}</div></div>;
}

function Results({ go }: { go: (s: Screen) => void }) {
  const [selected, setSelected] = useState(0);
  return <div className="container"><PageTop eyebrow="ASSIGNMENT RESULTS" title="Two Sum" description="ดูผลการส่งและโค้ดของนักเรียนแต่ละคน" back={() => go("classroom")}><Button variant="secondary" icon="upload">ส่งออก CSV</Button></PageTop><div className="stats-strip"><Stat label="ส่งแล้ว" value="32 / 36" icon="send" /><Stat label="ผ่านทั้งหมด" value="24" icon="check" /><Stat label="คะแนนเฉลี่ย" value="84.2" icon="chart" /><Stat label="ยังไม่ส่ง" value="4" icon="clock" /></div><div className="results-layout"><div className="table-card"><table><thead><tr><th>นักเรียน</th><th>ผลลัพธ์</th><th>คะแนน</th><th>ส่งล่าสุด</th></tr></thead><tbody>{students.map((s, i) => <tr key={s[0]} className={selected === i ? "selected-row" : ""} onClick={() => setSelected(i)}><td><strong>{s[1]}</strong><small>{s[0]}</small></td><td><Badge tone={s[2] === "Passed" ? "success" : s[2] === "Pending" ? "warning" : "danger"}>{s[2]}</Badge></td><td>{s[3]}</td><td>{s[4]}</td></tr>)}</tbody></table></div><aside className="code-panel"><div className="code-panel-head"><div><small>SUBMISSION</small><h2>{students[selected][1]}</h2><p>{students[selected][0]} · Python 3.11</p></div><button className="icon-btn"><Icon name="x" /></button></div><div className="score-line"><Badge tone={selected === 0 || selected === 2 ? "success" : "warning"}>{students[selected][2]}</Badge><strong>{students[selected][3]} คะแนน</strong></div><pre className="code-preview"><code>def two_sum(nums, target):{"\n"}    seen = {"{}"}{"\n"}    for i, num in enumerate(nums):{"\n"}        diff = target - num{"\n"}        if diff in seen:{"\n"}            return [seen[diff], i]{"\n"}        seen[num] = i</code></pre><h3>Test cases</h3><div className="case-dots">{Array.from({ length: 10 }).map((_, i) => <i key={i} className={i < (selected === 1 ? 7 : 10) ? "pass" : "fail"} />)}</div><label>ความคิดเห็นถึงนักเรียน<textarea placeholder="เพิ่มความคิดเห็น..." /></label><Button>บันทึกความคิดเห็น</Button></aside></div></div>;
}

function CreateProblem({ go }: { go: (s: Screen) => void }) {
  const [stage, setStage] = useState<"prompt" | "draft" | "review" | "published">("prompt");
  const [step, setStep] = useState(1);
  const steps = ["แก้ไขโจทย์", "Test cases", "ตั้งค่า", "เลือกห้องเรียน"];
  if (stage === "published") return <div className="narrow container"><div className="panel success-panel publish-success"><span className="success-ring"><Icon name="check" size={28} /></span><h1>เผยแพร่โจทย์สำเร็จ</h1><p>โจทย์ “Temperature Converter” พร้อมให้นักเรียนทำแล้ว</p><Button onClick={() => go("classroom")}>กลับไปที่ห้องเรียน</Button></div></div>;
  return <div className="container"><PageTop eyebrow="AI PROBLEM CREATOR" title={stage === "prompt" ? "สร้างโจทย์ด้วย AI" : "ตรวจสอบและเผยแพร่โจทย์"} description={stage === "prompt" ? "อธิบายโจทย์ที่ต้องการ แล้วให้ Questly ช่วยสร้างร่างแรก" : "แก้ไขรายละเอียดและทดสอบก่อนเผยแพร่"} back={() => stage === "prompt" ? go("classroom") : setStage("prompt")} />
    {stage === "prompt" ? <div className="ai-layout"><div className="panel ai-form"><label>อยากสร้างโจทย์เกี่ยวกับอะไร?<textarea defaultValue="สร้างโจทย์เรื่องการแปลงอุณหภูมิจาก Celsius เป็น Fahrenheit สำหรับนักศึกษาปี 1 เน้นการใช้ฟังก์ชันและ floating point" rows={6} /></label><div className="two-col"><label>ระดับความยาก<select><option>Easy</option><option>Medium</option><option>Hard</option></select></label><label>ภาษาที่รองรับ<select><option>ทุกภาษา</option><option>Python</option></select></label></div><label>ใช้เอกสารอ้างอิง<select><option>Lecture 03 — Functions.pdf</option><option>ไม่ใช้เอกสาร</option></select></label><Button icon="sparkles" onClick={() => setStage("draft")}>สร้างร่างโจทย์</Button></div><aside className="ai-tip"><span><Icon name="sparkles" /></span><h3>เขียน prompt อย่างไรให้ได้ผลดี?</h3><ul><li>ระบุหัวข้อและระดับผู้เรียน</li><li>บอกแนวคิดที่ต้องการทดสอบ</li><li>กำหนดรูปแบบ input/output</li></ul><button className="text-link" onClick={() => go("documents")}>จัดการเอกสารอ้างอิง</button></aside></div> :
    <><div className="stepper">{steps.map((s, i) => <div className={step === i + 1 ? "current" : step > i + 1 ? "done" : ""} key={s}><span>{step > i + 1 ? <Icon name="check" size={14} /> : i + 1}</span><small>{s}</small></div>)}</div><div className="panel review-panel">{step === 1 && <><div className="review-label"><Badge tone="pink">AI GENERATED DRAFT</Badge><small>แก้ไขได้ทุกส่วนก่อนเผยแพร่</small></div><label>ชื่อโจทย์<input defaultValue="Temperature Converter" /></label><label>คำอธิบาย<textarea rows={6} defaultValue={"เขียนฟังก์ชัน convert_temperature ที่รับค่าอุณหภูมิในหน่วย Celsius และคืนค่าในหน่วย Fahrenheit\n\nใช้สูตร: F = (C × 9/5) + 32"} /></label><div className="two-col"><label>Input format<input defaultValue="จำนวนจริง C หนึ่งจำนวน" /></label><label>Output format<input defaultValue="อุณหภูมิ F ทศนิยม 2 ตำแหน่ง" /></label></div></>}{step === 2 && <><h2>Test cases</h2><p>ตรวจสอบและเพิ่มกรณีทดสอบสำหรับโจทย์</p>{[["0", "32.00"], ["100", "212.00"], ["-40", "-40.00"]].map((c, i) => <div className="test-case" key={i}><strong>Case {i + 1}</strong><label>Input<input defaultValue={c[0]} /></label><label>Expected output<input defaultValue={c[1]} /></label><Badge tone="success">Valid</Badge></div>)}<Button variant="secondary" icon="plus">เพิ่ม Test case</Button></>}{step === 3 && <><h2>ตั้งค่าโจทย์</h2><div className="two-col"><label>คะแนนเต็ม<input type="number" defaultValue="100" /></label><label>กำหนดส่ง<input type="date" defaultValue="2025-05-30" /></label><label>ระดับ<select><option>Easy</option></select></label><label>สถานะ<select><option>Publish immediately</option><option>Draft</option></select></label></div><label className="toggle-row"><span><strong>แสดง Test cases ตัวอย่าง</strong><small>นักเรียนจะเห็นตัวอย่าง 2 กรณี</small></span><input type="checkbox" defaultChecked /></label></>}{step === 4 && <><h2>เลือกห้องเรียนที่จะเผยแพร่</h2><p>โจทย์จะถูกเพิ่มไปยังห้องเรียนที่เลือก</p>{["Programming Fundamentals · Section 1", "Programming Fundamentals · Section 2", "Algorithm Design · Section 1"].map((c, i) => <label className="class-check" key={c}><input type="checkbox" defaultChecked={i === 0} /><span><Icon name="book" /><strong>{c}</strong></span></label>)}</>}</div><div className="review-actions"><Button variant="secondary" onClick={() => step === 1 ? setStage("prompt") : setStep(step - 1)}>ย้อนกลับ</Button><Button icon={step === 4 ? "send" : undefined} onClick={() => step === 4 ? setStage("published") : setStep(step + 1)}>{step === 4 ? "เผยแพร่โจทย์" : "ถัดไป"}</Button></div></>}</div>;
}

function Documents({ go }: { go: (s: Screen) => void }) {
  const [loading, setLoading] = useState(false);
  return <div className="container"><PageTop eyebrow="AI KNOWLEDGE BASE" title="เอกสารของฉัน" description="อัปโหลดเอกสารประกอบการสอนเพื่อให้ AI ใช้สร้างโจทย์" back={() => go("classroom")}><Button icon="upload" onClick={() => { setLoading(true); setTimeout(() => setLoading(false), 1200); }}>อัปโหลด PDF</Button></PageTop><div className="upload-zone"><Icon name="upload" size={28} /><strong>{loading ? "กำลังอัปโหลดเอกสาร..." : "ลากไฟล์ PDF มาวางที่นี่"}</strong><p>หรือคลิกปุ่มอัปโหลด · สูงสุด 25 MB ต่อไฟล์</p>{loading && <div className="loading-line"><i /></div>}</div><div className="section-head"><div><h2>เอกสารทั้งหมด</h2><p>3 ไฟล์ · ใช้พื้นที่ 12.4 MB</p></div></div><div className="document-list">{["Lecture 03 — Functions.pdf", "Data Structures Handbook.pdf", "Python Lab Exercises.pdf"].map((d, i) => <div className="document" key={d}><span><Icon name="file" /></span><div><strong>{d}</strong><small>{[4.2, 6.8, 1.4][i]} MB · อัปโหลด {i + 2} วันที่แล้ว</small></div><Badge tone={i === 1 ? "warning" : "success"}>{i === 1 ? "Processing" : "Ready"}</Badge><button className="icon-btn"><Icon name="more" /></button></div>)}</div></div>;
}

function ClassSettings({ go }: { go: (s: Screen) => void }) {
  const [archived, setArchived] = useState(false);
  return <div className="container settings-width"><PageTop title="ตั้งค่าห้องเรียน" description="จัดการข้อมูลและการเข้าถึงห้องเรียน" back={() => go("classroom")} /><div className="settings-nav"><button className="active">ทั่วไป</button><button>การแจ้งเตือน</button><button>สิทธิ์การเข้าถึง</button></div><div className="panel form-panel"><h2>ข้อมูลห้องเรียน</h2><label>ชื่อห้องเรียน<input defaultValue="Programming Fundamentals" /></label><div className="two-col"><label>รหัสวิชา<input defaultValue="CS101" /></label><label>กลุ่มเรียน<input defaultValue="Section 1" /></label></div><div className="form-actions"><Button>บันทึกการเปลี่ยนแปลง</Button></div></div><div className="panel invite-settings"><div><h2>โค้ดเข้าร่วม</h2><p>นักเรียนใช้โค้ดนี้เพื่อเข้าร่วมห้องเรียน</p></div><div className="invite-code small">QST-824 <button><Icon name="copy" /></button></div><Button variant="secondary">สร้างโค้ดใหม่</Button></div><div className="panel danger-zone"><div><h2>Archive classroom</h2><p>ซ่อนห้องเรียนจากหน้าหลัก ข้อมูลทั้งหมดจะยังคงอยู่</p></div><Button variant="danger" onClick={() => setArchived(true)}>{archived ? "Archived" : "Archive classroom"}</Button></div></div>;
}

function Admin() {
  const [tab, setTab] = useState("Users");
  return <div className="container"><PageTop eyebrow="ADMIN CONSOLE" title="การตั้งค่าระบบ" description="จัดการผู้ใช้ AI และตรวจสอบสถานะของ Questly" /><div className="admin-layout"><nav className="admin-nav">{[["Users", "users", "ผู้ใช้งาน"], ["AI", "sparkles", "AI & Quota"], ["System", "chart", "สถานะระบบ"]].map(([id, icon, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon name={icon as IconName} />{label}</button>)}</nav><section className="admin-content">{tab === "Users" && <AdminUsers />}{tab === "AI" && <AdminAI />}{tab === "System" && <SystemStatus />}</section></div></div>;
}

function AdminUsers() {
  const [requests, setRequests] = useState([["Dr. Ploy S.", "ploy.s@kmitl.ac.th"], ["Asst. Prof. Kavin R.", "kavin.r@kmitl.ac.th"]]);
  return <><div className="section-head"><div><h2>คำขอสิทธิ์อาจารย์</h2><p>ตรวจสอบและอนุมัติคำขอที่รอดำเนินการ</p></div><Badge tone="warning">{requests.length} pending</Badge></div>{requests.map((r, i) => <div className="request-card" key={r[1]}><span className="avatar">{r[0].slice(0, 2)}</span><div><strong>{r[0]}</strong><small>{r[1]} · ส่งคำขอเมื่อ {i + 1} วันที่แล้ว</small></div><Button variant="secondary" onClick={() => setRequests(requests.filter((_, n) => n !== i))}>ปฏิเสธ</Button><Button onClick={() => setRequests(requests.filter((_, n) => n !== i))}>อนุมัติ</Button></div>)}{requests.length === 0 && <div className="mini-empty"><Icon name="check" /><span>ดำเนินการครบทุกคำขอแล้ว</span></div>}<div className="section-head users-head"><div><h2>ผู้ใช้ทั้งหมด</h2><p>1,248 บัญชีในระบบ</p></div><div className="search"><Icon name="search" /><input placeholder="ค้นหาผู้ใช้" /></div></div><div className="table-card"><table><thead><tr><th>ผู้ใช้</th><th>บทบาท</th><th>สถานะ</th><th>เข้าร่วมเมื่อ</th><th /></tr></thead><tbody>{[["Araya S.", "Student"], ["Dr. Narin K.", "Instructor"], ["Napat K.", "Student"], ["Pimchanok T.", "Student"]].map((u, i) => <tr key={u[0]}><td><div className="member"><span className="avatar">{u[0].slice(0, 2)}</span><span><strong>{u[0]}</strong><small>user{i + 1}@kmitl.ac.th</small></span></div></td><td><Badge tone={u[1] === "Instructor" ? "pink" : "blue"}>{u[1]}</Badge></td><td><Badge tone="success">Active</Badge></td><td>{4 + i} May 2025</td><td><Icon name="more" /></td></tr>)}</tbody></table></div></>;
}

function AdminAI() {
  return <><div className="section-head"><div><h2>โมเดลและการใช้งาน AI</h2><p>กำหนดโมเดลหลักและข้อจำกัดของระบบ</p></div><Button>บันทึกการตั้งค่า</Button></div><div className="panel form-panel"><label>โมเดลเริ่มต้น<select defaultValue="GPT-4.1"><option>GPT-4.1</option><option>Claude Sonnet 4</option><option>Gemini 2.5 Pro</option></select></label><div className="two-col"><label>Quota ต่ออาจารย์ / เดือน<input type="number" defaultValue="100" /></label><label>Token limit ต่อคำขอ<input type="number" defaultValue="16000" /></label></div><h3>ความสามารถ</h3>{[["AI problem generation", "ให้อาจารย์สร้างโจทย์จาก prompt"], ["Document grounding", "ใช้เนื้อหาจาก PDF เป็นบริบท"], ["Automatic test cases", "สร้าง Test cases อัตโนมัติ"]].map((x) => <label className="toggle-row" key={x[0]}><span><strong>{x[0]}</strong><small>{x[1]}</small></span><input type="checkbox" defaultChecked /></label>)}</div><div className="panel quota-card"><div><small>การใช้งานเดือนนี้</small><strong>48,920 / 100,000</strong></div><div className="progress"><i style={{ width: "49%" }} /></div><p>รีเซ็ตในอีก 12 วัน · ประมาณการสิ้นเดือน 78%</p></div></>;
}

function SystemStatus() {
  const services = [["Web application", "Operational", "99.99%"], ["Judge service", "Operational", "99.97%"], ["AI generation", "Degraded", "98.42%"], ["Email delivery", "Operational", "99.95%"], ["Database", "Operational", "99.99%"]];
  return <><div className="status-banner"><span><Icon name="shield" /></span><div><strong>ระบบโดยรวมทำงานเป็นปกติ</strong><p>มี 1 บริการที่ประสิทธิภาพลดลงเล็กน้อย</p></div><Badge tone="success">All systems online</Badge></div><div className="section-head"><div><h2>สถานะบริการ</h2><p>อัปเดตล่าสุดเมื่อไม่กี่วินาทีที่ผ่านมา</p></div><Button variant="secondary">รีเฟรช</Button></div><div className="service-list">{services.map((s) => <div className="service" key={s[0]}><span className={s[1] === "Degraded" ? "dot warning-dot" : "dot"} /><strong>{s[0]}</strong><Badge tone={s[1] === "Degraded" ? "warning" : "success"}>{s[1]}</Badge><span>{s[2]} uptime</span><Icon name="chevron" /></div>)}</div><div className="panel incident"><h2>เหตุการณ์ล่าสุด</h2><div><span>10 May</span><p><strong>AI response latency increased</strong><br />แก้ไขแล้วภายใน 18 นาที ไม่มีข้อมูลสูญหาย</p><Badge tone="success">Resolved</Badge></div></div></>;
}
