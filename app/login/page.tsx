"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
// Đã thay ChalkboardTeacher bằng Presentation
import { User, Presentation } from "lucide-react";

const roleCards = [
  {
    id: "student",
    title: "Student",
    description:
      "Ask questions, review citations, and follow your personalized study roadmap.",
    icon: User,
    href: "/student/chat",
  },
  {
    id: "lecturer",
    title: "Lecturer",
    description:
      "Manage materials, monitor class gaps, and review analytics at a glance.",
    icon: Presentation, // Cập nhật icon ở đây
    href: "/lecturer/dashboard",
  },
];

export default function LoginPage() {
  const [selectedRole, setSelectedRole] = useState("student");

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-10 rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft sm:p-12">
        <div className="space-y-4 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-brand-600">
            Mock authentication
          </p>
          <h1 className="text-4xl font-semibold text-slate-900">
            Login to AI Teaching Assistant
          </h1>
          <p className="mx-auto max-w-2xl text-base leading-7 text-slate-600">
            Select your role and continue. This mock login routes you directly
            to the student or lecturer experience.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {roleCards.map((card) => {
            const Icon = card.icon;
            const isSelected = selectedRole === card.id;

            return (
              <button
                key={card.id}
                type="button"
                onClick={() => setSelectedRole(card.id)}
                className={`group flex flex-col gap-4 rounded-3xl border px-6 py-7 text-left transition ${
                  isSelected
                    ? "border-brand-500 bg-brand-50 shadow-soft"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700">
                  <Icon className="h-6 w-6" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    {card.title}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {card.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-slate-500">Selected role:</p>
            <p className="text-lg font-semibold text-slate-900">
              {selectedRole === "student" ? "Student" : "Lecturer"}
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              signIn("google", {
                callbackUrl: selectedRole === "student" ? "/student/chat" : "/lecturer/dashboard",
              })
            }
            className="inline-flex items-center justify-center rounded-3xl bg-red-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-red-700"
          >
            <svg className="mr-2 h-4 w-4 fill-current" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    </main>
  );
}
