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

export async function extractResume(file: File): Promise<ResumeResult> {
  const form = new FormData();
  form.append('file', file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/resume`, { method: 'POST', body: form });
  } catch {
    throw new ResumeUploadError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();

  const detail = await res
    .json()
    .then((b) => (typeof b?.detail === 'string' ? b.detail : null))
    .catch(() => null);
  if (res.status === 413) throw new ResumeUploadError('That file is over 10 MB. Try a smaller PDF.');
  if (res.status === 400 || res.status === 422) throw new ResumeUploadError(detail ?? 'That file couldn’t be read. Try another PDF.');
  throw new ResumeUploadError('Something went wrong reading your resume. Try again in a moment.');
}
