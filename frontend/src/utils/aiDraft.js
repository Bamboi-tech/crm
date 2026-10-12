// Bamboi: applies a "Generate with AI" draft (bamboi_crm.api.email_draft) to the
// composer. Kept in its own file so the fork's edits to upstream components stay a few
// lines long and upstream merges rarely conflict.

import { call } from 'frappe-ui'

// The reply quote EmailArea.vue inserts (a <blockquote>) and anything after it.
export function quotedPart(html) {
  const i = (html || '').indexOf('<blockquote')
  return i === -1 ? '' : html.slice(i)
}

// Draft first, then the user's signature, then the quoted message of a reply: the
// composer's own signature sits above the cursor, which would put it above the draft.
export function draftBody(draftHtml, currentHtml, signature) {
  const sig = signature ? signature.replace(/\n/g, '<br>') : ''
  return (draftHtml || '') + sig + quotedPart(currentHtml)
}

// `content` and `subject` are the composer's refs. The subject is replaced only while it
// is still the composer's default, never a reply's deliberate "Re: ...".
export async function applyAiDraft(
  result,
  { content, subject, defaultSubject },
) {
  let signature = ''
  try {
    signature = await call('crm.api.get_user_signature')
  } catch {
    // Draft without a signature rather than lose the draft.
  }
  if (result.subject && subject.value === defaultSubject) {
    subject.value = result.subject
  }
  content.value = draftBody(result.content, content.value, signature)
}
