import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";

export const dynamic = "force-dynamic";

type ChatStreamPayload = {
  message?: string;
  session_id?: string;
  preferred_sources?: string[];
};

async function getSessionUserId() {
  const session = await getServerSession(authOptions);
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  return user?.id || user?.email || user?.name || "";
}

export async function POST(request: Request) {
  const encoder = new TextEncoder();

  try {
    const body = (await request.json()) as ChatStreamPayload;

    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const send = (line: string) => controller.enqueue(encoder.encode(line));

        try {
          send("__STEP__:Opening secure chat session...\n");

          const userId = await getSessionUserId();
          if (!userId) {
            send("\n[ERROR] Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
            controller.close();
            return;
          }

          send("__STEP__:Connecting to backend agent...\n");
          const response = await fetch(`${getBackendApiBase()}/api/chat/stream`, {
            method: "POST",
            headers: backendHeaders(),
            body: JSON.stringify({
              ...body,
              user_id: userId,
            }),
            cache: "no-store",
          });

          if (!response.ok || !response.body) {
            const text = await response.text().catch(() => "");
            const message = response.status >= 502
              ? "Máy chủ AI đang quá tải hoặc mất kết nối. Vui lòng thử lại sau ít phút."
              : text || "Chat stream failed";
            send(`\n[ERROR] ${message}`);
            controller.close();
            return;
          }

          send("__STEP__:Backend stream connected...\n");
          const reader = response.body.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) controller.enqueue(value);
          }
          controller.close();
        } catch (error) {
          console.error("Chat stream proxy failed", error);
          send("\n[ERROR] Không thể kết nối tới Agent API. Vui lòng thử lại sau ít phút.");
          controller.close();
        }
      },
    });

    return new NextResponse(stream, {
      status: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    console.error("Chat stream request setup failed", error);
    return NextResponse.json({ error: "Chat stream failed" }, { status: 500 });
  }
}
