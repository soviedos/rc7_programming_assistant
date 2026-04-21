/**
 * Catch-all API proxy route handler.
 *
 * Forwards all /api/v1/* requests from the browser to the internal FastAPI
 * service, explicitly forwarding the session cookie so auth works across
 * the Next.js → FastAPI boundary.
 */
import { NextRequest, NextResponse } from "next/server";

const INTERNAL_API = process.env.INTERNAL_API_URL ?? "http://api:8000";

async function proxy(req: NextRequest, path: string): Promise<NextResponse> {
  const targetUrl = `${INTERNAL_API}/api/v1/${path}${req.nextUrl.search}`;

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  };

  // Forward session cookie so the FastAPI auth middleware can read it
  const cookie = req.headers.get("cookie");
  if (cookie) headers["Cookie"] = cookie;

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.text()
      : undefined;

  const upstream = await fetch(targetUrl, {
    method: req.method,
    headers,
    body,
  });

  // Use arrayBuffer to preserve binary data (e.g. PDFs) without UTF-8 corruption
  const data = await upstream.arrayBuffer();

  const responseHeaders = new Headers({
    "Content-Type": upstream.headers.get("content-type") ?? "application/json",
  });

  // Forward Set-Cookie so login/logout/switch-role cookies reach the browser
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "set-cookie") {
      responseHeaders.append("Set-Cookie", value);
    } else if (lower === "content-disposition") {
      responseHeaders.set("Content-Disposition", value);
    }
  });

  return new NextResponse(data, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(req, path.join("/"));
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(req, path.join("/"));
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(req, path.join("/"));
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(req, path.join("/"));
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(req, path.join("/"));
}
