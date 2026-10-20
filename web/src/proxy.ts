// Phone mode only (scripts/phone_mode.sh sets PHONE_KEY): the site is reachable on the Wi-Fi,
// so every request must carry the secret key. Normal mode (no PHONE_KEY): does nothing.
//   1st visit:  /ko?key=SECRET  -> cookie set, redirect to /ko
//   later:      cookie must match, otherwise 401
import { NextResponse, type NextRequest } from "next/server";

const KEY = process.env.PHONE_KEY;

export function proxy(request: NextRequest) {
  if (!KEY) return NextResponse.next();

  const url = request.nextUrl;
  if (url.searchParams.get("key") === KEY) {
    url.searchParams.delete("key");
    const response = NextResponse.redirect(url);
    // readable by the page (not httpOnly) so it can send the key to the AI API as a header
    response.cookies.set("phone_key", KEY, { sameSite: "strict", path: "/", maxAge: 60 * 60 * 12 });
    return response;
  }
  if (request.cookies.get("phone_key")?.value === KEY) return NextResponse.next();
  return new NextResponse("401 Unauthorized: open the link with ?key=… shown in the terminal.", { status: 401 });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
