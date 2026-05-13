import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../lib/session-user";

export const dynamic = "force-dynamic";

async function proxyWithUserId(request: Request, method: "GET" | "POST") {
  const userId = await getRequiredSessionUserId();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (method === "GET") {
    const incomingUrl = new URL(request.url);
    const role = incomingUrl.searchParams.get("role") || "student";
    const backendUrl = new URL(`${getBackendApiBase()}/api/classes`);
    backendUrl.searchParams.set("user_id", userId);
    backendUrl.searchParams.set("role", role);

    const response = await fetch(backendUrl, { headers: backendHeaders(), cache: "no-store" });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  }

  const incoming = await request.formData();
  const outgoing = new FormData();
  outgoing.append("user_id", userId);
  outgoing.append("name", String(incoming.get("name") || ""));
  outgoing.append("description", String(incoming.get("description") || ""));

  const response = await fetch(`${getBackendApiBase()}/api/classes`, {
    method: "POST",
    headers: backendHeaders(""),
    body: outgoing,
    cache: "no-store",
  });
  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}

export async function GET(request: Request) {
  try {
    return await proxyWithUserId(request, "GET");
  } catch (error) {
    console.error("Classes list proxy failed", error);
    return NextResponse.json({ error: "Failed to load classes" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    return await proxyWithUserId(request, "POST");
  } catch (error) {
    console.error("Class create proxy failed", error);
    return NextResponse.json({ error: "Failed to create class" }, { status: 500 });
  }
}
