import { API_URL } from './config';

export const MAX_RESUME_BYTES = 10 * 1024 * 1024;

export interface SkillScore {
  name: string;
  score: number;
}

export interface ResumeResult {
  resume_id: string | null;
  filename: string | null;
  page_count: number;
  char_count: number;
  top_skills: SkillScore[] | null;
  skills: SkillScore[] | null;
  /** Why skills is null, when the PDF was read but no skills came out (e.g. a scan). */
  error: string | null;
  /** How the skills were found, shown on the results summary when present. */
  engine?: { candidates?: number; seconds?: number };
}

/** A failed upload, with a message that can be shown to the user as is. */
export class ResumeUploadError extends Error {}

/** Checks the file in the browser first, so obvious problems don't need a round trip. */
export function checkResumeFile(file: File): string | null {
  if (!file.size) return 'That file is empty. Pick another one.';
  if (file.size > MAX_RESUME_BYTES) return 'That file is over 10 MB. Try a smaller PDF.';
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) return 'Only PDF files work for now.';
  return null;
}

/** What the server reports while it reads a resume (POST /resume/stream). */
export type ResumeEvent =
  | { type: 'read'; page_count: number; char_count: number; expected_seconds: number }
  | { type: 'candidates'; count: number }
  | { type: 'engine'; source: string }
  | { type: 'thinking'; words: number }
  | { type: 'skill'; name: string; score: number };

/** Splits the stream's text into complete events; what's left over is a half-received event to keep for the next chunk. */
export function takeSseEvents(buffer: string): { events: Record<string, unknown>[]; rest: string } {
  const parts = buffer.split('\n\n');
  const rest = parts.pop() ?? '';
  const events = parts.flatMap((part) => {
    const data = part.split('\n').filter((line) => line.startsWith('data: ')).map((line) => line.slice(6)).join('\n');
    if (!data) return []; // a keep-alive comment
    try {
      return [JSON.parse(data)];
    } catch {
      return [];
    }
  });
  return { events, rest };
}

async function failure(res: Response): Promise<ResumeUploadError> {
  const detail = await res
    .json()
    .then((b) => (typeof b?.detail === 'string' ? b.detail : null))
    .catch(() => null);
  if (res.status === 413) return new ResumeUploadError('That file is over 10 MB. Try a smaller PDF.');
  if (res.status === 400 || res.status === 422) return new ResumeUploadError(detail ?? 'That file couldn’t be read. Try another PDF.');
  return new ResumeUploadError('Something went wrong reading your resume. Try again in a moment.');
}

async function post(path: string, file: File): Promise<Response> {
  const form = new FormData();
  form.append('file', file);
  try {
    return await fetch(`${API_URL}${path}`, { method: 'POST', body: form });
  } catch {
    throw new ResumeUploadError('Couldn’t reach Jobee. Check your connection and try again.');
  }
}

/**
 * Sends the resume and returns the skills found. onEvent hears the server's progress while it works, so the page
 * can show what is really happening. If the server can't stream (an older one), the plain request is used and
 * onEvent just never fires.
 */
export async function extractResume(file: File, onEvent?: (event: ResumeEvent) => void): Promise<ResumeResult> {
  const res = await post('/resume/stream', file);
  if (res.status === 404 || res.status === 405) {
    const plain = await post('/resume', file);
    if (plain.ok) return plain.json();
    throw await failure(plain);
  }
  if (!res.ok) throw await failure(res);
  if (!res.body) throw new ResumeUploadError('Something went wrong reading your resume. Try again in a moment.');

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  let result: ResumeResult | null = null;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      const taken = takeSseEvents(buffer + value);
      buffer = taken.rest;
      for (const event of taken.events) {
        if (event.type === 'result') result = event as unknown as ResumeResult;
        else if (event.type === 'failed') throw new ResumeUploadError(String(event.message ?? 'Something went wrong reading your resume.'));
        else onEvent?.(event as ResumeEvent);
      }
    }
  } catch (e) {
    if (e instanceof ResumeUploadError) throw e;
    throw new ResumeUploadError('The connection dropped while reading your resume. Try again.');
  }
  if (!result) throw new ResumeUploadError('The connection dropped while reading your resume. Try again.');
  return result;
}
