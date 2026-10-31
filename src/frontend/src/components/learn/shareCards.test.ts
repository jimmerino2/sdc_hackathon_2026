// @vitest-environment node
import { createSSRApp, h } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { renderToString, type SSRContext } from 'vue/server-renderer';
import { describe, expect, it } from 'vitest';
import LinkedInShareDialog from './LinkedInShareDialog.vue';
import ShareCard from './ShareCard.vue';

const props = { role: 'Software Developers', skills: 36, sections: 5, minutes: 600, name: 'Aisha Rahman' };

async function render(component: object) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] });
  const app = createSSRApp({ render: () => h(component, props) });
  app.use(router);
  await router.push('/');
  await router.isReady();
  const ctx: SSRContext = {};
  const html = await renderToString(app, ctx);
  return { html, teleported: String(ctx.teleports?.body ?? '') };
}

describe('Share card', () => {
  it('has the Larp on LinkedIn button and says nothing is sent without the learner', async () => {
    const { html } = await render(ShareCard);
    expect(html).toContain('Larp on LinkedIn');
    expect(html).toContain('Software Developers');
    expect(html).toContain('nothing is sent until you say so');
  });
});

describe('Share dialog', () => {
  it('shows the editable post, the copy, download and open buttons, and the plain-words consent', async () => {
    const { teleported } = await render(LinkedInShareDialog);
    expect(teleported).toContain('Share your Jobee roadmap');
    expect(teleported).toContain('<textarea');
    expect(teleported).toContain('Copy text');
    expect(teleported).toContain('Open LinkedIn');
    expect(teleported).toContain('Put my name on the image');
    expect(teleported).toContain('isn’t an accredited qualification');
  });

  it('only offers the name option when the learner has a name', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] });
    const app = createSSRApp({ render: () => h(LinkedInShareDialog, { ...props, name: '' }) });
    app.use(router);
    const ctx: SSRContext = {};
    await renderToString(app, ctx);
    expect(String(ctx.teleports?.body ?? '')).not.toContain('Put my name on the image');
  });
});
