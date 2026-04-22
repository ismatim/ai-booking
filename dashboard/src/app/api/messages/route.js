import { NextResponse } from "next/server";
import generateFakeMessages from "../../data/messages.js";

const data = generateFakeMessages(20);

export async function GET(request, { params }) {
  return NextResponse.json(data);
}
