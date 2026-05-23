import { join } from "path";
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { filename, targetLanguages } = await req.json();
  const filePath = join(process.cwd(), "public", filename);

  const res = await fetch(`${FASTAPI_URL}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_type: "file_path",
      source_value: filePath,
      target_languages: targetLanguages ?? ["es", "pt", "fr"],
      mode: "direct",
    }),
  });

  if (!res.ok) {
    return NextResponse.json({ error: "FastAPI error" }, { status: res.status });
  }

  return NextResponse.json(await res.json());
}
