import { findKeywords } from '../data/resumeKeywords';

export const DOC_WIDTH = 420;
const MAX_PAGES = 3;

/** One highlighted keyword, positioned on its page in CSS px. */
export interface Mark {
  key: string;
  page: number;
  left: number;
  top: number;
  width: number;
  height: number;
  /** Distance from the top of the whole document, so the scan line knows when it has passed it. */
  y: number;
}

export interface ResumePreview {
  pages: { canvas: HTMLCanvasElement; width: number; height: number }[];
  /** Sorted top to bottom. */
  marks: Mark[];
  /** Mentions per display name, and the names in the order they first appear. */
  counts: Record<string, number>;
  order: string[];
  pageCount: number;
  chars: number;
  /** Height of the rendered pages together. */
  height: number;
}

/**
 * Draws the first pages of the PDF and finds skill keywords in its text layer, keeping their exact rectangles.
 * Runs in the browser; the file is sent to the API separately.
 */
export async function readResumePdf(file: File): Promise<ResumePreview> {
  // pdf.js is large, so it loads only when someone uploads a resume.
  const [pdfjs, { default: workerSrc }] = await Promise.all([import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.js?url')]);
  pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

  const pdf = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const out: ResumePreview = { pages: [], marks: [], counts: {}, order: [], pageCount: pdf.numPages, chars: 0, height: 0 };

  for (let n = 1; n <= Math.min(pdf.numPages, MAX_PAGES); n++) {
    const page = await pdf.getPage(n);
    const scale = DOC_WIDTH / page.getViewport({ scale: 1 }).width;
    const vp = page.getViewport({ scale });
    const hi = page.getViewport({ scale: scale * dpr });

    const canvas = document.createElement('canvas');
    canvas.width = Math.floor(hi.width);
    canvas.height = Math.floor(hi.height);
    canvas.style.width = `${vp.width}px`;
    canvas.style.height = `${vp.height}px`;
    await page.render({ canvasContext: canvas.getContext('2d')!, viewport: hi }).promise;

    const items = (await page.getTextContent()).items.filter((it): it is Extract<typeof it, { str: string }> => 'str' in it);
    let text = '';
    const starts = items.map((it) => {
      const at = text.length;
      text += it.str + (it.hasEOL ? '\n' : '');
      return at;
    });
    out.chars += text.length;

    for (const hit of findKeywords(text)) {
      out.counts[hit.key] = (out.counts[hit.key] ?? 0) + 1;
      if (!out.order.includes(hit.key)) out.order.push(hit.key);
      // A keyword can span text items; each gets the share of its width that the keyword covers.
      items.forEach((it, i) => {
        const len = it.str.length;
        const from = starts[i];
        if (!len || from >= hit.end || from + len <= hit.start) return;
        const a = Math.max(hit.start, from) - from;
        const b = Math.min(hit.end, from + len) - from;
        const tr = pdfjs.Util.transform(vp.transform, it.transform);
        const w = it.width * scale;
        const fontHeight = Math.hypot(tr[2], tr[3]);
        const top = tr[5] - fontHeight * 0.92;
        out.marks.push({
          key: hit.key,
          page: out.pages.length,
          left: tr[4] + (w * a) / len - 1.5,
          top,
          width: (w * (b - a)) / len + 3,
          height: fontHeight * 1.12,
          y: out.height + top,
        });
      });
    }
    out.pages.push({ canvas, width: vp.width, height: vp.height });
    out.height += vp.height;
  }
  out.marks.sort((a, b) => a.y - b.y);
  return out;
}
