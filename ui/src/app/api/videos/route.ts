import { readdir } from "fs/promises";
import { join } from "path";
import { NextResponse } from "next/server";

export async function GET() {
  const publicDir = join(process.cwd(), "public");
  const files = await readdir(publicDir);
  const videos = files.filter((f) => f.endsWith(".mp4"));
  return NextResponse.json(videos);
}
