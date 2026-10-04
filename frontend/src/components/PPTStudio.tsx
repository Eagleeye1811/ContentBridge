import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import DeckPreview from '@/components/preview/DeckPreview'
import { Button, Field, Progress, Segmented, Select } from '@/components/ui'
import { Icon } from '@/lib/icons'
import type {
  Doc,
  FormatInfo,
  Job,
  OutputDetail,
  PresentationOutlineRequest,
  PresentationOutlineResponse,
  SlideOutlineItem,
  IRNode,
  ContentIR,
} from '@/types/api'

interface Props {
  format: FormatInfo
  sources: Doc[]
  languages: string[]
  initialSource?: string
  initialEditId?: string
  onCancel?: () => void
  onCreated: (outputIds: string[]) => void
}

const PURPOSES = [
  { key: 'executive briefing', label: 'Executive Briefing' },
  { key: 'technical briefing', label: 'Technical Briefing' },
  { key: 'research/findings', label: 'Research / Findings' },
  { key: 'public awareness', label: 'Public Awareness' },
  { key: 'project proposal', label: 'Project Proposal' },
  { key: 'training', label: 'Training' },
]

const AUDIENCES = [
  { key: 'technical', label: 'Technical Team' },
  { key: 'officials', label: 'Officials / Leadership' },
  { key: 'public', label: 'Public / Stakeholders' },
  { key: 'team', label: 'Internal Team' },
  { key: 'researchers', label: 'Researchers / Experts' },
  { key: 'students', label: 'Students / Trainees' },
  { key: 'senior_leadership', label: 'Senior Leadership' },
]

const SLIDE_COUNTS = [
  { key: '5', label: '5 slides' },
  { key: '8', label: '8 slides' },
  { key: '10', label: '10 slides' },
  { key: '12', label: '12 slides' },
  { key: '15', label: '15 slides' },
  { key: '20', label: '20 slides' },
  { key: 'auto', label: 'Let AI decide' },
]

const DURATIONS = [
  { key: '5', label: '5 mins' },
  { key: '10', label: '10 mins' },
  { key: '15', label: '15 mins' },
  { key: '30', label: '30 mins' },
]

function normalizeSlideCount(val?: string | number): string {
  if (!val) return 'auto'
  const valStr = String(val).trim()
  const validKeys = ['5', '8', '10', '12', '15', '20', 'auto']
  if (validKeys.includes(valStr)) return valStr
  const num = parseInt(valStr, 10)
  if (!isNaN(num)) {
    const nums = [5, 8, 10, 12, 15, 20]
    const closest = nums.reduce((prev, curr) => (Math.abs(curr - num) < Math.abs(prev - num) ? curr : prev))
    return String(closest)
  }
  return 'auto'
}

const THEMES = [
  { key: 'corporate_blue', label: 'Corporate Blue', swatch: 'bg-blue-700' },
  { key: 'midnight_dark', label: 'Midnight Dark', swatch: 'bg-slate-900' },
  { key: 'minimal_monochrome', label: 'Minimal Monochrome', swatch: 'bg-zinc-800' },
  { key: 'modern_gradient', label: 'Modern Gradient', swatch: 'bg-indigo-600' },
  { key: 'academic_research', label: 'Academic Research', swatch: 'bg-amber-900' },
  { key: 'data_analytics', label: 'Data & Analytics', swatch: 'bg-teal-600' },
  { key: 'warm_editorial', label: 'Warm Editorial', swatch: 'bg-orange-700' },
  { key: 'high_contrast', label: 'High-Contrast', swatch: 'bg-yellow-500' },
]

const LAYOUT_OPTIONS = [
  { key: 'standard_bullet', label: 'Standard Bullets' },
  { key: 'two_column', label: 'Two-Column Split' },
  { key: 'process', label: 'Process Flow' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'metrics', label: 'Key Metrics' },
  { key: 'comparison', label: 'Comparison' },
  { key: 'table', label: 'Data Table' },
  { key: 'section_divider', label: 'Section Divider' },
  { key: 'key_takeaways', label: 'Key Takeaways' },
]

