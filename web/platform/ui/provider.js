/** Provider selection for Phase 6B. Real mode uses the shared Core API and a bearer token. */
import {CoreApiClient} from "/student/core-api.js";
import {ensureTelegramAuth, storedToken, clearStoredToken} from "/platform/ui/auth-bootstrap.js";
const params=new URLSearchParams(location.search);
// Product dashboards must never present fabricated business metrics. Use the
// Core API whenever a session exists; without one, fail closed with an auth
// state instead of silently falling back to mock data.
let useReal=params.get("provider")==="real" || Boolean(storedToken());
const realClient=new CoreApiClient();
const token=storedToken();
if(token) realClient.setSession({token});
let authPromise;
let reauthPromise;
async function ensureSession(force=false){
  if(!force && realClient.session?.token) return;
  if(force){
    if (reauthPromise) return reauthPromise;
    clearStoredToken(); realClient.setSession(null); authPromise=null;
    reauthPromise = (async () => { const auth=await ensureTelegramAuth(); realClient.setSession({token:auth.token}); useReal=true; return auth; })();
    try { await reauthPromise; } finally { reauthPromise=null; }
    return;
  }
  authPromise ||= ensureTelegramAuth(); const auth=await authPromise; realClient.setSession({token:auth.token}); useReal=true;
}
async function request(path, options={}, retried=false) { await ensureSession(); try { return await realClient.request(path, options); } catch (error) { if(error.status!==401 || retried) throw error; await ensureSession(true); return request(path, options, true); } }
export const platformProvider={
  get mode(){ return useReal?"real":"unavailable" },
  async adminDashboard(){
    await ensureSession();
    const [schools, users, students, classrooms, activity, content, usage] = await Promise.all([
      request("/admin/schools"), request("/admin/users"), request("/admin/students"), request("/admin/classrooms"), request("/admin/activity"), request("/admin/content"), request("/admin/observability/overview")
    ]);
    return {schools: schools.items||[], users: users.items||[], students: students.items||[], classrooms: classrooms.items||[], activity, content: content.items||[], usage};
  },
  async dashboard(role="student"){
    await ensureSession();
    if(!useReal) throw new Error("برای مشاهده داشبورد، ابتدا وارد حساب کاربری شوید.");
    if(role==="teacher"){
      const [classrooms,analytics]=await Promise.all([
        request("/teacher/classrooms"),
        request("/teacher/dashboard/analytics"),
      ]);
      return {
        name:analytics.teacher?.name||"معلم",
        classes:classrooms.total_classrooms||0,
        students:analytics.total_students||0,
        submissions:analytics.pending_submissions||0,
        items:(analytics.students_requiring_attention||[]).map(item=>({title:item.name||"نیازمند پیگیری",meta:item.reason||"بازبینی وضعیت یادگیری",status:"بازبینی"})),
      };
    }
    const [dashboard,progress,assignments]=await Promise.all([
      request("/student/dashboard"),
      request("/student/progress"),
      request("/student/v1/assignments"),
    ]);
    return {name:dashboard.student?.username||"دانش‌آموز",progress:dashboard.summary_metrics?.overall_readiness_pct||0,streak:dashboard.summary_metrics?.streak_days??null,assignments:(assignments.assignments||[]).map(a=>({title:a.title,meta:a.due_at?`تا ${a.due_at}`:"تکلیف فعال",icon:"✓",status:a.status})),courses:Object.entries(progress.subject_mastery||{}).map(([name,v])=>({name,value:v.mastery_score_pct||0}))};
  },
  async tutorAnswer(query, context={}){
    await ensureSession();
    if(!useReal) throw new Error("برای استفاده از دستیار، ابتدا وارد حساب کاربری شوید.");
    return request("/tutor/answer",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query,context})});
  },
  async profile(){
    await ensureSession();
    if(!useReal) throw new Error("برای مشاهده پروفایل، ابتدا وارد حساب کاربری شوید.");
    return request("/student/profile");
  },
  async assignments(){
    await ensureSession();
    if(!useReal) throw new Error("برای مشاهده تکالیف، ابتدا وارد حساب کاربری شوید.");
    return request("/student/v1/assignments");
  }
};

