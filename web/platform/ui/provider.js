/** Provider selection for Phase 6B. Real mode uses the shared Core API and a bearer token. */
import {CoreApiClient} from "/student/core-api.js";
const params=new URLSearchParams(location.search);
// Product dashboards must never present fabricated business metrics. Use the
// Core API whenever a session exists; without one, fail closed with an auth
// state instead of silently falling back to mock data.
const useReal=params.get("provider")==="real" || Boolean(sessionStorage.getItem("studentToken")||sessionStorage.getItem("teacherToken")||sessionStorage.getItem("accessToken"));
const realClient=new CoreApiClient();
const token=sessionStorage.getItem("studentToken")||sessionStorage.getItem("teacherToken")||sessionStorage.getItem("accessToken");
if(token) realClient.setSession({token});
export const platformProvider={
  mode:useReal?"real":"unavailable",
  async dashboard(role="student"){
    if(!useReal) throw new Error("برای مشاهده داشبورد، ابتدا وارد حساب کاربری شوید.");
    if(role==="teacher"){
      const [classrooms,analytics]=await Promise.all([
        realClient.request("/teacher/classrooms"),
        realClient.request("/teacher/dashboard/analytics"),
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
      realClient.request("/student/dashboard"),
      realClient.request("/student/progress"),
      realClient.request("/student/v1/assignments"),
    ]);
    return {name:dashboard.student?.username||"دانش‌آموز",progress:dashboard.summary_metrics?.overall_readiness_pct||0,streak:dashboard.summary_metrics?.streak_days??null,assignments:(assignments.assignments||[]).map(a=>({title:a.title,meta:a.due_at?`تا ${a.due_at}`:"تکلیف فعال",icon:"✓",status:a.status})),courses:Object.entries(progress.subject_mastery||{}).map(([name,v])=>({name,value:v.mastery_score_pct||0}))};
  },
  async tutorAnswer(query, context={}){
    if(!useReal) throw new Error("برای استفاده از دستیار، ابتدا وارد حساب کاربری شوید.");
    return realClient.request("/tutor/answer",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query,context})});
  },
  async profile(){
    if(!useReal) throw new Error("برای مشاهده پروفایل، ابتدا وارد حساب کاربری شوید.");
    return realClient.request("/student/profile");
  },
  async assignments(){
    if(!useReal) throw new Error("برای مشاهده تکالیف، ابتدا وارد حساب کاربری شوید.");
    return realClient.request("/student/v1/assignments");
  }
};


