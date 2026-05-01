import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

async function isRegisteredAndOnboarded(email?: string | null) {
  if (!email || !supabaseUrl || !supabaseServiceRoleKey) return false;

  const url = `${supabaseUrl}/rest/v1/users?email=eq.${encodeURIComponent(email)}&select=id,onboarded&limit=1`;
  const response = await fetch(url, {
    headers: {
      apikey: supabaseServiceRoleKey,
      Authorization: `Bearer ${supabaseServiceRoleKey}`,
    },
    cache: "no-store",
  });

  if (!response.ok) return false;
  const rows = (await response.json()) as Array<{ onboarded?: boolean }>;
  return !!rows[0]?.onboarded;
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async signIn({ user }) {
      const allowed = await isRegisteredAndOnboarded(user?.email);
      return allowed;
    },
    async jwt({ token, user, profile }) {
      if (user) {
        token.userId = user.email || user.id || token.sub || "anonymous_user";
        token.name = user.name || token.name;
        token.email = user.email || token.email;
        token.picture = user.image || token.picture;
      }

      if (profile && typeof profile === "object") {
        token.name = token.name || (profile as { name?: string }).name;
        token.email = token.email || (profile as { email?: string }).email;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.name = (token.name as string) || session.user.name;
        session.user.email = (token.email as string) || session.user.email;
        session.user.image = (token.picture as string) || session.user.image;
        (session.user as { id?: string }).id =
          (token.userId as string) || token.sub || "anonymous_user";
      }
      return session;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
