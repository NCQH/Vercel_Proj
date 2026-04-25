"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Menu,
  LogOut,
  MessageSquare,
  BookOpen,
  BarChart3,
  FileText,
  Home,
} from "lucide-react";

interface MainLayoutProps {
  role: "student" | "lecturer";
  children: React.ReactNode;
}

const navGroups = {
  student: [
    { label: "Chat", href: "/student/chat", icon: MessageSquare },
    { label: "Roadmap", href: "/student/roadmap", icon: BookOpen },
  ],
  lecturer: [
    { label: "Dashboard", href: "/lecturer/dashboard", icon: BarChart3 },
    { label: "Materials", href: "/lecturer/materials", icon: FileText },
  ],
};

const roleLabel = {
  student: "Student",
  lecturer: "Lecturer",
};

export default function MainLayout({ role, children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="relative flex min-h-screen overflow-hidden">
        <aside className="hidden w-72 shrink-0 flex-col border-r border-slate-200 bg-white px-6 py-8 lg:flex">
          <div className="mb-10 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-3xl bg-brand-600 text-white shadow-soft">
              <Home className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
                AI Teaching Assistant
              </p>
              <h2 className="text-lg font-semibold text-slate-900">
                {roleLabel[role]} Console
              </h2>
            </div>
          </div>

          <nav className="space-y-2">
            {navGroups[role].map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-center gap-3 rounded-3xl px-4 py-3 text-sm font-medium transition ${
                    active
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto rounded-3xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
            <p className="font-semibold text-slate-900">Need help?</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Use the chat for quick subject guidance or check roadmap topics
              for your next review session.
            </p>
          </div>
        </aside>

        <div className="flex flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur-xl">
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm lg:hidden"
                >
                  <Menu className="h-5 w-5" />
                </button>
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    {roleLabel[role]} experience
                  </p>
                  <p className="text-2xl font-semibold text-slate-900">
                    Focused learning flow
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button className="hidden rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-700 transition hover:bg-slate-200 lg:inline-flex">
                  Courses
                </button>
                <button className="inline-flex items-center gap-2 rounded-2xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700">
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </div>
            </div>
          </header>

          <div className="flex flex-1 overflow-hidden">
            <div className="relative flex flex-1 flex-col overflow-hidden">
              <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
                {children}
              </main>
            </div>
          </div>
        </div>

        {sidebarOpen ? (
          <div
            className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}

        <aside
          className={`fixed inset-y-0 left-0 z-40 w-72 overflow-y-auto border-r border-slate-200 bg-white px-6 py-8 transition-all duration-300 lg:hidden ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
        >
          <div className="mb-10 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-3xl bg-brand-600 text-white shadow-soft">
              <Home className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
                AI Teaching Assistant
              </p>
              <h2 className="text-lg font-semibold text-slate-900">
                {roleLabel[role]} Console
              </h2>
            </div>
          </div>
          <nav className="space-y-2">
            {navGroups[role].map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-center gap-3 rounded-3xl px-4 py-3 text-sm font-medium transition ${
                    active
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
      </div>
    </div>
  );
}