export default function PPTStudio({
  format: _format,
  sources,
  languages,
  initialSource,
  initialEditId,
  onCreated,
  onCancel: _onCancel,
}: Props) {
  const readySources = sources.filter((d) => d.status === 'ready')

  // Workflow Step State (1: Source -> 2: Configure -> 3: Outline -> 4: Generate -> 5: Review/Edit)
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1)

  // Document State
  const [selectedSourceId, setSelectedSourceId] = useState<string>(
    initialSource && readySources.some((d) => d.id === initialSource)
      ? initialSource
      : readySources[0]?.id ?? '',
  )
  const [uploading, setUploading] = useState(false)
  const [uploadDoc, setUploadDoc] = useState<Doc | null>(null)

  // Configuration State
  const [config, setConfig] = useState<PresentationOutlineRequest>({
    title: '',
    purpose: 'executive briefing',
    audience: 'officials',
    slide_count: '8',
    duration: '10',
    language: 'en',
    content_detail: 'balanced',
    theme: 'corporate_blue',
    visual_preference: 'balanced',
    speaker_notes: true,
    additional_instructions: '',
  })

  // Outline State
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [outline, setOutline] = useState<PresentationOutlineResponse | null>(null)

  // Generation & Output State
  const [job, setJob] = useState<Job | null>(null)
  const [generatingDeck, setGeneratingDeck] = useState(false)
  const [outputDetail, setOutputDetail] = useState<OutputDetail | null>(null)

  // Interactive Slide Studio State
  const [activeSlideIndex, setActiveSlideIndex] = useState(0)
  const [editingSlide, setEditingSlide] = useState<IRNode | null>(null)
  const [slideInstructions, setSlideInstructions] = useState('')
  const [regeneratingSlide, setRegeneratingSlide] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [editorTab, setEditorTab] = useState<'preview' | 'edit'>('preview')
  const [showSettingsDrawer, setShowSettingsDrawer] = useState(false)

  // Reconfig State
  const [editConfig, setEditConfig] = useState<PresentationOutlineRequest>({ ...config })
  const [changeSummary, setChangeSummary] = useState<string[]>([])
  const [reconfiguring, setReconfiguring] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (readySources.length > 0 && !selectedSourceId) {
      setSelectedSourceId(readySources[0].id)
    }
  }, [readySources, selectedSourceId])

  useEffect(() => {
    if (initialEditId) {
      api
        .getOutput(initialEditId)
        .then((detail) => {
          setOutputDetail(detail)
          if (detail.document_id) {
            setSelectedSourceId(detail.document_id)
          }
          const ctrls = (detail.controls || {}) as Record<string, any>
          const slidesCount = String(
            detail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1,
          )
          const loadedConfig: PresentationOutlineRequest = {
            title: detail.content_ir.title || '',
            purpose: ctrls.purpose || 'executive briefing',
            audience: detail.audience || 'officials',
            slide_count: slidesCount,
            duration: ctrls.duration || '10',
            language: detail.language || 'en',
            content_detail: ctrls.detail_level || 'balanced',
            theme: ctrls.theme || 'corporate_blue',
            visual_preference: ctrls.visual_preference || 'balanced',
            speaker_notes: ctrls.speaker_notes ?? true,
            additional_instructions: ctrls.additional_instructions || '',
          }
          setConfig(loadedConfig)
          setEditConfig(loadedConfig)
          setStep(5)
        })
        .catch((err) => {
          setError(err instanceof ApiError ? err.message : 'Failed to load presentation')
        })
    }
  }, [initialEditId])

  // File Upload Handler
  async function handleFileUpload(file: File) {
    setUploading(true)
    setError(null)
    try {
      const res = await api.uploadDocument(file)
      setUploadDoc(res.document)
      await api.streamJob(res.job.id, () => {})
      const updatedDoc = await api.getDocument(res.document.id)
      setUploadDoc(updatedDoc)
      setSelectedSourceId(updatedDoc.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  // Step 2 -> Step 3: Generate AI Outline
  async function handleGenerateOutline() {
    if (!selectedSourceId) return
    setGeneratingOutline(true)
    setError(null)
    try {
      const res = await api.generatePresentationOutline(selectedSourceId, config)
      setOutline(res)
      setStep(3)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Outline generation failed')
    } finally {
      setGeneratingOutline(false)
    }
  }

  // Helper Outline Modifiers
  function handleUpdateOutlineItem(index: number, patch: Partial<SlideOutlineItem>) {
    if (!outline) return
    const updated = [...outline.slides]
    updated[index] = { ...updated[index], ...patch }
    setOutline({ ...outline, slides: updated })
  }

  function handleAddOutlineSlide() {
    if (!outline) return
    const newSlide: SlideOutlineItem = {
      id: `out_${outline.slides.length + 1}`,
      title: 'New Slide Card',
      key_message: 'Key message summary',
      summary: 'Detailed summary bullet point',
      suggested_layout: 'standard_bullet',
    }
    setOutline({ ...outline, slides: [...outline.slides, newSlide] })
  }

  function handleDeleteOutlineSlide(index: number) {
    if (!outline) return
    setOutline({ ...outline, slides: outline.slides.filter((_, i) => i !== index) })
  }

  function handleMoveOutlineSlide(index: number, direction: 'up' | 'down') {
    if (!outline) return
    const slides = [...outline.slides]
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= slides.length) return
    const temp = slides[index]
    slides[index] = slides[targetIndex]
    slides[targetIndex] = temp
    setOutline({ ...outline, slides })
  }

  // Step 2/3 -> Step 4/5: Generate Full Presentation
  async function handleApproveAndGenerateDeck() {
    if (!selectedSourceId) return
    setGeneratingDeck(true)
    setStep(4)
    setError(null)

    try {
      const targetSlides =
        config.slide_count !== 'auto'
          ? String(config.slide_count)
          : outline
            ? String(outline.slides.length + 1)
            : '8'

      const startedJob = await api.generate(selectedSourceId, {
        types: ['ppt'],
        languages: [config.language || 'en'],
        audience: config.audience,
        controls: {
          detail_level: config.content_detail || 'balanced',
          theme: config.theme || 'corporate_blue',
          purpose: config.purpose || 'executive briefing',
          duration: config.duration || '10',
        },
        options: {
          ppt: {
            slides: targetSlides,
            presenting_to: config.audience || 'officials',
          },
        },
      })
      setJob(startedJob)

      const finalJob = await api.streamJob(startedJob.id, setJob)
      if (finalJob.status === 'failed') {
        setError(finalJob.error ?? 'Generation failed')
        setStep(3)
        return
      }

      const outputId = finalJob.result?.outputs?.[0]
      if (outputId) {
        const detail = await api.getOutput(outputId)

        // Apply outline layout choices if custom outline was approved
        if (outline && detail.content_ir) {
          const updatedNodes = detail.content_ir.nodes.map((node, i) => {
            const outlineItem = outline.slides[i - 1]
            if (node.kind === 'slide' && outlineItem) {
              return { ...node, layout: outlineItem.suggested_layout || 'standard_bullet' }
            }
            return node
          })
          const updatedDetail = {
            ...detail,
            content_ir: { ...detail.content_ir, nodes: updatedNodes },
          }
          await api.updateOutput(outputId, updatedDetail.content_ir)
          setOutputDetail(updatedDetail)
        } else {
          setOutputDetail(detail)
        }

        onCreated([outputId])
        setStep(5)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Generation failed')
      setStep(3)
    } finally {
      setGeneratingDeck(false)
    }
  }

  // Slide Selection & Live Canvas Editing
  function selectSlideForEdit(index: number) {
    setActiveSlideIndex(index)
    if (!outputDetail) return
    const slides = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    if (index === 0) {
      setEditingSlide(null)
    } else {
      setEditingSlide(slides[index - 1] || null)
    }
  }

  async function handleSaveSlideEdit(updatedNode: IRNode) {
    if (!outputDetail) return
    const nodeWithFlag: IRNode = { ...updatedNode, is_user_modified: true }
    try {
      const updatedNodes = outputDetail.content_ir.nodes.map((n) =>
        n.id === nodeWithFlag.id ? nodeWithFlag : n,
      )
      const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setEditingSlide(nodeWithFlag)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed')
    }
  }

  async function handleSingleSlideRegenerate() {
    if (!outputDetail || !editingSlide) return
    setRegeneratingSlide(true)
    setError(null)
    try {
      const res = await api.regenerateSlide(outputDetail.id, editingSlide.id, slideInstructions)
      setOutputDetail(res)
      setSlideInstructions('')
      const updatedNode = res.content_ir.nodes.find((n) => n.id === editingSlide.id)
      if (updatedNode) setEditingSlide(updatedNode)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Single slide regeneration failed')
    } finally {
      setRegeneratingSlide(false)
    }
  }

  // Slide Deck Modifiers
  async function handleAddSlide(insertIndex?: number) {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')
    const newSlideId = `slide_${Date.now()}`
    const newSlide: IRNode = {
      id: newSlideId,
      kind: 'slide',
      title: 'New Executive Slide',
      layout: 'standard_bullet',
      items: ['Key takeaway point 1', 'Supporting evidence or contextual detail'],
      notes: 'Speaker notes for new slide.',
      fact_ids: [],
      is_user_modified: true,
    }

    const updatedSlides = [...slideNodes]
    const idx = insertIndex !== undefined ? insertIndex : updatedSlides.length
    updatedSlides.splice(idx, 0, newSlide)

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(idx + 1)
      setEditingSlide(newSlide)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Add slide failed')
    }
  }

  async function handleDeleteSlide(slideId: string) {
    if (!outputDetail) return
    const updatedNodes = outputDetail.content_ir.nodes.filter((n) => n.id !== slideId)
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      const remainingSlides = updatedNodes.filter((n) => n.kind === 'slide')
      if (remainingSlides.length > 0) {
        setActiveSlideIndex(1)
        setEditingSlide(remainingSlides[0])
      } else {
        setActiveSlideIndex(0)
        setEditingSlide(null)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete slide failed')
    }
  }

  async function handleDuplicateSlide(slideNode: IRNode) {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const slideIdx = slideNodes.findIndex((s) => s.id === slideNode.id)
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')

    const dupSlide: IRNode = {
      ...slideNode,
      id: `slide_${Date.now()}`,
      title: `${slideNode.title || 'Slide'} (Copy)`,
      is_user_modified: true,
    }

    const updatedSlides = [...slideNodes]
    updatedSlides.splice(slideIdx + 1, 0, dupSlide)

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(slideIdx + 2)
      setEditingSlide(dupSlide)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Duplicate slide failed')
    }
  }

  async function handleMoveSlide(index: number, direction: 'up' | 'down') {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')

    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= slideNodes.length) return

    const updatedSlides = [...slideNodes]
    const temp = updatedSlides[index]
    updatedSlides[index] = updatedSlides[targetIndex]
    updatedSlides[targetIndex] = temp

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(targetIndex + 1)
      setEditingSlide(updatedSlides[targetIndex])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Reorder slide failed')
    }
  }

  // Theme & Global Settings Actions
  async function handleApplyThemeChange(newTheme: string) {
    if (!outputDetail) return
    setConfig((prev) => ({ ...prev, theme: newTheme }))
    setEditConfig((prev) => ({ ...prev, theme: newTheme }))

    try {
      const res = await api.reconfigurePresentation(outputDetail.id, {
        config: { ...editConfig, theme: newTheme },
        scope: 'all',
        preserve_user_edits: true,
        content_ir: outputDetail.content_ir,
      })
      setOutputDetail(res.output)
      if (res.change_summary.length > 0) {
        setChangeSummary(res.change_summary)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Theme update failed')
    }
  }

  function handleOpenSettingsDrawer() {
    if (outputDetail) {
      const ctrls = (outputDetail.controls || {}) as Record<string, any>
      const actualCount = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1
      const rawCount = ctrls.slide_count || config.slide_count || actualCount
      setEditConfig({
        title: outputDetail.content_ir.title || config.title,
        purpose: ctrls.purpose || config.purpose || 'executive briefing',
        audience: outputDetail.audience || config.audience || 'officials',
        slide_count: normalizeSlideCount(rawCount),
        duration: ctrls.duration || config.duration || '10',
        language: outputDetail.language || config.language || 'en',
        content_detail: ctrls.detail_level || config.content_detail || 'balanced',
        theme: ctrls.theme || config.theme || 'corporate_blue',
        visual_preference: ctrls.visual_preference || config.visual_preference || 'balanced',
        speaker_notes: config.speaker_notes ?? true,
        additional_instructions: ctrls.additional_instructions || config.additional_instructions || '',
      })
    }
    setShowSettingsDrawer((prev) => !prev)
  }

  async function handleApplyGlobalReconfig() {
    if (!outputDetail) return
    setReconfiguring(true)
    setError(null)
    try {
      const res = await api.reconfigurePresentation(outputDetail.id, {
        config: editConfig,
        scope: 'all',
        preserve_user_edits: true,
        content_ir: outputDetail.content_ir,
      })
      setOutputDetail(res.output)
      setConfig(editConfig)
      setChangeSummary(res.change_summary)
      setShowSettingsDrawer(false)
    } catch (err) {
      console.error('Reconfiguration failed:', err)
      const userMessage =
        err instanceof ApiError && err.message
          ? err.message
          : "Unable to update presentation: We couldn't regenerate the presentation with these settings. Please try again."
      setError(userMessage)
    } finally {
      setReconfiguring(false)
    }
  }

  async function handleRevertVersion() {
    if (!outputDetail) return
    setReverting(true)
    setError(null)
    try {
      const res = await api.revertPresentation(outputDetail.id)
      setOutputDetail(res)
      setChangeSummary(['Reverted presentation to previous version successfully.'])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Revert failed')
    } finally {
      setReverting(false)
    }
  }

  async function handleDownloadPPTX() {
    if (!outputDetail) return
    setExporting(true)
    try {
      const blobUrl = await api.exportUrl(
        outputDetail.id,
        'pptx',
        false,
        config.theme || (outputDetail.controls as any)?.theme || 'corporate_blue',
      )
      const link = document.createElement('a')
      link.href = blobUrl
      const filename = `${(outputDetail.content_ir.title || 'presentation')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')}.pptx`
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Download failed')
    } finally {
      setExporting(false)
    }
  }

  const activeDocName =
    sources.find((d) => d.id === selectedSourceId)?.filename || uploadDoc?.filename || 'Source Document'

  return (
    <div className="space-y-6 rounded-2xl border border-ink-200 bg-white p-6 shadow-sm">
      {/* State-Driven Progress Header Stepper */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-100 pb-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-brand-600 shadow-2xs">
            <Icon name="ppt" className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ink-900">Presentation Studio</h2>
            <p className="text-xs text-ink-500">
              {step === 1 && 'Select or upload a verified source document'}
              {step === 2 && 'Configure target audience, duration, and visual theme'}
              {step === 3 && 'Review and fine-tune AI slide outline cards'}
              {step === 4 && 'Generating PowerPoint presentation deck...'}
              {step === 5 && 'Interactive Slide Studio: Preview, Edit & Export'}
            </p>
          </div>
        </div>

        {/* Workflow State Stepper Badges */}
        <div className="flex items-center gap-1 text-xs font-semibold">
          {[
            { num: 1, label: 'Source' },
            { num: 2, label: 'Configure' },
            { num: 3, label: 'Outline' },
            { num: 4, label: 'Generate' },
            { num: 5, label: 'Review & Export' },
          ].map((s) => {
            const isCurrent = step === s.num
            const isCompleted = step > s.num
            return (
              <button
                key={s.num}
                disabled={!isCompleted}
                onClick={() => {
                  if (isCompleted) setStep(s.num as any)
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${
                  isCurrent
                    ? 'bg-brand-600 text-white shadow-xs'
                    : isCompleted
                      ? 'bg-ink-100 text-ink-800 hover:bg-ink-200 cursor-pointer'
                      : 'text-ink-400 opacity-60 cursor-not-allowed'
                }`}
              >
                {isCompleted ? (
                  <Icon name="check" className="h-3.5 w-3.5 text-emerald-600" />
                ) : (
                  <span>{s.num}.</span>
                )}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-700 flex items-center justify-between shadow-2xs">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 font-bold ml-2 hover:text-red-800">
            ✕
          </button>
        </div>
      )}

      {/* STEP 1: SOURCE SELECTION */}
      {step === 1 && (
        <div className="space-y-6 py-2">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3 rounded-xl border border-ink-200 p-5 bg-ink-50/30">
              <h3 className="text-sm font-bold text-ink-900">Select Existing Source Document</h3>
              <p className="text-xs text-ink-500">
                Choose a pre-processed document with extracted key facts.
              </p>
              {readySources.length > 0 ? (
                <Select
                  value={selectedSourceId}
                  onChange={setSelectedSourceId}
                  options={readySources.map((d) => ({ key: d.id, label: d.filename }))}
                />
              ) : (
                <p className="text-xs text-ink-400 italic">No ready documents found in repository.</p>
              )}
            </div>

            <div className="space-y-3 rounded-xl border border-dashed border-ink-300 p-5 text-center bg-white">
              <h3 className="text-sm font-bold text-ink-900">Upload New Source File</h3>
              <p className="text-xs text-ink-500">Supports PDF, DOCX, TXT, or image files.</p>
              <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-ink-100 px-4 py-2.5 text-xs font-semibold text-ink-800 hover:bg-ink-200 transition">
                <Icon name="plus" />
                {uploading ? 'Processing Document…' : 'Choose File to Upload'}
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,image/*"
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFileUpload(e.target.files[0])
                  }}
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          {selectedSourceId && (
            <div className="flex items-center justify-between rounded-xl bg-blue-50/70 p-4 border border-blue-100">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 text-brand-700 font-bold text-xs">
                  DOC
                </span>
                <div>
                  <p className="text-xs font-bold text-ink-900">{activeDocName}</p>
                  <p className="text-[11px] text-ink-500">
                    Source verified & ready for presentation synthesis.
                  </p>
                </div>
              </div>
              <Button onClick={() => setStep(2)}>
                Continue to Configuration →
              </Button>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: PRESENTATION CONFIGURATION */}
      {step === 2 && (
        <div className="space-y-6 py-2">
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            <Field label="Presentation Title (Optional)">
              <input
                type="text"
                value={config.title || ''}
                onChange={(e) => setConfig({ ...config, title: e.target.value })}
                placeholder="Leave blank for AI auto-title"
                className="w-full rounded-lg border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
              />
            </Field>

            <Field label="Purpose">
              <Select
                value={config.purpose || 'executive briefing'}
                onChange={(v) => setConfig({ ...config, purpose: v })}
                options={PURPOSES}
              />
            </Field>

            <Field label="Target Audience">
              <Select
                value={config.audience || 'officials'}
                onChange={(v) => setConfig({ ...config, audience: v })}
                options={AUDIENCES}
              />
            </Field>

            <Field label="Slide Count">
              <Segmented
                options={SLIDE_COUNTS}
                value={config.slide_count || '8'}
                onChange={(v) => setConfig({ ...config, slide_count: v })}
              />
            </Field>

            <Field label="Estimated Duration">
              <Segmented
                options={DURATIONS}
                value={config.duration || '10'}
                onChange={(v) => setConfig({ ...config, duration: v })}
              />
            </Field>

            <Field label="Language">
              <Segmented
                options={languages.map((code) => ({ key: code, label: code.toUpperCase() }))}
                value={config.language || 'en'}
                onChange={(v) => setConfig({ ...config, language: v })}
              />
            </Field>

            <Field label="Content Detail Level">
              <Segmented
                options={[
                  { key: 'concise', label: 'Concise' },
                  { key: 'balanced', label: 'Balanced' },
                  { key: 'detailed', label: 'Detailed' },
                ]}
                value={config.content_detail || 'balanced'}
                onChange={(v) => setConfig({ ...config, content_detail: v })}
              />
            </Field>

            <Field label="Visual Theme">
              <Select
                value={config.theme || 'corporate_blue'}
                onChange={(v) => setConfig({ ...config, theme: v })}
                options={THEMES}
              />
            </Field>

            <Field label="Speaker Notes">
              <label className="flex items-center gap-2 pt-2 text-xs font-medium text-ink-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.speaker_notes ?? true}
                  onChange={(e) => setConfig({ ...config, speaker_notes: e.target.checked })}
                  className="h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                />
                Generate speaker notes for each slide
              </label>
            </Field>
          </div>

          <Field label="Additional Instructions (Optional)">
            <textarea
              value={config.additional_instructions || ''}
              onChange={(e) => setConfig({ ...config, additional_instructions: e.target.value })}
              rows={2}
              placeholder="e.g. Emphasize budget allocations, risk mitigations, and timeline milestones."
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
            />
          </Field>

          <div className="flex items-center justify-between border-t border-ink-100 pt-4">
            <Button variant="ghost" onClick={() => setStep(1)}>
              ← Back to Source
            </Button>
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={handleApproveAndGenerateDeck}
                disabled={generatingDeck || generatingOutline}
              >
                Quick Generate Deck
              </Button>
              <Button onClick={handleGenerateOutline} disabled={generatingOutline}>
                <Icon name="spark" />
                {generatingOutline ? 'Generating Outline…' : 'Generate AI Slide Outline →'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 3: AI SLIDE OUTLINE REVIEW */}
      {step === 3 && outline && (
        <div className="space-y-6 py-2">
          <div className="flex flex-wrap items-center justify-between gap-4 bg-ink-50 p-4 rounded-xl border border-ink-200">
            <div className="flex-1 min-w-[240px]">
              <span className="text-[11px] font-bold text-ink-500 uppercase tracking-wider block mb-1">
                Presentation Outline Title
              </span>
              <input
                type="text"
                value={outline.title}
                onChange={(e) => setOutline({ ...outline, title: e.target.value })}
                className="w-full rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-sm font-bold outline-none focus:border-brand-500"
              />
            </div>
            <Button variant="secondary" onClick={handleAddOutlineSlide}>
              <Icon name="plus" />
              Add Slide Card
            </Button>
          </div>

          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {outline.slides.map((item, idx) => (
              <div
                key={item.id || idx}
                className="flex flex-col gap-3 rounded-xl border border-ink-200 bg-white p-4 shadow-2xs md:flex-row md:items-start"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-xs font-bold text-brand-700 border border-blue-100">
                  {idx + 1}
                </span>

                <div className="grid flex-1 gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="text-[11px] font-medium text-ink-500">Slide Title</span>
                    <input
                      type="text"
                      value={item.title}
                      onChange={(e) => handleUpdateOutlineItem(idx, { title: e.target.value })}
                      className="mt-1 w-full rounded-md border border-ink-200 px-2.5 py-1 text-xs font-semibold outline-none focus:border-brand-500"
                    />
                  </label>

                  <label className="block">
                    <span className="text-[11px] font-medium text-ink-500">Suggested Layout</span>
                    <Select
                      value={item.suggested_layout || 'standard_bullet'}
                      onChange={(v) => handleUpdateOutlineItem(idx, { suggested_layout: v })}
                      options={LAYOUT_OPTIONS}
                    />
                  </label>

                  <label className="block sm:col-span-2">
                    <span className="text-[11px] font-medium text-ink-500">Key Message & Summary</span>
                    <textarea
                      value={item.summary || item.key_message}
                      onChange={(e) => handleUpdateOutlineItem(idx, { summary: e.target.value })}
                      rows={2}
                      className="mt-1 w-full rounded-md border border-ink-200 px-2.5 py-1 text-xs outline-none focus:border-brand-500"
                    />
                  </label>
                </div>

                <div className="flex items-center gap-1 self-end md:self-start">
                  <button
                    disabled={idx === 0}
                    onClick={() => handleMoveOutlineSlide(idx, 'up')}
                    className="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-800 disabled:opacity-20 text-xs"
                    title="Move Up"
                  >
                    ↑
                  </button>
                  <button
                    disabled={idx === outline.slides.length - 1}
                    onClick={() => handleMoveOutlineSlide(idx, 'down')}
                    className="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-800 disabled:opacity-20 text-xs"
                    title="Move Down"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => handleDeleteOutlineSlide(idx)}
                    className="rounded p-1 text-red-500 hover:bg-red-50 text-xs"
                    title="Delete Slide"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between border-t border-ink-100 pt-4">
            <Button variant="ghost" onClick={() => setStep(2)}>
              ← Back to Configuration
            </Button>
            <div className="flex items-center gap-3">
              <Button variant="secondary" onClick={handleGenerateOutline} disabled={generatingOutline}>
                Regenerate Outline
              </Button>
              <Button onClick={handleApproveAndGenerateDeck} disabled={generatingDeck}>
                <Icon name="spark" />
                Approve & Generate Presentation ({outline.slides.length + 1} Slides) →
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: GENERATING DECK */}
      {step === 4 && (
        <div className="space-y-6 py-10 text-center">
          <div className="mx-auto max-w-md space-y-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-brand-600 mx-auto animate-pulse shadow-xs">
              <Icon name="spark" className="h-6 w-6" />
            </span>
            <h3 className="text-base font-bold text-ink-900">Synthesizing PowerPoint Presentation</h3>
            <Progress value={job?.progress ?? 0.4} label={job?.stage ?? 'Formatting slides & verifying contrast…'} />
            <p className="text-xs text-ink-500">
              Applying contrast-aware theme token styling, text-fitting, and layout validation...
            </p>
          </div>
        </div>
      )}

      {/* STEP 5: INTERACTIVE SLIDE STUDIO WORKSPACE */}
      {step === 5 && outputDetail && (
        <div className="space-y-6">
          {/* Change Summary Banner */}
          {changeSummary.length > 0 && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3.5 text-xs">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-emerald-900 flex items-center gap-1.5">
                  <Icon name="check" className="h-4 w-4 text-emerald-600" />
                  Presentation Updated & Verified
                </h4>
                <button
                  onClick={() => setChangeSummary([])}
                  className="text-emerald-700 hover:text-emerald-900 font-bold"
                >
                  ✕
                </button>
              </div>
              <ul className="list-disc list-inside text-emerald-800 space-y-0.5 mt-1 text-[11px]">
                {changeSummary.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Unified Studio Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-ink-200 bg-ink-50 p-3">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-ink-700">Theme:</span>
              <Select
                value={config.theme || (outputDetail.controls as any)?.theme || 'corporate_blue'}
                onChange={(v) => handleApplyThemeChange(v)}
                options={THEMES}
              />

              <Button
                variant="secondary"
                onClick={handleOpenSettingsDrawer}
                className="text-xs"
              >
                <Icon name="settings" className="h-3.5 w-3.5" />
                Global Settings
              </Button>

              {outputDetail.version > 1 && (
                <Button
                  variant="secondary"
                  onClick={handleRevertVersion}
                  disabled={reverting}
                  className="text-xs"
                >
                  <Icon name="back" className="h-3.5 w-3.5" />
                  {reverting ? 'Reverting…' : `Revert to v${outputDetail.version - 1}`}
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={handleDownloadPPTX} disabled={exporting}>
                <Icon name="download" className="h-4 w-4" />
                {exporting ? 'Preparing PPTX…' : 'Download PowerPoint (.pptx)'}
              </Button>
            </div>
          </div>

          {/* Global Settings Drawer (Collapsible) */}
          {showSettingsDrawer && (
            <div className="rounded-2xl border border-brand-200 bg-blue-50/40 p-5 space-y-4 animate-in fade-in duration-150">
              <div className="flex items-center justify-between border-b border-brand-100 pb-2">
                <h3 className="text-xs font-bold text-ink-900 flex items-center gap-2">
                  <Icon name="edit" className="text-brand-600 h-4 w-4" />
                  Reconfigure Presentation Parameters
                </h3>
                <button
                  onClick={() => setShowSettingsDrawer(false)}
                  className="text-ink-400 hover:text-ink-700 text-xs font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Presentation Title">
                  <input
                    type="text"
                    value={editConfig.title || ''}
                    onChange={(e) => setEditConfig({ ...editConfig, title: e.target.value })}
                    className="w-full rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                  />
                </Field>

                <Field label="Purpose">
                  <Select
                    value={editConfig.purpose || 'executive briefing'}
                    onChange={(v) => setEditConfig({ ...editConfig, purpose: v })}
                    options={PURPOSES}
                  />
                </Field>

                <Field label="Target Audience">
                  <Select
                    value={editConfig.audience || 'officials'}
                    onChange={(v) => setEditConfig({ ...editConfig, audience: v })}
                    options={AUDIENCES}
                  />
                </Field>

                <Field label="Detail Level">
                  <Segmented
                    options={[
                      { key: 'concise', label: 'Concise' },
                      { key: 'balanced', label: 'Balanced' },
                      { key: 'detailed', label: 'Detailed' },
                    ]}
                    value={editConfig.content_detail || 'balanced'}
                    onChange={(v) => setEditConfig({ ...editConfig, content_detail: v })}
                  />
                </Field>

                <Field label="Language">
                  <Select
                    value={editConfig.language || 'en'}
                    onChange={(v) => setEditConfig({ ...editConfig, language: v })}
                    options={languages.map((c) => ({ key: c, label: c.toUpperCase() }))}
                  />
                </Field>
              </div>

              <Field label="Additional AI Instructions">
                <textarea
                  value={editConfig.additional_instructions || ''}
                  onChange={(e) => setEditConfig({ ...editConfig, additional_instructions: e.target.value })}
                  rows={2}
                  placeholder="e.g. Focus on cybersecurity mitigations, risk metrics, and budget timelines."
                  className="w-full rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                />
              </Field>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-brand-100">
                <Button variant="ghost" onClick={() => setShowSettingsDrawer(false)} disabled={reconfiguring}>
                  Cancel
                </Button>
                <Button onClick={handleApplyGlobalReconfig} disabled={reconfiguring}>
                  {reconfiguring ? 'Updating Presentation…' : 'Apply Settings'}
                </Button>
              </div>
            </div>
          )}

          {/* MAIN 2-COLUMN SLIDE STUDIO WORKSPACE */}
          <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
            {/* Left Sidebar: Slide Thumbnails & Management */}
            <div className="space-y-3 rounded-xl border border-ink-200 bg-white p-3 shadow-2xs">
              <div className="flex items-center justify-between border-b border-ink-100 pb-2">
                <span className="text-xs font-bold text-ink-900">
                  Slides ({outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1})
                </span>
                <Button
                  variant="secondary"
                  onClick={() => handleAddSlide()}
                  className="text-[11px] py-1 px-2"
                >
                  <Icon name="plus" className="h-3 w-3" />
                  Add Slide
                </Button>
              </div>

              <div className="space-y-2 max-h-[580px] overflow-y-auto pr-1">
                {/* Cover Slide Thumbnail */}
                <button
                  onClick={() => selectSlideForEdit(0)}
                  className={`w-full flex items-center justify-between rounded-lg border p-2.5 text-left text-xs transition ${
                    activeSlideIndex === 0
                      ? 'border-brand-600 bg-blue-50/80 font-bold text-brand-700 ring-2 ring-brand-300'
                      : 'border-ink-200 bg-white text-ink-800 hover:bg-ink-50'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-ink-100 text-[10px] font-bold text-ink-600">
                      1
                    </span>
                    <span className="truncate font-semibold">{outputDetail.content_ir.title || 'Title Cover'}</span>
                  </div>
                  <span className="text-[9px] bg-ink-100 text-ink-600 px-1.5 py-0.5 rounded font-mono">Cover</span>
                </button>

                {/* Content Slides Thumbnails */}
                {outputDetail.content_ir.nodes
                  .filter((n) => n.kind === 'slide')
                  .map((node, i) => (
                    <div
                      key={node.id}
                      onClick={() => selectSlideForEdit(i + 1)}
                      className={`flex items-center justify-between rounded-lg border p-2 text-xs cursor-pointer transition ${
                        activeSlideIndex === i + 1
                          ? 'border-brand-600 bg-blue-50/80 font-bold text-brand-700 ring-2 ring-brand-300'
                          : 'border-ink-200 bg-white text-ink-800 hover:bg-ink-50'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-ink-100 text-[10px] font-bold text-ink-600">
                          {i + 2}
                        </span>
                        <div className="truncate flex-1">
                          <p className="truncate font-semibold text-xs">{node.title || 'Untitled Slide'}</p>
                          <div className="flex items-center gap-1 mt-0.5">
                            <span className="text-[9px] text-ink-500 bg-ink-100 px-1 py-0.2 rounded capitalize">
                              {node.layout || 'bullets'}
                            </span>
                            {node.is_user_modified && (
                              <span className="text-[9px] bg-amber-100 text-amber-800 font-bold px-1 rounded">
                                Edited
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Direct Inline Action Controls */}
                      <div className="flex items-center gap-0.5 shrink-0 ml-1">
                        <button
                          disabled={i === 0}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMoveSlide(i, 'up')
                          }}
                          className="rounded p-1 text-ink-400 hover:bg-ink-200 disabled:opacity-20 text-[10px]"
                          title="Move Up"
                        >
                          ↑
                        </button>
                        <button
                          disabled={i === outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length - 1}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMoveSlide(i, 'down')
                          }}
                          className="rounded p-1 text-ink-400 hover:bg-ink-200 disabled:opacity-20 text-[10px]"
                          title="Move Down"
                        >
                          ↓
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDuplicateSlide(node)
                          }}
                          className="rounded p-1 text-blue-600 hover:bg-blue-100 text-[10px]"
                          title="Duplicate Slide"
                        >
                          📋
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteSlide(node.id)
                          }}
                          className="rounded p-1 text-red-500 hover:bg-red-100 text-[10px]"
                          title="Delete Slide"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            {/* Right Canvas: Preview & Inline Editor Panel */}
            <div className="space-y-4 rounded-xl border border-ink-200 bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between border-b border-ink-100 pb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-bold text-ink-900">
                    {activeSlideIndex === 0
                      ? 'Cover Slide Details'
                      : `Slide ${activeSlideIndex + 1}: ${editingSlide?.title || 'Untitled'}`}
                  </h3>
                  {editingSlide?.is_user_modified && (
                    <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full">
                      Customized
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Segmented
                    options={[
                      { key: 'preview', label: 'Preview Canvas' },
                      { key: 'edit', label: 'Edit Content' },
                    ]}
                    value={editorTab}
                    onChange={(v) => setEditorTab(v as any)}
                  />
                  {activeSlideIndex > 0 && editingSlide && (
                    <Button
                      variant="secondary"
                      onClick={() => handleDeleteSlide(editingSlide.id)}
                      className="text-xs py-1 px-2.5 text-red-600 border-red-200 hover:bg-red-50"
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>

              {/* Tab 1: Live Interactive Preview */}
              {editorTab === 'preview' && (
                <div className="space-y-4">
                  <DeckPreview
                    ir={outputDetail.content_ir}
                    theme={config.theme || (outputDetail.controls as any)?.theme || 'corporate_blue'}
                    selectedIndex={activeSlideIndex}
                    onSelectSlide={selectSlideForEdit}
                  />

                  <div className="flex items-center justify-between text-xs text-ink-500 pt-2 border-t border-ink-100">
                    <span>
                      Viewing Slide {activeSlideIndex + 1} of{' '}
                      {outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1}
                    </span>
                    <Button
                      variant="secondary"
                      onClick={() => setEditorTab('edit')}
                      className="text-xs py-1 px-2.5"
                    >
                      <Icon name="edit" />
                      Edit Slide Details
                    </Button>
                  </div>
                </div>
              )}

              {/* Tab 2: Inline Content & Layout Editor */}
              {editorTab === 'edit' && (
                <div className="space-y-4">
                  {activeSlideIndex === 0 ? (
                    <div className="space-y-4">
                      <Field label="Presentation Title">
                        <input
                          type="text"
                          value={outputDetail.content_ir.title}
                          onChange={(e) => {
                            const updated = { ...outputDetail.content_ir, title: e.target.value }
                            setOutputDetail({ ...outputDetail, content_ir: updated })
                            api.updateOutput(outputDetail.id, updated)
                          }}
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs font-semibold outline-none focus:border-brand-500"
                        />
                      </Field>
                    </div>
                  ) : editingSlide ? (
                    <div className="space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <Field label="Slide Title">
                          <input
                            type="text"
                            value={editingSlide.title || ''}
                            onChange={(e) => {
                              const updated = { ...editingSlide, title: e.target.value }
                              setEditingSlide(updated)
                              handleSaveSlideEdit(updated)
                            }}
                            className="w-full rounded-md border border-ink-200 px-3 py-1.5 text-xs font-semibold outline-none focus:border-brand-500"
                          />
                        </Field>

                        <Field label="Slide Layout Type">
                          <Select
                            value={editingSlide.layout || 'standard_bullet'}
                            onChange={(v) => {
                              const updated = { ...editingSlide, layout: v }
                              setEditingSlide(updated)
                              handleSaveSlideEdit(updated)
                            }}
                            options={LAYOUT_OPTIONS}
                          />
                        </Field>
                      </div>

                      <Field label="Bullet Points / Content Blocks (One item per line)">
                        <textarea
                          value={(editingSlide.items || []).join('\n')}
                          onChange={(e) => {
                            const updated = {
                              ...editingSlide,
                              items: e.target.value.split('\n'),
                            }
                            setEditingSlide(updated)
                            handleSaveSlideEdit(updated)
                          }}
                          rows={6}
                          placeholder="Enter bullet points, metrics (Value: Label), or process steps (Phase: Description)..."
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500 font-mono"
                        />
                        <p className="text-[10px] text-ink-500 mt-1">
                          Tip: Use <code className="bg-ink-100 px-1 rounded">Label: Value</code> for metrics or <code className="bg-ink-100 px-1 rounded">Phase: Description</code> for process flows.
                        </p>
                      </Field>

                      <Field label="Speaker Notes">
                        <textarea
                          value={editingSlide.notes || ''}
                          onChange={(e) => {
                            const updated = { ...editingSlide, notes: e.target.value }
                            setEditingSlide(updated)
                            handleSaveSlideEdit(updated)
                          }}
                          rows={3}
                          placeholder="Speaker narrative notes..."
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
                        />
                      </Field>

                      {/* Single Slide AI Regeneration Panel */}
                      <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-brand-800 flex items-center gap-1.5">
                            <Icon name="spark" className="h-4 w-4 text-brand-600" />
                            Regenerate This Slide with AI
                          </h4>
                          <span className="text-[10px] text-ink-500">Uses source facts</span>
                        </div>
                        <textarea
                          value={slideInstructions}
                          onChange={(e) => setSlideInstructions(e.target.value)}
                          placeholder="e.g. Focus on financial impact, expand metrics, or convert to process timeline."
                          rows={2}
                          className="w-full rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                        />
                        <Button
                          variant="secondary"
                          onClick={handleSingleSlideRegenerate}
                          disabled={regeneratingSlide}
                          className="w-full justify-center"
                        >
                          {regeneratingSlide ? 'Regenerating Slide…' : 'Regenerate This Slide'}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
