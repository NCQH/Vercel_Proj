import { withAuth } from "next-auth/middleware";

export default withAuth(
  function middleware() {
    // Guard handled by authorized callback below.
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl;

        const protectedPaths = ["/student/chat", "/student/materials", "/student/roadmap"];
        const isProtected = protectedPaths.some((p) => pathname.startsWith(p));

        if (!isProtected) return true;
        return !!token;
      },
    },
    pages: {
      signIn: "/login",
    },
  }
);

export const config = {
  matcher: ["/student/:path*"],
};
