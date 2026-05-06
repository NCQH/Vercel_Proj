"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  Menu,
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
    { label: "Materials", href: "/student/materials", icon: FileText },
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
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [hasNewMaterials, setHasNewMaterials] = useState(false);
  const [profileFullName, setProfileFullName] = useState("");
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession();
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        accountMenuRef.current &&
        !accountMenuRef.current.contains(event.target as Node)
      ) {
        setIsAccountMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Role guard: redirect user if opened wrong section
  useEffect(() => {
    if (status !== "authenticated") return;

    fetch("/api/users/me")
      .then((res) => res.json())
      .then((data) => {
        const fullName = String(data?.profile?.full_name || "").trim();
        setProfileFullName(fullName);

        const profileRole = String(data?.profile?.class_name || "student").toLowerCase();
        const expectedRole = role;
        if (profileRole !== expectedRole) {
          router.replace(profileRole === "lecturer" ? "/lecturer/dashboard" : "/student/chat");
        }
      })
      .catch(() => {
        // keep current page if profile check fails
      });
  }, [status, role, router]);

  useEffect(() => {
    if (role !== "student" || status !== "authenticated" || !identity) return;

    const checkNewMaterials = async () => {
      try {
        const membershipsRes = await fetch(`/api/classes?user_id=${encodeURIComponent(identity)}&role=student`, { cache: "no-store" });
        if (!membershipsRes.ok) return;
        const membershipsData = await membershipsRes.json();
        const approvedClassIds = (membershipsData.items || [])
          .filter((m: { status?: string; class?: { id?: string } }) => m.status === "approved" && m.class?.id)
          .map((m: { class: { id: string } }) => m.class.id);

        if (approvedClassIds.length === 0) {
          setHasNewMaterials(false);
          return;
        }

        const fileResponses = await Promise.all(
          approvedClassIds.map((classId: string) =>
            fetch(`/api/class-files?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(classId)}`, { cache: "no-store" })
          )
        );

        const fileJsons = await Promise.all(fileResponses.map((r) => (r.ok ? r.json() : Promise.resolve({ items: [] }))));
        const allFiles = fileJsons.flatMap((j) => j.items || []);
        const latestUploadedAt = allFiles.reduce((max: number, f: { uploaded_at?: string }) => {
          const t = f.uploaded_at ? new Date(f.uploaded_at).getTime() : 0;
          return t > max ? t : max;
        }, 0);

        const seenKey = `student_materials_last_seen_${identity}`;
        const seenAt = Number(localStorage.getItem(seenKey) || "0");
        setHasNewMaterials(latestUploadedAt > seenAt);
      } catch {
        setHasNewMaterials(false);
      }
    };

    checkNewMaterials();
  }, [role, status, identity, pathname]);

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
                  className={`group flex items-center gap-3 rounded-3xl px-4 py-3 text-sm font-medium transition ${active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-700 hover:bg-slate-100"
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="relative inline-flex items-center gap-2">
                    {item.label}
                    {role === "student" && item.href === "/student/materials" && hasNewMaterials ? (
                      <span className="inline-block h-2.5 w-2.5 rounded-full bg-rose-500" />
                    ) : null}
                  </span>
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
            <div className="flex w-full items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-3">
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

              {/* Account button - same style as original StudentChat button */}
              <div className="relative ml-auto mr-5" ref={accountMenuRef}>
                <button
                  id="account-menu-toggle"
                  type="button"
                  onClick={() => setIsAccountMenuOpen((prev) => !prev)}
                  className="flex items-center rounded-full border border-slate-300 bg-white p-1.5 shadow-sm transition hover:shadow"
                >
                  <div className="h-8 w-8 overflow-hidden rounded-full bg-brand-100 ring-1 ring-slate-200">
                    {session?.user?.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={session.user.image}
                        alt="User avatar"
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-xs font-semibold text-brand-700">
                        {(session?.user?.name || session?.user?.email || "U")
                          .slice(0, 1)
                          .toUpperCase()}
                      </div>
                    )}
                  </div>
                </button>

                {isAccountMenuOpen && (
                  <div className="absolute right-0 z-50 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                      Account
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {profileFullName || session?.user?.name || "Unknown User"}
                    </p>
                    <p className="text-xs text-slate-600">
                      {session?.user?.email || "No email"}
                    </p>

                    <div className="mt-4 grid gap-2 text-sm">
                      <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                        <span className="text-slate-500">Role</span>
                        <span className="font-medium text-slate-900 capitalize">
                          {roleLabel[role]}
                        </span>
                      </div>
                    </div>

                    <button
                      id="logout-btn"
                      type="button"
                      onClick={() => signOut({ callbackUrl: "/login" })}
                      className="mt-4 w-full rounded-full border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                      Sign out
                    </button>
                  </div>
                )}
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
                  className={`group flex items-center gap-3 rounded-3xl px-4 py-3 text-sm font-medium transition ${active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-700 hover:bg-slate-100"
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="relative inline-flex items-center gap-2">
                    {item.label}
                    {role === "student" && item.href === "/student/materials" && hasNewMaterials ? (
                      <span className="inline-block h-2.5 w-2.5 rounded-full bg-rose-500" />
                    ) : null}
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>
      </div>
    </div>
  );
}
