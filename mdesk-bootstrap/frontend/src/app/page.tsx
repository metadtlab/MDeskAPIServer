import Link from "next/link";

export default function HomePage() {
  return (
    <section className="rounded-2xl border border-emerald-100 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">MDesk Migration Starter</h1>
      <p className="mt-2 text-slate-600">Django 템플릿에서 Next.js로 전환하는 초기 화면입니다.</p>
      <div className="mt-6 flex gap-3">
        <Link href="/login" className="rounded-lg bg-brand-700 px-4 py-2 text-white">로그인</Link>
        <Link href="/work" className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700">작업 페이지</Link>
      </div>
    </section>
  );
}
