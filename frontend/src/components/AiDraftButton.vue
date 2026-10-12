<!--
  Shared with crm/frontend/src/components/AiDraftButton.vue (the Bamboi-tech/crm fork).
  Kept as two copies rather than one shared package because the two frontends are
  separate Vite projects with no shared dependency of their own (see README.md >
  "Inbox backend" for why this app's frontend is not a build target inside
  crm/frontend) -- update both together.

  Renders nothing until `get_draft_config` resolves `enabled: true`, which is what
  makes the crm-fork copy a no-op when the feature is switched off in Bamboi CRM
  Settings.
-->
<template>
  <div v-if="config.data?.enabled" class="flex items-center">
    <Button
      variant="ghost"
      :tooltip="__('Generate with AI')"
      icon="lucide-sparkles"
      :loading="generating"
      @click="generateNow()"
    />
    <Popover transition="default">
      <template #target="{ togglePopover }">
        <Button
          variant="ghost"
          :tooltip="__('Generate from bullet points')"
          icon="lucide-chevron-down"
          class="!px-1"
          @click="
            () => {
              togglePopover()
              focusTextarea()
            }
          "
        />
      </template>
      <template #body="{ togglePopover }">
        <div
          class="w-72 rounded-lg bg-surface-elevation-2 p-3 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <textarea
            ref="textareaEl"
            v-model="instructions"
            rows="4"
            class="w-full resize-none rounded border border-outline-gray-2 bg-surface-base p-2 text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:border-outline-gray-4 focus:outline-none focus:ring-0"
            :placeholder="__('What should this email say? One point per line.')"
            @keydown.enter.exact.prevent.stop="submitFromPopover(togglePopover)"
            @keydown.esc.stop="togglePopover()"
          />
          <div class="mt-2 flex flex-col gap-2">
            <Checkbox v-model="useTemplate" :label="__('Include template')" />
            <template v-if="useTemplate">
              <Select
                v-if="templateOptions.length"
                v-model="template"
                :options="templateOptions"
                :placeholder="__('Choose a template')"
              />
              <p v-else class="text-xs text-ink-gray-5">
                {{
                  templates.loading
                    ? __('Loading...')
                    : __('No email templates available.')
                }}
              </p>
              <p class="text-xs text-ink-gray-5">
                {{
                  __(
                    "The draft follows the template's structure and gist, in fresh wording.",
                  )
                }}
              </p>
            </template>
          </div>
          <div class="mt-2 flex justify-end">
            <Button
              variant="solid"
              size="sm"
              :label="__('Generate')"
              :loading="generating"
              :disabled="!canGenerate"
              @click="submitFromPopover(togglePopover)"
            />
          </div>
        </div>
      </template>
    </Popover>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  Button,
  Checkbox,
  Popover,
  Select,
  call,
  createResource,
  toast,
} from 'frappe-ui'

const props = defineProps({
  // Trusted when both are given (the CRM composer always has them). Left null for a
  // brand-new Inbox compose, whose reference (if any) is resolved server-side from
  // `recipients`/`inReplyTo` instead.
  referenceDoctype: { type: String, default: null },
  referenceName: { type: String, default: null },
  recipients: { type: String, default: '' },
  inReplyTo: { type: String, default: null },
  // "bulk" drafts an email for many recipients at once (a campaign step, the bulk Send
  // Email action): no record, so it addresses the recipient with merge fields instead.
  // `campaign`/`stepIdx` then give the model the campaign's earlier steps as context.
  mode: { type: String, default: 'single' },
  campaign: { type: String, default: null },
  stepIdx: { type: Number, default: null },
})

const emit = defineEmits(['generated'])

const instructions = ref('')
const useTemplate = ref(false)
const template = ref('')
const generating = ref(false)
const textareaEl = ref(null)

// A bulk email goes to leads, so offer the lead templates; a single email offers those
// of the record it is about (every enabled one when the Inbox has not resolved a record).
const templateDoctype = computed(() =>
  props.mode === 'bulk' ? 'CRM Lead' : props.referenceDoctype,
)
const templates = createResource({
  url: 'bamboi_crm.api.email_draft.get_draft_templates',
  makeParams: () => ({ reference_doctype: templateDoctype.value || undefined }),
})
const templateOptions = computed(() =>
  (templates.data || []).map((t) => ({ label: t.name, value: t.name })),
)
// Choosing "Include template" without picking one would silently draft without it.
const canGenerate = computed(() => !useTemplate.value || !!template.value)

watch(useTemplate, (on) => {
  if (on) {
    templates.fetch()
  } else {
    template.value = ''
  }
})

const config = createResource({
  url: 'bamboi_crm.api.email_draft.get_draft_config',
  cache: 'bamboi-ai-email-draft-config',
  auto: true,
})

function focusTextarea() {
  nextTick(() => textareaEl.value?.focus())
}

// This component never unmounts between compose sessions -- both EmailEditor.vue and
// ComposeModal.vue keep it alive with v-show, not v-if, the same way they keep their
// own editors alive. Left-over bullet points from an abandoned draft on one email
// must not resurface when the user opens the popover for a completely different one.
watch(
  () => [props.referenceDoctype, props.referenceName, props.inReplyTo],
  () => {
    instructions.value = ''
    useTemplate.value = false
  },
)

// Returns true on success, so a caller can decide whether it's safe to close --
// exposed mainly for the parent's own "New message" reset, where the reference
// identity above does not change between two separate blank composes.
function reset() {
  instructions.value = ''
  useTemplate.value = false
}

// Awaited by the caller so the popover stays open (with its own Generate button
// showing a loading state) for the whole ~5-15s the request can take, and only closes
// on success -- closing it immediately on click, before the request even resolves,
// would leave the user watching a tiny ghost-button spinner as their only sign
// anything is happening, with no way to tell success from failure until a toast
// appears well after the popover they were looking at is already gone.
async function submitFromPopover(togglePopover) {
  if (!canGenerate.value) return
  if (await generateNow()) {
    togglePopover()
  }
}

async function generateNow() {
  if (generating.value || !canGenerate.value) return false
  generating.value = true
  try {
    const result =
      props.mode === 'bulk'
        ? await call('bamboi_crm.api.email_draft.generate_bulk_draft', {
            campaign: props.campaign || undefined,
            step_idx: props.stepIdx || undefined,
            instructions: instructions.value || undefined,
            template: (useTemplate.value && template.value) || undefined,
          })
        : await call('bamboi_crm.api.email_draft.generate_email_draft', {
            reference_doctype: props.referenceDoctype || undefined,
            reference_name: props.referenceName || undefined,
            recipients: props.recipients || undefined,
            in_reply_to: props.inReplyTo || undefined,
            instructions: instructions.value || undefined,
            template: (useTemplate.value && template.value) || undefined,
          })
    emit('generated', result)
    instructions.value = ''
    useTemplate.value = false
    return true
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Failed to generate a draft'))
    return false
  } finally {
    generating.value = false
  }
}

defineExpose({ generateNow, reset })
</script>
