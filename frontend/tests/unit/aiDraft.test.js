import { describe, expect, it, vi } from 'vitest'

vi.mock('frappe-ui', () => ({ call: vi.fn() }))

import { draftBody, quotedPart } from '@/utils/aiDraft'

describe('aiDraft', () => {
  it('keeps the quoted message of a reply below the draft and signature', () => {
    const current =
      '<p>sig</p><p>typed</p><blockquote><p>old mail</p></blockquote>'
    expect(draftBody('<p>Draft</p>', current, '<p>Sig</p>')).toBe(
      '<p>Draft</p><p>Sig</p><blockquote><p>old mail</p></blockquote>',
    )
  })

  it('replaces everything on a fresh email', () => {
    expect(draftBody('<p>Draft</p>', '<p>old</p>', null)).toBe('<p>Draft</p>')
    expect(quotedPart('')).toBe('')
  })

  it('turns newlines in a plain-text signature into line breaks', () => {
    expect(draftBody('<p>D</p>', '', 'A\nB')).toBe('<p>D</p>A<br>B')
  })
})
