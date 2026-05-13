import { getServerSession } from "next-auth";
import { authOptions } from "../app/api/auth/[...nextauth]/route";

export async function getRequiredSessionUserId(): Promise<string> {
  const session = await getServerSession(authOptions);
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  return user?.id || user?.email || user?.name || "";
}
