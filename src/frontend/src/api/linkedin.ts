import { API_URL } from './config';

/** A failed LinkedIn request, with a message that can be shown to the learner as is. */
export class LinkedInError extends Error {}

let status: Promise<boolean> | undefined;

/** Whether the server can post to LinkedIn (its app keys are set). Asked once per page load; a failure counts as no. */
export function linkedinEnabled(): Promise<boolean> {
  status ??= fetch(`${API_URL}/linkedin/status`)
    .then((res) => (res.ok ? res.json().then((b) => !!b.enabled) : false))
    .catch(() => false);
  return status;
}

/**
 * Hands the learner's reviewed draft to the server and returns where to send the browser: LinkedIn's sign-in, where they
 * allow one post. Nothing is posted until they agree there.
 */
export async function startLinkedInShare(text: string, imageDataUrl: string): Promise<string> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/linkedin/share`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, image_base64: imageDataUrl }),
    });
  } catch {
    throw new LinkedInError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return (await res.json()).authorize_url;
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  throw new LinkedInError(detail ?? 'Couldn’t start the LinkedIn post. Try again in a moment.');
}
