import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const incomingUrl = new URL(request.url);
    const fileId = incomingUrl.searchParams.get("file_id") || "";
    const backendUrl = new URL(`${getBackendApiBase()}/api/classes/files/download_file`);
    backendUrl.searchParams.set("user_id", userId);
    backendUrl.searchParams.set("file_id", fileId);

    const response = await fetch(backendUrl, { headers: backendHeaders(), cache: "no-store" });
    const contentType = response.headers.get("Content-Type") || "application/octet-stream";
    const contentDisposition = response.headers.get("Content-Disposition") || "attachment";

    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": contentDisposition,
      },
    });
  } catch (error) {
    console.error("Class file download proxy failed", error);
    return NextResponse.json({ error: "Failed to download class file" }, { status: 500 });
  }
}
