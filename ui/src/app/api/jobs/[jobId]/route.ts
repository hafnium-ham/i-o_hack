import { NextRequest, NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  const res = await fetch(`${FASTAPI_URL}/jobs/${jobId}`);

  if (!res.ok) {
    return NextResponse.json({ error: "Job not found" }, { status: res.status });
  }

  return NextResponse.json(await res.json());
}
