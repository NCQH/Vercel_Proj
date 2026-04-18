"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
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
              router.push(
                selectedRole === "student"
                  ? "/student/chat"
                  : "/lecturer/dashboard",
              )
            }
            className="inline-flex items-center justify-center rounded-3xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            Continue
          </button>
        </div>
      </div>
    </main>
  );
}
